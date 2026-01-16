import random
import string
from typing import Callable
from unittest.mock import patch
import datetime
import numpy as np
import pytest
from sqlalchemy import and_, delete, insert, select
from sqlalchemy.orm import Session, sessionmaker
from backend.helpers.scrape_letterboxd import ScrapedRating
from backend.helpers.reduce_features import N_COMPONENTS, normalize
from backend.helpers.db_models import K, LetterboxdUser, Movie, PreprocessedMovie, Rating, Recommendation
from backend.helpers.db import (
    BASE_RECOMMENDATION_TTL_HRS,
    RECOMMENDATION_TTL_HRS_PER_100_RATINGS,
    NoDataException,
    add_letterboxd_user_ratings,
    fill_ratings_table_imdb_ids,
    get_engine,
    get_expiration_timestamp,
    get_features_and_ratings,
    get_letterboxd_user_id,
    get_k_nearest_neighbor_imdb_ids,
    get_recommendation_imdb_ids,
    get_cached_recommendation,
    cache_recommendation,
    get_movies,
    cache_trailer_ids,
    has_expired,
    delete_expired_recommendations,
    delete_recommendations,
    extract_imdb_ids_from_recommendation,
    populate_ratings_table,
)

engine = get_engine()
scraped_ratings: list[ScrapedRating] = [
            ("Five Nights at Freddy's 2", 2025, 3.0),
            ("Avatar: Fire and Ash", 2025, 3.0),
            ("Marty Supreme", 2025, 4.0),
            ("Chainsaw Man – The Movie: Reze Arc", 2025, 5.0),
            ("The Conjuring: Last Rites", 2025, 2.0),
            ("Demon Slayer: Kimetsu no Yaiba Infinity Castle", 2025, None),
            ("The Fragrant Flower Blooms with Dignity", 2025, 4.0),
            ("Takopi's Original Sin", 2025, 3.0),
            ("KPop Demon Hunters", 2025, 3.0),
            ("F1", 2025, None),
            ]


def get_random_string() -> str:
    return "".join(random.choices(string.ascii_letters, k=21))


def get_k_imdb_ids(session: Session) -> list[str]:
    """
    Retrieves `K` `imdb_id`s from the `movies` table.
    """
    imdb_ids = list(session.scalars(
        select(Movie.imdb_id)
        .where(Movie.imdb_id != None)
        .limit(K)
        ).all())
    assert len(imdb_ids) == K
    return imdb_ids


def get_imdb_id_kwargs(session: Session) -> dict[str, str]:
    """
    Returns the key word arguments for the `imdb_id`s needed to a create a `Recommendation`,
    using the first `K` `imdb_id`s from the table `movies`.
    """
    return { 
        f"imdb_id_{i + 1}":imdb_id for i, imdb_id in enumerate(get_k_imdb_ids(session)) 
    }


def get_from_ratings_table(session: Session, letterboxd_user_id: int) -> list[Rating]:
    """
    Retrieves all the entries from the table `ratings` associated with `letterboxd_user_id`.
    """
    return list(session.scalars(
        select(Rating)
        .where(Rating.letterboxd_user_id == letterboxd_user_id)
        ).all())


def reset_tables_post_test(test: Callable):
    """
    Resets the tables `ratings`, `recommendations`, and `letterboxd_users`,
    after executing `test`.
    """
    def wrapper(*args, **kwargs):
        test(*args, **kwargs)
        with Session(engine) as session:
            session.execute(delete(Rating))
            session.execute(delete(Recommendation))
            session.execute(delete(LetterboxdUser))
            session.commit()
    return wrapper


@reset_tables_post_test
# Every test method needs to be prefixed with `test` for pytest to detect it
def test_get_letterboxd_user_id():
    """
    Ensure the `letterboxd_user_id` associated with a username is returned.
    """
    username = get_random_string()
    with Session(engine) as session:
        letterboxd_user_id = get_letterboxd_user_id(session, username)
        assert letterboxd_user_id == get_letterboxd_user_id(session, username)


