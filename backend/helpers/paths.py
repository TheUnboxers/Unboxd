import os
from enum import Enum


class Path(str, Enum):
    DATA_FOLDER = os.path.join(
            os.path.abspath(os.path.dirname(os.path.abspath(__file__))), "..", "data"
            )
    MOVIE_DATASET_FOLDER = os.path.join(DATA_FOLDER, "movie_dataset")
    MOVIES_FOLDER = os.path.join(DATA_FOLDER, "movies")
    TRIMMED_MOVIES_FOLDER = os.path.join(DATA_FOLDER, "trimmed_movies")
    PREPROCESSED_MOVIES_FOLDER = os.path.join(DATA_FOLDER, "preprocessed_movies")
    REDUCED_PREPROCESSED_MOVIES_FOLDER = os.path.join(
        DATA_FOLDER, "reduced_preprocessed_movies"
    )
    RATINGS_FOLDER = os.path.join(DATA_FOLDER, "ratings")

