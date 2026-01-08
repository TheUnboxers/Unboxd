import os
import datetime

from sqlalchemy import (
    Engine,
    and_,
    create_engine,
    insert,
    delete,
    select,
    update,
)
from sqlalchemy.orm import Session
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
    from scrape_letterboxd import Ratings
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
    from .scrape_letterboxd import Ratings
    from .representative import find_representative_movie

class add_letterboxd_user:
    """
    Context manager for a Letterboxd user's temporarily stored username and ratings.
    """
    def __init__(self, session: Session, username: str, ratings: Ratings):
        self.session = session
        self.username = username

        # Add an entry for the Letterboxd user and retrieve the automatically created id
        self.session.execute(insert(LetterboxdUser).values({ "username":self.username }))
        self.session.commit()
        letterboxd_user_id = self.session.scalar(
                select(LetterboxdUser.id)
                .where(LetterboxdUser.username == self.username)
        )
        if letterboxd_user_id is None:
            raise UserInsertionException()

        # Add entries for the user's ratings and match them with `imdb_id`s if possible
        self.letterboxd_user_id = letterboxd_user_id
        populate_ratings_table(self.session, self.letterboxd_user_id, ratings)
        fill_ratings_table_imdb_ids(self.session, self.letterboxd_user_id)
        self.session.commit()

    def __enter__(self) -> int:
        return self.letterboxd_user_id

    def __exit__(self, exception_type, exception_val, exception_traceback):
        """
        Deletes the Letterboxd user's username and ratings.
        """
        self.session.execute(
                delete(Rating)
                .where(Rating.letterboxd_user_id == self.letterboxd_user_id)
                )
        self.session.execute(
                delete(LetterboxdUser)
                .where(LetterboxdUser.username == self.username)
                )

class NoDataException(Exception):
    """
    Raised when the feature vectors for movies of non-empty `Ratings` could not be retrieved.
    """
    def __init__(self):
        super()

class UserInsertionException(Exception):
    """
    Raised when the `id` of a previously inserted `LetterboxdUser` could not be retrieved.
    """
    def __init__(self):
        super()
   

def get_engine(echo: bool = False) -> Engine:
    """
    Creates a sqlalchemy `Engine`. For this to work properly, ensure that if set, any 
    PostgreSQL environemnt variables (e.g. `PGUSER`, `PGPORT`, etc.), match the values below. 
    Also, set the `POSTGRESQL_PASSWORD` environment variable, or add it to a .env file. It 
    must be the same password associated with `PGUSER`/`user`. Note that multiple threads 
    can share the same `Engine`, but every process must have its own `Engine`. 

    Args:
        `echo`: If `True`, the database's activity is logged to `STDOUT`.

    Returns:
        A sqlalchemy `Engine`.
    """
    db = "postgresql"
    db_api = "psycopg"
    user = "postgres"
    host = "localhost"
    port = "5432"
    db_name = "unboxd"
    load_dotenv()
    password = os.getenv("POSTGRESQL_PASSWORD")
    if password is None:
        raise ValueError(
        "Failed to get POSTGRESQL_PASSWORD environment variable.\n"
        "Please set POSTGRESQL_PASSWORD in a .env file or add it to your environment."
        )
    return create_engine(f"{db}+{db_api}://{user}:{password}@{host}:{port}/{db_name}", echo=echo)


def populate_ratings_table(session: Session, letterboxd_user_id: int, ratings: Ratings) -> None:
    """
    Assigns `letterboxd_user_id` to all the entries in `ratings`, and inserts
    the result into the table `ratings`.

    Args:
        `session`: A sqlalchemy `Session`.
        `letterboxd_user_id`: An `id` from the table `letterboxd_users`.
        `ratings`: A sequence of `(original_title, release_year, rating)`.
    """
    # The psycopg (DBAPI) cursor is used to be insert `list[tuple]` directly instead of `list[dict]`
    cur = session.connection().connection.cursor()
    populate_temp_ratings_table = ("""
        INSERT INTO ratings (letterboxd_user_id, original_title, release_year, rating, imdb_id) 
        Values (%s, %s, %s, %s, NULL)"""
    )
    ratings_with_ids = [(letterboxd_user_id, *rating) for rating in ratings]
    cur.executemany(populate_temp_ratings_table, ratings_with_ids)
    session.commit()
    print("imdb_ids in ratings before filling: ", session.scalars(select(Rating.imdb_id)).all())


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
    print("imdb_ids in ratings after filling: ", session.scalars(select(Rating.imdb_id)).all())


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
    ratings_values = np.empty((m,))
    feature_vectors = np.empty((m,), dtype=np.ndarray)
    for i, row in enumerate(rows):
        features, rating = row
        # `features` are already `np.ndarray`s
        feature_vectors[i] = features
        ratings_values[i] = rating
    return (feature_vectors, ratings_values)


