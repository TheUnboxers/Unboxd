import os

from sqlalchemy import text, Index
from sqlalchemy.orm import Session
from psycopg import sql
from tqdm import tqdm 
import pandas as pd

from paths import Path
from init_dataset import (
    folder_paths,
    read_csvs_to_df,
    write_df_to_csvs,
    init_movies_dataset,
    COLS_TO_DUMP as COLS_TO_LOAD,
)
from preprocess_features import preprocess_movie_dataset
from reduce_features import reduce_features_and_normalize, N_COMPONENTS, COL_TO_DUMP
from db_models import (
    Base, 
    Movie, 
    Recommendation, 
    MOVIES_TABLE_NAME, 
    PREPROCESSED_MOVIES_TABLE_NAME
)
from db import get_engine


def create_trimmed_movies_dataset(movies: pd.DataFrame) -> None:
    """
    Prepares the columns of the movies dataset needed by the DB for the `movies`
    table and saves the result.

    Args:
        `movies`: The movies dataset.
    """
    print("Preparing trimmed_movies dataset...")
    # Ensure the necessary columns exist and are ordered exactly like the `Movie` orm model
    trimmed_movies = movies
    trimmed_movies["trailer_id"] = None
    movie_model_columns_ordering = [
        "imdb_id",
        "original_title",
        "release_year",
        "trailer_id",
        "genres",
        "poster_url",
        "plot",
    ]
    trimmed_movies = trimmed_movies.reindex(movie_model_columns_ordering, axis=1)
    trimmed_movies.info()
    write_df_to_csvs(trimmed_movies, Path.TRIMMED_MOVIES_FOLDER, cols_to_dump=["genres"])


def ensure_existence_of_trimmed_movies_dataset() -> pd.DataFrame | None:
    """
    Ensures the existence of the trimmed_movies dataset (i.e. the desired 
    columns of the movies dataset).

    Returns:
        The movies dataset.
    """
    movies = None
    if os.path.isdir(Path.TRIMMED_MOVIES_FOLDER):
        print("Detected the trimmed_movies dataset")
    elif os.path.isdir(Path.MOVIES_FOLDER):
        print("Detected the movies dataset")
        movies = read_csvs_to_df(Path.MOVIES_FOLDER, cols_to_load=COLS_TO_LOAD)
    else:
        print("Did not detect the trimmed_movies dataset or the movies dataset")
        movies = init_movies_dataset()
    if movies is not None:
        create_trimmed_movies_dataset(movies.copy())
    return movies


def ensure_existence_of_reduced_preprocessed_movies_dataset(movies: pd.DataFrame | None):
    """
    Ensures the existence of the reduced_preprocessed_movies dataset.

    Args:
        `movies`: The movies dataset.
    """
    if os.path.isdir(Path.REDUCED_PREPROCESSED_MOVIES_FOLDER):
        print("Detected the reduced_preprocessed_movies dataset")
        reduced_preprocessed_movies = None
    elif os.path.isdir(Path.PREPROCESSED_MOVIES_FOLDER):
        print("Detected the preprocessed_movies dataset")
        preprocessed_movies = read_csvs_to_df(Path.PREPROCESSED_MOVIES_FOLDER)
        reduced_preprocessed_movies = reduce_features_and_normalize(preprocessed_movies, N_COMPONENTS)
    else:
        print("Did not detect the reduced_preprocessed_movies dataset or the preprocessed_movies dataset")
        if movies is None:
            movies = init_movies_dataset()
        preprocessed_movies = preprocess_movie_dataset(movies)
        reduced_preprocessed_movies = reduce_features_and_normalize(preprocessed_movies, N_COMPONENTS)
    if reduced_preprocessed_movies is not None:
        write_df_to_csvs(
                reduced_preprocessed_movies, 
                Path.REDUCED_PREPROCESSED_MOVIES_FOLDER, 
                cols_to_dump=[COL_TO_DUMP]
                )


def copy_to_table_from_csvs(session: Session, table_name: str, folder_path: Path) -> None:
    """
    Copies to the DB table specified by `table_name` from the csv files located in 
    `folder_path`. This is the fastest method of adding the data from `folder_path`.

    Args:
        `session`: A sqlalchemy `Session`.
        `table_name`: The name of the table to copy the data to.
        `folder_path`: The path to the folder containing the data to copy.
    """
    print(f"Copying to {table_name}...")
    cur = session.connection().connection.cursor()
    for path in tqdm(list(folder_paths(folder_path))):
        with open(path, "r") as file:
            with cur.copy(
                    sql.SQL("COPY {} FROM STDIN WITH (FORMAT csv, HEADER true)")
                    .format(sql.Identifier(table_name))
            ) as copy:
                copy.write(file.read())
    session.commit()


def init_db():
    """
    Initializes the database. Creates the pgvector extension, populates the `movies` 
    and `preprocessed_movies` tables, and adds indexes to optimize data retrieval.
    """
    # Log the activity of the DB
    engine = get_engine(echo=True)

    # Create the pgvector extension before creating any tables
    with Session(engine) as session:
        session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        session.commit()

    # Reset all tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
  
    with Session(engine) as session:
        # Initialize `movies` with the trimmed_movies dataset
        copy_to_table_from_csvs(session, MOVIES_TABLE_NAME, Path.TRIMMED_MOVIES_FOLDER)

        # Index on `imdb_id` to optimize user representative k-NN information retrieval
        movie_imdb_id_index = Index("ix_imdb_id", Movie.imdb_id, unique=True)
        movie_imdb_id_index.create(engine)
        session.commit()

        # Index on `original_title` and `release_year` to optimize scraped rating `imdb_id` retrieval
        movie_title_year_index = Index(
            "ix_original_title_release_year",
            Movie.original_title,
            Movie.release_year,
            unique=True,
        )
        movie_title_year_index.create(engine)
        session.commit()

        # Initialize `preprocessed_movies` with the reduced_preprocessed_movies dataset
        copy_to_table_from_csvs(
            session, PREPROCESSED_MOVIES_TABLE_NAME, Path.REDUCED_PREPROCESSED_MOVIES_FOLDER
        )

        # Index on `username` to optimize the checking the cache, and retrieval from it
        recommendation_username_index = Index(
                "ix_username", Recommendation.username, unique=True
                )
        recommendation_username_index.create(engine)


if __name__ == "__main__":
    movies = ensure_existence_of_trimmed_movies_dataset()
    ensure_existence_of_reduced_preprocessed_movies_dataset(movies)
    init_db()

