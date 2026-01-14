import os
import datetime
from typing import Sequence
from sqlalchemy import (
    Engine,
    and_,
    create_engine,
    insert,
    delete,
    select,
    update,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session, sessionmaker
from dotenv import load_dotenv
import numpy as np

if os.getcwd().endswith("helpers"):
    from db_models import (
        K,
        Movie, 
        PreprocessedMovie, 
        Recommendation, 
        LetterboxdUser,
        Rating, 
    )
    from scrape_letterboxd import ScrapedRating
    from representative import find_representative_movie
else:
    from .db_models import (
        K,
        Movie, 
        PreprocessedMovie, 
        Recommendation, 
        LetterboxdUser,
        Rating, 
    )
    from .scrape_letterboxd import ScrapedRating
    from .representative import find_representative_movie
       

# Feel free to adjust these values if they are too easygoing or harsh
BASE_RECOMMENDATION_TTL_HRS = 0.5
RECOMMENDATION_TTL_HRS_PER_100_RATINGS = 1


class NoDataException(Exception):
    """
    Raised when the feature vectors for movies of non-empty `list[ScrapedRating]` could 
    not be retrieved.
    """
    def __init__(self):
        super()


class UserInsertionException(Exception):
    """
    Raised when the `id` of a previously inserted `LetterboxdUser` could not be retrieved.
    """
    def __init__(self):
        super()


class add_letterboxd_user_ratings:
    """
    Context manager for a Letterboxd user's temporarily stored ratings.
    """
    def __init__(
        self, session: Session, letterboxd_user_id: int, scraped_ratings: list[ScrapedRating]
    ):
        """
        Adds the Letterboxd user's `scraped_ratings` and matches them with `imdb_id`s 
        if possible.
        """
        self.session = session
        self.letterboxd_user_id = letterboxd_user_id
        populate_ratings_table(self.session, self.letterboxd_user_id, scraped_ratings)
        fill_ratings_table_imdb_ids(self.session, self.letterboxd_user_id)
        self.session.commit()

    def __enter__(self) -> None:
        return

    def __exit__(self, exception_type, exception_val, exception_traceback):
        """
        Deletes the Letterboxd user's stored ratings.
        """
        self.session.execute(
            delete(Rating)
            .where(Rating.letterboxd_user_id == self.letterboxd_user_id)
        )


def get_engine(echo: bool = False) -> Engine:
    """
    Creates a sqlalchemy `Engine`. For this to work properly, ensure that the
    environment variables `PGUSER`, `PGHOST`, `PGPORT`, and `PGPASSWORD` are set 
    with the values matching the ones used during the PostgreSQL installation. While
    the first three may get set by PostgreSQL automatically, `PGPASSWORD` must be 
    manually set as an environment variable, or added to a .env file. Note that 
    multiple threads can share the same `Engine`, but every process must have its 
    own `Engine`. 
    Args:
        `echo`: If `True`, the database's activity is logged to `STDOUT`.
    Returns:
        A sqlalchemy `Engine`.
    """
    load_dotenv()
    env_vars = ["PGUSER", "PGHOST", "PGPORT", "PGPASSWORD"]
    env = { var:os.getenv(var) for var in env_vars }
    for var, val in env.items():
        if val is None:
            raise ValueError(
            f"Failed to get {var} environment variable.\n"
            f"Please set {var} in a .env file or add it to your environment."
            )

    db = "postgresql"
    db_api = "psycopg"
    db_name = "unboxd"
    user = env["PGUSER"]
    host = env["PGHOST"]
    port = env["PGPORT"]
    password = env["PGPASSWORD"]
    return create_engine(
        f"{db}+{db_api}://{user}:{password}@{host}:{port}/{db_name}", echo=echo
    )


def get_letterboxd_user_id(session: Session, username: str) -> int:
    """
    Retrieves the `id` associated with `username` in the table
    `letterboxd_users`. If it does not exist, a new entry is created using `username`,
    and the associated `id` is returned.
    Args: 
        `session`: A sqlalchemy `Session`.
        `username`: A Letterboxd user's username.
    Returns:
        A `letterboxd_user_id` usable in `recommendations` and `ratings`.
    Raises:
        `UserInsertionException`, if a user could not be inserted into the DB.
    """
    letterboxd_user_id = session.scalar(
            select(LetterboxdUser.id)
            .where(LetterboxdUser.username == username)
            )
    if letterboxd_user_id is not None: 
        return letterboxd_user_id

    letterboxd_user_id = session.scalar(
            insert(LetterboxdUser)
            .values({ "username":username })
            .returning(LetterboxdUser.id)
            )
    session.commit()
    if letterboxd_user_id is None:
        raise UserInsertionException()

    return letterboxd_user_id


def populate_ratings_table(
    session: Session, letterboxd_user_id: int, scraped_ratings: list[ScrapedRating]
) -> None:
    """
    Assigns `letterboxd_user_id` to all the items in `scraped_ratings`, and inserts
    the result into the table `ratings`.
    Args:
        `session`: A sqlalchemy `Session`.
        `letterboxd_user_id`: An `id` from the table `letterboxd_users`.
        `scraped_ratings`: A sequence of `(original_title, release_year, rating)`.
    """
    # The psycopg (DBAPI) cursor is used to insert `list[tuple]` instead of `list[dict]`
    cur = session.connection().connection.cursor()
    populate_temp_ratings_table = ("""
        INSERT INTO ratings (letterboxd_user_id, original_title, release_year, rating, imdb_id) 
        Values (%s, %s, %s, %s, NULL)"""
    )
    ratings_with_ids = [(letterboxd_user_id, *rating) for rating in scraped_ratings]
    cur.executemany(populate_temp_ratings_table, ratings_with_ids)
    session.commit()


def fill_ratings_table_imdb_ids(session: Session, letterboxd_user_id: int) -> None:
    """
    Updates the `imdb_id`s of entries in the table `ratings` associated with
    `letterboxd_user_id`, by fetching `imdb_id`s from the table `movies` where 
    the `original_title` and `release_year` are equal.
    Args:
        `session`: A sqlalchemy `Session`.
        `letterboxd_user_id`: An `id` from the table `letterboxd_users`.
    """
    session.execute(
            update(Rating)
            .where(
                and_(Rating.letterboxd_user_id == letterboxd_user_id,
                     Rating.original_title == Movie.original_title,
                     Rating.release_year == Movie.release_year,
                     )
                )
            .values(imdb_id=Movie.imdb_id)
            )
    session.commit()


def get_features_and_ratings(session: Session, letterboxd_user_id: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Retrieves the feature vectors and rating values of the entries in the table `ratings` 
    that are associated with `letterboxd_user_id`, and have non-`NULL` `imdb_id`s.
    Args:
        `session`: A sqlalchemy `Session`.
        `letterboxd_user_id`: An `id` from the table `letterboxd_users`.
    Returns:
        `([feature_vector_1, ..., feature_vector_m], [rating_1, ..., rating_m])`
    """
    cur = session.execute(
            select(PreprocessedMovie.features, Rating.rating)
            .join_from(
                PreprocessedMovie, 
                Rating, 
                PreprocessedMovie.imdb_id == Rating.imdb_id
                )
            .where(
                and_(Rating.letterboxd_user_id == letterboxd_user_id,
                     Rating.rating != None
                     )
                )
            )
    rows = cur.fetchall()

    # Split up the data and convert to numpy
    m = len(rows)
    ratings = np.empty((m,))
    feature_vectors = np.empty((m,), dtype=np.ndarray)
    for i, row in enumerate(rows):
        features, rating = row
        # `features` are already `np.ndarray`s
        feature_vectors[i] = features
        ratings[i] = rating
    return (feature_vectors, ratings)


def get_k_nearest_neighbor_imdb_ids(session: Session, representative_features: np.ndarray) -> list[str]:
    """
    Retrieves `K` `imdb_id`s of the movies yielding the largest dot (inner) products with the
    feature vector `representative_features`. Assuming all vectors are normalized, this is
    equivalent, and more efficient, than computing cosine similarities.
    Args:
        `session`: A sqlalchemy `Session`.
        `representative_features`: The feature vector of a user's representative movie.
    Returns:
        `K` `imdb_id`s
    """
    cur = session.scalars(
            select(PreprocessedMovie.imdb_id)
            .outerjoin_from(
                PreprocessedMovie, 
                Rating, 
                PreprocessedMovie.imdb_id == Rating.imdb_id
                )
            .where(Rating.original_title == None)
            .order_by(PreprocessedMovie.features.max_inner_product(representative_features))
            .limit(K)
            )
    imdb_ids = list(cur.fetchall())
    return imdb_ids


def get_recommendation_imdb_ids(
    session: Session, letterboxd_user_id: int, scraped_ratings: list[ScrapedRating]
) -> list[str]:
    """
    Retrieves `K` `imdb_id`s of movies recommended based on `scraped_ratings`.
    Args:
        `session`: A sqlalchemy `Session`.
        `letterboxd_user_id`: An `id` from the table `letterboxd_users`.
        `scraped_ratings`: A sequence of `(original_title, release_year, rating)`.
    Returns:
        `K` `imdb_id`s
    Raises:
        `NoDataException`, if no feature vectors could be retrieved for the rated movies.
    """
    with add_letterboxd_user_ratings(session, letterboxd_user_id, scraped_ratings):
        feature_vectors, ratings = get_features_and_ratings(session, letterboxd_user_id)
        if len(feature_vectors) == 0:
            raise NoDataException()

        representative_index = find_representative_movie(feature_vectors, ratings)

        rep_features = feature_vectors[representative_index]
        recommendation_imdb_ids = get_k_nearest_neighbor_imdb_ids(session, rep_features)
        return recommendation_imdb_ids


def get_expiration_timestamp(num_ratings: int) -> datetime.datetime:
    """
    Computes a timezone independent, expiration timestamp for a user's `Recommendation`
    proportional to `num_ratings`. 
    Args: 
        `num_ratings`: The number of user ratings scraped from Letterboxd.
    Returns:
        An expiration timestamp for a `Recommendation`.
    """
    current_timestamp = datetime.datetime.now()
    expiration_timestamp = current_timestamp + datetime.timedelta(
        hours=
        BASE_RECOMMENDATION_TTL_HRS
        + (RECOMMENDATION_TTL_HRS_PER_100_RATINGS * (num_ratings // 100))
    )
    return expiration_timestamp


def cache_recommendation(
        session: Session, 
        letterboxd_user_id: int, 
        num_ratings: int, 
        recommendation_imdb_ids: list[str]
) -> None:
    """
    Caches a `Recommendation` for `username` that has an expiration timestamp proportional to 
    `num_ratings`. If a previous `Recommendation` for `username` exists, it is updated.
    Otherwise, a new `Recommendation` is created.
    
    The proportional expiration timstamp is utilized because of the assumption: as 
    `num_ratings` increase, future ratings will have a smaller impact on `username`'s 
    `Recommendation`. Thus, `Recommendation`s of `username`s with higher `num_ratings` will 
    take longer to expire than `Recommendation`s of `username`s with lower `num_ratings`.
    Args:
        `session`: A sqlalchemy `Session`.
        `letterboxd_user_id`: An `id` from the table `letterboxd_users`.
        `num_ratings`: The number of ratings scraped from `username`'s account.
        `recommendation_imdb_ids`: The `imdb_id`s of the `Recommendation`.
    """
    assert len(recommendation_imdb_ids) == K
    data_without_id = dict()
    data_without_id["expiration_timestamp"] = get_expiration_timestamp(num_ratings),
    for i, imdb_id in enumerate(recommendation_imdb_ids):
        data_without_id[f"imdb_id_{i + 1}"] = imdb_id

    data = data_without_id.copy()
    data["letterboxd_user_id"] = letterboxd_user_id

    # Upsert: try to insert a Recommendation, but if an expired one exists, update it
    session.execute(
            postgresql.insert(Recommendation)
            .on_conflict_do_update(
                index_elements=[Recommendation.letterboxd_user_id], 
                index_where=Recommendation.letterboxd_user_id == letterboxd_user_id,
                set_=data_without_id
                )
            .values(data)
            )
    session.commit()


def delete_expired_recommendations(Session: sessionmaker) -> None:
    """
    Deletes entries from the table `recommendations` where the `expiration_timestamp` 
    is older than the current time.
    """
    with Session() as session:
        session.execute(
                delete(Recommendation)
                .where(Recommendation.expiration_timestamp < datetime.datetime.now())
                )
        session.commit()


def delete_recommendations(Session: sessionmaker) -> None:
    """
    Deletes all entries from the table `recommendations`.
    """
    with Session() as session:
        session.execute(delete(Recommendation))
        session.commit()


def get_movies(session: Session, imdb_ids: list[str]) -> list[Movie]:
    """
    Retrieves the entries from the table `movies` that have an `imdb_id` in `imdb_ids`.
    """
    cur = session.scalars(
            select(Movie)
            .where(Movie.imdb_id.in_(imdb_ids))
            )
    return list(cur.all())


def cache_trailer_ids(
    session: Session, imdb_ids: list[str], trailer_ids: Sequence[str | None]
) -> None:
    """
    Updates the `trailer_id` of entries from the table `movies` having an `imdb_id` in
    `imdb_ids`, using the values in `trailer_ids`.
    Args:
        `session`: A sqlalchemy `Session`.
        `imdb_ids`: The `imdb_id`s of movies without `trailer_id`s.
        `trailer_ids`: The YouTube trailer ids of the movies having `imdb_ids`.
    """
    # The psycopg (DBAPI) cursor is used to insert `list[tuple]` instead of `list[dict]`
    cur = session.connection().connection.cursor()
    data = list(zip(trailer_ids, imdb_ids))
    cur.executemany("""UPDATE movies SET trailer_id = %s WHERE imdb_id = %s""", data)
    session.commit()


def get_cached_recommendation(session: Session, letterboxd_user_id: int) -> Recommendation | None:
    """
    Retrieves the `Recommendation` associated with `letterboxd_user_id`, regardless
    of whether it expired.
    """
    recommendation = session.scalar(
            select(Recommendation)
            .where(Recommendation.letterboxd_user_id == letterboxd_user_id)
            )
    return recommendation


def extract_imdb_ids_from_recommendation(recommendation: Recommendation) -> list[str]:
    """
    Extracts the `imdb_id`s from `recommendation`.
    """
    imdb_ids = [
            recommendation.imdb_id_1,
            recommendation.imdb_id_2,
            recommendation.imdb_id_3,
            recommendation.imdb_id_4,
            recommendation.imdb_id_5,
            recommendation.imdb_id_6,
            recommendation.imdb_id_7,
            recommendation.imdb_id_8,
            recommendation.imdb_id_9,
            recommendation.imdb_id_10,
            ]
    return imdb_ids


def has_expired(recommendation: Recommendation) -> bool:
    """
    Returns `True` if `recommendation`'s `expiration_timestamp` is older than the 
    current time.
    """
    return recommendation.expiration_timestamp < datetime.datetime.now();