def get_k_nearest_neighbor_imdb_ids(session: Session, representative_features: list[float]) -> list[str]:
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


def get_recommendation_imdb_ids(session: Session, username: str, ratings: Ratings) -> list[str]:
    """
    Retrieves `K` `imdb_id`s of movies recommended based on `ratings`.

    Args:
        `session`: A sqlalchemy `Session`.
        `ratings`: A sequence of `(original_title, release_year, rating)`.

    Returns:
        `K` `imdb_id`s

    Raises:
        `NoDataException` 
        `UserInsertionException`
    """

    with add_letterboxd_user(session, username, ratings) as letterboxd_user_id:
        feature_vectors, rating_values = get_features_and_ratings(session, letterboxd_user_id)
        if len(feature_vectors) == 0:
            raise NoDataException()

        representative_index = find_representative_movie(feature_vectors, rating_values)

        # `np.ndarray` must be converted into `list[float]` for insertion into the DB.
        rep_features = list(feature_vectors[representative_index])
        recommendation_imdb_ids = get_k_nearest_neighbor_imdb_ids(
            session, rep_features
        )
        return recommendation_imdb_ids


def get_expiration_timestamp(num_ratings: int) -> datetime.datetime:
    """
    Computes a timezone independent, expiration timestamp for a user's `Recommendation`
    proportional to `num_ratings`. 

    Args: 
        `num_ratings`: The number of user ratings scraped from Letterboxd.

    Returns:
        An expiration timestamp.
    """
    # Feel free to adjust these values if they are too easygoing or harsh
    base_recommendation_ttl_hrs = 0.5
    recommendation_ttl_hrs_per_100_ratings = 1

    current_timestamp = datetime.datetime.now()
    expiration_timestamp = current_timestamp + datetime.timedelta(
        hours=
        base_recommendation_ttl_hrs
        + (recommendation_ttl_hrs_per_100_ratings * (num_ratings / 100))
    )
    return expiration_timestamp


def cache_recommendation(
        session: Session, 
        username: str, 
        num_ratings: int, 
        recommendation_imdb_ids: list[str],
        prev_recommendation_has_expired: bool
) -> None:
    """
    Caches a `Recommendation` for `username` that has an expiration timestamp proportional to 
    `num_ratings`. If `prev_recommendation_has_expired` is `True`, then the previous 
    `Recommendation`one is updated. Otherwise, a new `Recommendation` is created.
    
    The proportional expiration timstamp is utilized because of the assumption: as 
    `num_ratings` increase, future ratings will have a smaller impact on `username`'s 
    `Recommendation`. Thus, `Recommendation`s of `username`s with higher `num_ratings` will 
    take longer to expire than `Recommendation`s of `username`s with lower `num_ratings`.

    Args:
        `session`: A sqlalchemy `Session`.
        `username`: A Letterboxd username.
        `num_ratings`: The number of ratings scraped from `username`'s account.
        `recommendation_imdb_ids`: The `imdb_id`s of the `Recommendation`.
        `prev_recommendation_has_expired`: True if a `Recommendation` for 
            `username` exists, but it has expired.     
    """
    assert len(recommendation_imdb_ids) == K

    data = {}
    data["expiration_timestamp"] = get_expiration_timestamp(num_ratings),
    for i, imdb_id in enumerate(recommendation_imdb_ids):
        data[f"imdb_id_{i + 1}"] = imdb_id

    if prev_recommendation_has_expired:
        stmt = update(Recommendation).where(Recommendation.username.like(username))
    else:
        data["username"] = username
        stmt = insert(Recommendation)

    session.execute(stmt.values(data))
    session.commit()

def delete_expired_recommendations(engine: Engine) -> None:
    """
    Deletes entries from the table `recommendations` where the `expiration_timestamp` 
    is older than the current time.

    Args:
        `engine`: A sqlalchemy `Engine`.
    """
    with Session(engine) as session:
        session.execute(
                delete(Recommendation)
                .where(Recommendation.expiration_timestamp < datetime.datetime.now())
                )
        session.commit()


def delete_recommendations(engine: Engine) -> None:
    """
    Deletes all entries from `recommendations`.

    Args:
        `engine`: A sqlalchemy `Engine`.
    """
    with Session(engine) as session:
        session.execute(delete(Recommendation))
        session.commit()


