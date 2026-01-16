import os
import shutil
import json
import math
from typing import Iterable, Any, Callable, Hashable, Sequence
from multiprocessing import Pool
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from pydantic import BaseModel

if os.getcwd().endswith("helpers"):
    from paths import Path
else:
    from .paths import Path


def folder_paths(folder: str) -> Iterable[str]:
    """
    Yields the absolute paths of every file in `folder`.
    """
    filenames = os.listdir(folder)
    for filename in filenames:
        yield os.path.join(folder, filename)


def reset_folder(folder: str) -> None:
    """
    Creates an empty directory at `folder`, discarding any previous contents.
    """
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)


def read_csv_to_df(info: tuple[str, dict[Hashable, Callable]]) -> pd.DataFrame:
    """
    Reads the csv file to a `DataFrame` given the `(path, converters)` specified in 
    `info`. `path` is the csv file to read from, and `converters` are a mapping
    of column names to functions to use to load the associated columns during 
    `DataFrame` creation. An index is not created in the resulting `DataFrame`.
    Args:
        `info`: `(path, converters)`
    Returns:
        The `DataFrame` created using `info`. 
    """
    path, converters = info
    return pd.read_csv(path, index_col=False, converters=converters)


def read_csvs_to_df(csv_dir: str, cols_to_load: Sequence[Hashable] = []) -> pd.DataFrame:
    """
    Creates a DataFrame from the csvs files in `csv_dir`, and loads the stringified JSON
    objects in `cols_to_load`.
    Args:
        `csv_dir`: A folder containing the csv files to load.
        `cols_to_load`: The names of columns with stringified JSON values.
    Returns:
        The `DataFrame` resulting from reading `csv_dir`, and loading `cols_to_load`.
    """
    print(f"Reading dataset splits...")
    paths = folder_paths(csv_dir)
    converters = {col: json.loads for col in cols_to_load}
    # Multiple processes perform better than multiple threads for reading the splits
    with Pool(4) as p:
        df = pd.concat(p.map(read_csv_to_df, [(path, converters) for path in paths]))

    # This fixes the disappearing `original_title`s of movies literally named "None"
    if "original_title" in df.columns:
        df["original_title"] = df["original_title"].fillna("None")

    return df


def df_splits(
    df: pd.DataFrame, splits_dir: str, cols_to_dump: list[str], row_limit: int
) -> Iterable[tuple[pd.DataFrame, str, list[str]]]:
    """
    Yields the information needed to save splits of `df` independent of each other.
    Args: 
        `df`: The `DataFrame` to create splits of.
        `splits_dir`: The folder to save the splits in.
        `cols_to_dump`: The names of columns to stringify as JSON.
        `row_limit`: The maximum number of rows per csv file.
    Returns:
        An `Iterable` of `(df_split, filename, cols_to_dump)`.
    """
    df_len = len(df)
    num_splits = math.ceil(df_len / float(row_limit))

    print(f"Saving dataset into {num_splits} splits...")
    for i in range(num_splits):
        start, end = i * row_limit, min(df_len, (i + 1) * row_limit)
        df_split = df.iloc[start:end]
        filename = os.path.join(splits_dir, f"split_{i + 1}.csv")
        yield (df_split, filename, cols_to_dump)


def write_split_to_csv(split: tuple[pd.DataFrame, str, list[str]]) -> None:
    """
    Writes a csv file given the information in `split`.
    Args: 
        `split`: `(df_split, filename, cols_to_dump)`
    """
    df_split, filename, cols_to_dump = split
    for col in cols_to_dump:
        df_split.loc[:, (col)] = df_split[col].apply(json.dumps)
    df_split.to_csv(filename, index=False, chunksize=10000)


def write_df_to_csvs(
    df: pd.DataFrame,
    splits_dir: str,
    cols_to_dump: list[str] = [],
    row_limit: int = 7500,
) -> None:
    """
    Writes `df` into smaller csv files.
    Args: 
        `df`: The `DataFrame` to save splits of.
        `splits_dir`: The folder to reset, and then write the splits to.
        `cols_to_dump`: The names of columns to stringify as JSON.
        `row_limit`: The maximum number of rows per csv file.
    """
    reset_folder(splits_dir)
    # Multiple threads perform better than multiple processes for writing the splits
    with ThreadPoolExecutor(4) as p:
        p.map(write_split_to_csv, df_splits(df, splits_dir, cols_to_dump, row_limit))


COLS_TO_DUMP = [
    "genres",
    "spoken_languages",
    "keywords",
    "directors",
    "writers",
    "actors",
    "companies",
]