@reset_tables_post_test
def test_populate_ratings_table():
    """
    Ensure no entries for `letterboxd_user_id` exist prior to table population,
    and all the items in `scraped_ratings` are inserted into the table `ratings`.
    """
    with Session(engine) as session:
        letterboxd_user_id = get_letterboxd_user_id(session, get_random_string())
        ratings = get_from_ratings_table(session, letterboxd_user_id)
        assert len(ratings) == 0

        populate_ratings_table(session, letterboxd_user_id, scraped_ratings)
        ratings = get_from_ratings_table(session, letterboxd_user_id)
    assert len(ratings) == len(scraped_ratings)
    for rating in ratings:
        assert rating.letterboxd_user_id == letterboxd_user_id
        assert rating.imdb_id == None
    ratings = ((r.original_title, r.release_year, r.rating) for r in ratings)
    assert len(set(ratings) - set(scraped_ratings)) ==  0


@reset_tables_post_test
def test_fill_ratings_table_imdb_ids():
    """
    Ensure for all the entries in the table `ratings` that are associated 
    with `letterboxd_user_id`, the `imdb_id`s are updated if they can be
    retrieved, and none of the other values are disturbed. 
    """
    with Session(engine) as session:
        letterboxd_user_id = get_letterboxd_user_id(session, get_random_string())
        populate_ratings_table(session, letterboxd_user_id, scraped_ratings)
        fill_ratings_table_imdb_ids(session, letterboxd_user_id)
        ratings = get_from_ratings_table(session, letterboxd_user_id)
        assert len(ratings) == len(scraped_ratings)
        for rating in ratings:
            assert rating.letterboxd_user_id == letterboxd_user_id
            expected_imdb_id = session.scalar(
                select(Movie.imdb_id)
                .where(
                    and_(
                        Movie.original_title == rating.original_title,
                        Movie.release_year == rating.release_year
                    )
                )
            )
            assert rating.imdb_id == expected_imdb_id
    ratings = ((r.original_title, r.release_year, r.rating) for r in ratings)
    assert len(set(ratings) - set(scraped_ratings)) == 0


@reset_tables_post_test
def test_add_letterboxd_user_ratings():
    """
    Ensure user ratings only persist in the context of `add_letterboxd_user_ratings`.
    """
    with Session(engine) as session:
        letterboxd_user_id = get_letterboxd_user_id(session, get_random_string())
        before_ratings_count = len(get_from_ratings_table(session, letterboxd_user_id))
        with add_letterboxd_user_ratings(session, letterboxd_user_id, scraped_ratings):
            pass
        after_ratings_count = len(get_from_ratings_table(session, letterboxd_user_id))
        assert before_ratings_count == after_ratings_count