def get_movies(session: Session, imdb_ids: list[str]) -> list[Movie]:
    """
    Retrieves the `Movie`s associated with `imdb_ids`.

    Args:
        `session`: A sqlalchemy `Session`.
        `imdb_ids`: The `imdb_id`s of the `Movie`s to retrieve.
    """
    cur = session.scalars(
            select(Movie)
            .where(Movie.imdb_id.in_(imdb_ids))
            )
    return list(cur.all())


def cache_trailer_ids(session: Session, imdb_ids: list[str], trailer_ids: list[str]) -> None:
    """
    Updates the `trailer_id` of entries of table `movies` corresponding to `imdb_ids`,
    with the values in `trailer_ids`.

    Args:
        `session`: A sqlalchemy `Session`.
        `imdb_ids`: The `imdb_id`s of entries in `movies` with `NULL` `trailer_id`s. 
        `trailer_ids`: The YouTube trailer video ids of the movies corresponding to `imdb_ids`.
    """
    # The psycopg (DBAPI) cursor is used to be insert `list[tuple]` directly instead of `list[dict]`
    cur = session.connection().connection.cursor()
    data = list(zip(trailer_ids, imdb_ids))
    cur.executemany("""UPDATE movies SET trailer_id = %s WHERE imdb_id = %s""", data)
    session.commit()


def get_cached_recommendation(session: Session, username: str) -> Recommendation | None:
    """
    Args:
        `session`: A sqlalchemy `Session`.
        `username`: A Letterboxd username.
    Returns:
        `username`'s cached `Recommendation` (even if it expired), or `None`.
    """
    recommendation = session.scalar(
            select(Recommendation)
            .where(Recommendation.username == username)
            )
    return recommendation


def extract_imdb_ids_from_recommendation(recommendation: Recommendation) -> list[str]:
    """
    Args:
        `recommendation`: The `Recommendation` to extract `imdb_id`s from.
    Returns:
        The `imdb_id`s from `recommendation`.
    """
    # This is a more flexible way of extracting the imdb_ids, if ever needed
    # imdb_id_attrs = [attr for attr in dir(recommendation) if attr.startswith("imdb_id")]
    # imdb_ids = [recommendation.__getattribute__(attr) for attr in imdb_id_attrs]

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


def is_expired(recommendation: Recommendation) -> bool:
    """
    Args:
        `recommendation`: The `Recommendation` check for expiration.
    Returns:
        `True` if `recommendation`'s `expiration_timestamp` is older than the current time.
    """
    return recommendation.expiration_timestamp < datetime.datetime.now();


def mock_recommendation_system():
    engine = get_engine()
    ratings = [
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
    username = 'username' 


    with Session(engine) as session:
        print("Getting recommendation imdb_ids...")
        try:
            recommendation_imdb_ids = get_recommendation_imdb_ids(session, username, ratings)
        except NoDataException:
            print("This shouldn't have happened part 1")
            return
        except UserInsertionException:
            print("This shouldn't have happened part 2")
            return
        assert len(recommendation_imdb_ids) == 10

        print("Pre-caching recommendation...")
        print(get_cached_recommendation(session, username))

        print("Caching recommendation...")
        cache_recommendation(session, username, len(ratings), recommendation_imdb_ids, False)

        print("Post-caching recommendation...")
        print(get_cached_recommendation(session, username))

        print("Post-expiration recommendation...")
        # Simulate recommendation expiration
        session.execute(delete(Recommendation))
        session.commit()
        print(get_cached_recommendation(session, username))

        print("Getting corresponding movies...")
        movies = get_movies(session, recommendation_imdb_ids)
        print("Initial movie trailer_ids:")
        print([movie.trailer_id for movie in movies])

        print("Scraping trailer ids...")
        trailer_ids = [
                'BbzwLMIgcNQ', 'sU_SQo1wbos', 'pZEvB2z644U', 'PFB-M1suyuY', 
                'OTbhQ0ct1as', 'ZK92E588K-0', '1NIXWgBkJNU', 'GLEY5ea3HjU', 
                'EIhlE3lfu6w', '0t-xZOwFHjE'
                ]
        print(trailer_ids)

        print("Caching trailer ids...")
        cache_trailer_ids(session, recommendation_imdb_ids, trailer_ids)

        print("Post-caching movie trailer_ids:")
        movies = get_movies(session, recommendation_imdb_ids)
        print([movie.trailer_id for movie in movies])


if __name__ == "__main__":
    mock_recommendation_system()
    