class Movie(BaseModel):
    """
    The data extracted for each movie from the international movies dataset.
    https://www.kaggle.com/datasets/pavan4kalyan/imdb-dataset-of-600k-international-movies
    """
    original_title: str
    release_year: int
    imdb_id: str
    poster_url: str | None
    runtime_seconds: int | None
    certificate_rating: str | None
    genres: list[str]
    spoken_languages: list[str]
    plot: str | None
    keywords: list[str]
    directors: list[str]
    writers: list[str]
    actors: list[str]
    companies: list[str]


def safe_get(d, keys: list[str], default=None):
    """
    Safely navigate nested `dict`s.
    """
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key, default)
        else:
            return default
    return d


def safe_get_list(d: dict, keys_to_list: list[str], list_keys: list[str]) -> list[Any]:
    """
    Safely navigates the nested `dict`s in `d` to a `list` and extracts values 
    from its nested `dict` entries.
    """
    return [safe_get(entry, list_keys) for entry in safe_get(d, keys_to_list, [])]


def strs(xs: list[Any]) -> list[str]:
    """
    Filters out non-`str` elements from a list.
    """
    return [x for x in xs if isinstance(x, str)]


def extract_movie_data(path: str) -> list[Movie]:
    """
    Extracts the data from a json batch of the international movies dataset at `path`.
    https://www.kaggle.com/datasets/pavan4kalyan/imdb-dataset-of-600k-international-movies
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    movies: list[Movie] = []
    for movie in data:
        title = safe_get(movie, ["titleText", "text"])
        original_title = safe_get(movie, ["originalTitleText", "text"], title)
        if not original_title:
            continue

        release_year = safe_get(movie, ["releaseYear", "year"])
        if release_year is None:
            continue

        imdb_id = safe_get(movie, ["id"])
        if not imdb_id:
            continue

        poster_url = safe_get(movie, ["primaryImage", "url"])

        runtime_seconds = safe_get(movie, ["runtime", "seconds"])

        certificate_rating = safe_get(movie, ["certificate", "rating"])

        genres = safe_get_list(movie, ["genres", "genres"], ["text"])

        spoken_languages = safe_get_list(
            movie, ["spokenLanguages", "spokenLanguages"], ["text"]
        )

        plot = safe_get(movie, ["plot", "plotText", "plainText"], None)

        keywords = safe_get_list(movie, ["keywords", "edges"], ["node", "text"])

        directors, writers, actors = [], [], []
        principal_credits = safe_get(movie, ["principalCredits"], [])
        categories = {"Director": directors, "Writers": writers, "Stars": actors}
        for pc in principal_credits:
            category = safe_get(pc, ["category", "text"])
            if category in categories:
                names = safe_get_list(pc, ["credits"], ["name", "nameText", "text"])
                categories[category].extend(names)

        companies = safe_get_list(
            movie,
            ["companyCredits", "edges"],
            ["node", "company", "companyText", "text"],
        )

        movies.append(
            Movie(
                original_title=original_title,
                release_year=release_year,
                imdb_id=imdb_id,
                runtime_seconds=runtime_seconds,
                certificate_rating=certificate_rating,
                genres=strs(genres),
                spoken_languages=strs(spoken_languages),
                plot=plot,
                keywords=strs(keywords),
                directors=strs(directors),
                writers=strs(writers),
                actors=strs(actors),
                companies=strs(companies),
                poster_url=poster_url,
            )
        )
    return movies


def filter_repeat_title_and_year(movies: list[Movie]) -> list[Movie]:
    """
    Filters out movies with repeat occurences of `original_title` and `release_year`.
    """
    title_year = set()
    filtered_movies = []
    for movie in movies:
        entry = (movie.original_title, movie.release_year)
        if entry not in title_year:
            title_year.add(entry)
            filtered_movies.append(movie)
    return filtered_movies


def init_movies_dataset() -> pd.DataFrame:
    """
    Extracts the data from all the json files of the international movies dataset.
    https://www.kaggle.com/datasets/pavan4kalyan/imdb-dataset-of-600k-international-movies
    """
    print("Initializing movies dataset...")
    with Pool(4) as p:
        movies_batches = p.map(
            extract_movie_data, folder_paths(Path.MOVIE_DATASET_FOLDER)
        )

    movies: list[Movie] = []
    for movies_batch in movies_batches:
        movies.extend([movie for movie in movies_batch])

    filtered_movies = filter_repeat_title_and_year(movies)
    dict_movies = [dict(movie) for movie in filtered_movies]
    return pd.DataFrame(dict_movies)
    

def main():
    df = init_movies_dataset()
    df.info()
    print("Note: the empty list values of features like keywords do not appear as null")
    write_df_to_csvs(df, Path.MOVIES_FOLDER, COLS_TO_DUMP)


if __name__ == "__main__":
    main()