def test_get_expiration_timestamp():
    """
    Ensure `num_ratings` < 100 are given a base expiration timestamp,
    and expiration timestamps for `num_ratings` >= 100 are proportional 
    to `num_ratings`.
    """
    base_expiration_timestamp = get_expiration_timestamp(int(42.0))
    current_timestamp = datetime.datetime.now()
    timestamp_after_base_ttl = (
        current_timestamp + datetime.timedelta(hours=BASE_RECOMMENDATION_TTL_HRS)
    )
    assert base_expiration_timestamp >= current_timestamp
    assert base_expiration_timestamp <= timestamp_after_base_ttl

    proportional_expiration_timestamp = get_expiration_timestamp(420)
    current_timestamp = datetime.datetime.now()
    timestamp_after_ttl = (
        current_timestamp 
        + datetime.timedelta(
            hours=BASE_RECOMMENDATION_TTL_HRS 
            + RECOMMENDATION_TTL_HRS_PER_100_RATINGS * (420//100)
            )
    )
    assert proportional_expiration_timestamp >= current_timestamp
    assert proportional_expiration_timestamp <= timestamp_after_ttl


def test_has_expired():
    """
    Ensure expiration timestamps older than the current timestamp are considered expired.
    """
    current_timestamp = datetime.datetime.now()
    expired_timestamp = current_timestamp - datetime.timedelta(seconds=21)
    not_expired_timestamp = current_timestamp + datetime.timedelta(hours=6, seconds=7)
    assert has_expired(Recommendation(expiration_timestamp=expired_timestamp))
    assert not has_expired(Recommendation(expiration_timestamp=not_expired_timestamp))


@reset_tables_post_test
def test_delete_expired_recommendations():
    """
    Ensure only non-expired entries remain in the table `recommendations`.
    """
    delete_recommendations(sessionmaker(engine))
    current_timestamp = datetime.datetime.now()
    expired_timestamp = current_timestamp - datetime.timedelta(seconds=21)
    not_expired_timestamp = current_timestamp + datetime.timedelta(hours=6, seconds=7)
    with Session(engine) as session:
        imdb_id_kwargs = get_imdb_id_kwargs(session)
        expired_rec_values = {
            "letterboxd_user_id": get_letterboxd_user_id(session, get_random_string()),
            "expiration_timestamp": expired_timestamp,
            **imdb_id_kwargs
        }
        not_expired_rec_values = {
            "letterboxd_user_id": get_letterboxd_user_id(session, get_random_string()),
            "expiration_timestamp": not_expired_timestamp,
            **imdb_id_kwargs
        }
        session.execute(insert(Recommendation).values(expired_rec_values))
        session.execute(insert(Recommendation).values(not_expired_rec_values))
        session.commit()
        delete_expired_recommendations(sessionmaker(engine))
        all_recommendations = session.execute(select(Recommendation)).fetchall()
        assert len(all_recommendations) == 1
        

@reset_tables_post_test
def test_get_features_and_ratings():
    """
    Ensure that feature vectors and ratings are retrieved for all rated movies with 
    non-`NULL` `imdb_id`s and non-`NULL` `rating`s. 
    """
    username = get_random_string()
    with Session(engine) as session:
        letterboxd_user_id = get_letterboxd_user_id(session, username)
        with add_letterboxd_user_ratings(session, letterboxd_user_id, scraped_ratings):
            ratings = get_from_ratings_table(session, letterboxd_user_id)
            expected_values = [
                (r.imdb_id, r.rating) for r in ratings 
                if r.imdb_id != None and r.rating != None
            ]
            expected_imdb_ids = [imdb_id for imdb_id, _ in expected_values]
            expected_rating_values = [rating for _, rating in expected_values]
            feature_vectors, rating_values = get_features_and_ratings(
                session, letterboxd_user_id
            )
            expected_feature_vectors = session.scalars(
                select(PreprocessedMovie.features)
                .where(PreprocessedMovie.imdb_id.in_(expected_imdb_ids))
            ).all()
            assert len(rating_values) == len(expected_rating_values)
            assert len(feature_vectors) == len(expected_feature_vectors)
            assert len(rating_values) == len(feature_vectors)
            assert len(set(rating_values) - set(expected_rating_values)) == 0
            expected_feature_vectors = set(tuple(v) for v in expected_feature_vectors)
            feature_vectors = set(tuple(v) for v in feature_vectors)
            assert len(feature_vectors - expected_feature_vectors) == 0
    

def test_get_k_nearest_neighbor_imdb_ids():
    """
    Ensure that non-nearest neighbors of a representative movie have cosine 
    similarities less than or equal to the lowest cosine similarity of the nearest 
    neighbors.
    """
    representative_features = np.empty((N_COMPONENTS,))
    random_gen = random.Random()
    for i in range(N_COMPONENTS):
        representative_features[i] = random_gen.random()
    normalized_rep_features = normalize(representative_features)
    with Session(engine) as session:
        imdb_ids = get_k_nearest_neighbor_imdb_ids(session, normalized_rep_features)
        nearest_neighbor_features = session.scalars(
            select(PreprocessedMovie.features)
            .where(PreprocessedMovie.imdb_id.in_(imdb_ids))
            .order_by(
                PreprocessedMovie.features.max_inner_product(normalized_rep_features)
            )
            .limit(K)
        ).all()
        assert len(nearest_neighbor_features) == K
        min_nearest_neighbor_similarity = np.dot(
            nearest_neighbor_features[K - 1], normalized_rep_features
        )
        closest_non_nearest_neighbor_features = session.scalars(
            select(PreprocessedMovie.features)
            .where(PreprocessedMovie.imdb_id.not_in(imdb_ids))
            .order_by(
                PreprocessedMovie.features.max_inner_product(normalized_rep_features)
            )
            .limit(1)
        ).all()
        assert len(closest_non_nearest_neighbor_features) == 1
        max_non_nearest_neighbor_similarity = np.dot(
            closest_non_nearest_neighbor_features[0], normalized_rep_features
        )
        assert min_nearest_neighbor_similarity >= max_non_nearest_neighbor_similarity
        

@reset_tables_post_test
@patch("backend.helpers.db.get_features_and_ratings")
def test_get_recommendation_imdb_ids(mock_get_features_and_ratings):
    """
    Ensure `NoDataException` is raised when no feature vectors could be 
    retrieved for a non-zero amount of rated movies. 
    """
    with Session(engine) as session:
        letterboxd_user_id = get_letterboxd_user_id(session, get_random_string())
        mock_get_features_and_ratings.return_value = ([], [])
        with pytest.raises(NoDataException):
            get_recommendation_imdb_ids(session, letterboxd_user_id, scraped_ratings)


def test_extract_imdb_ids_from_recommendation():
    """
    Ensure all the `imdb_id`s of a `Recommendation` are extracted.
    """
    with Session(engine) as session:
        imdb_id_kwargs = get_imdb_id_kwargs(session)
        recommendation = Recommendation(**imdb_id_kwargs)
        extracted_imdb_ids = extract_imdb_ids_from_recommendation(recommendation)
        assert len(imdb_id_kwargs) == len(extracted_imdb_ids)
        assert len(set(imdb_id_kwargs.values()) - set(extracted_imdb_ids)) == 0


@reset_tables_post_test
def test_cache_recommendation():
    """
    Ensure the equality of the contents of a `Recommendation` inserted into the cache
    for a given `letterboxd_user_id`, with the `Recommendation` retrieved for that
    `letterboxd_user_id`.
    """
    with Session(engine) as session:
        letterboxd_user_id = get_letterboxd_user_id(session, get_random_string())
        imdb_ids = get_k_imdb_ids(session)
        cache_recommendation(session, letterboxd_user_id, len(scraped_ratings), imdb_ids)
        recommendation = get_cached_recommendation(session, letterboxd_user_id)
        assert recommendation is not None
        if recommendation is not None:
            rec_imdb_ids = extract_imdb_ids_from_recommendation(recommendation)
            assert len(imdb_ids) == len(rec_imdb_ids)
            assert len(set(imdb_ids) - set(rec_imdb_ids)) == 0


def test_get_movies():
    """
    Ensure all movies corresponding to a list of `imdb_id`s are retrieved.
    """
    with Session(engine) as session:
        imdb_ids = get_k_imdb_ids(session)
        movies_of_imdb_ids = get_movies(session, imdb_ids)
        movie_imdb_ids = [movie.imdb_id for movie in movies_of_imdb_ids]
        assert len(imdb_ids) == len(movie_imdb_ids)
        assert len(set(imdb_ids) - set(movie_imdb_ids)) == 0


def test_cache_trailer_ids():
    """
    Ensure that `trailer_id`s are correctly cached.
    """
    trailer_ids = [
        "spongebob", "patrick", "squidward", "mr.krabs", "sandy", 
        "plankton", "doodlebob", "larry", "jellyfish", "krabbypatty"
    ]
    assert len(trailer_ids) == K
    with Session(engine) as session:
        imdb_ids = get_k_imdb_ids(session)
        cache_trailer_ids(session, imdb_ids, trailer_ids)
        stored_trailer_ids = session.scalars(
            select(Movie.trailer_id).where(Movie.imdb_id.in_(imdb_ids))
        ).all()
        assert len(trailer_ids) == len(stored_trailer_ids)
        assert len(set(trailer_ids) - set(stored_trailer_ids)) == 0
        # Remove the trailer_ids inserted for testing purposes
        cache_trailer_ids(session, imdb_ids, [None] * len(imdb_ids))

