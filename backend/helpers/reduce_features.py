import os
import sys
import warnings
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import TruncatedSVD

if os.getcwd().endswith("helpers"):
    from paths import Path
    from init_dataset import read_csvs_to_df, write_df_to_csvs
    from preprocess_features import preprocess_movie_dataset, COLS_TO_LOAD
else:
    from .paths import Path
    from .init_dataset import read_csvs_to_df, write_df_to_csvs
    from .preprocess_features import preprocess_movie_dataset, COLS_TO_LOAD


COL_TO_DUMP = "features"
N_COMPONENTS = 90
"""
90 components explain 80% of the total variance. This is the length of the feature
vectors stored in the preprocessed_movies table in the database. To reflect changes
to this value, the database should be reinitialized after recreating the 
`reduced_preprocessed_movies` dataset.
"""


def reduce_features_and_normalize(df: pd.DataFrame, n_components: int | None) -> pd.DataFrame:
    """
    Performs feature reduction and normalization on the preprocessed movies dataset, `df`,
    an and plots the results of all possible value of `n_components` if `n_components` 
    is not specified.
    Args:
        `df`: The preprocessed movies dataset.
        `n_components`: The number of components to reduce down to.
    Returns:
        A `DataFrame` of `imdb_id`s and reduced, normalized feature vectors.
    """
    print("Performing feature reduction...")
    saved_cols = ["imdb_id"]
    saved_col_values = df[saved_cols].values
    df.drop(columns=saved_cols, inplace=True)

    plot_results = False
    if n_components is None:
        n_components = len(df)
        plot_results = True

    # Ignore warning about sparse data being converted to dense 
    warnings.filterwarnings("ignore")
    feature_reducer = TruncatedSVD(n_components)
    reduced_data = feature_reducer.fit_transform(df)

    if plot_results:
        plot_explained_variance_ratios(feature_reducer)

    df = pd.DataFrame(saved_col_values, columns=saved_cols)

    print("Creating and normalizing features vectors...")
    reduced_data_rows = [
        list(normalize(reduced_data[i])) for i in range(len(reduced_data))
    ]

    df[COL_TO_DUMP] = reduced_data_rows
    return df


def plot_explained_variance_ratios(fit_transformed_feature_reducer: TruncatedSVD) -> None:
    """
    Plots the cumulative expained variance ratios of a fit-transformed feature 
    reducer as a function of the number of components needed to obtain the ratios.
    """
    print("Plotting results...")
    explained_variance_ratios = (
        fit_transformed_feature_reducer.explained_variance_ratio_
    )
    total = 0
    cumumlative_explained_variance_ratios = []
    for ratio in explained_variance_ratios:
        cumumlative_explained_variance_ratios.append(total)
        total += ratio
    num_components = [i + 1 for i in range(len(cumumlative_explained_variance_ratios))]
    plt.scatter(num_components, cumumlative_explained_variance_ratios)
    plt.ylabel("cumulative explained variance ratios")
    plt.xlabel("n components")
    plt.show()


def normalize(v: np.ndarray) -> np.ndarray:
    """
    Normalizes the vector `v`.
    """
    magnitude = np.linalg.norm(v)
    if magnitude == 0:
        return v
    return v / magnitude


def main():
    if "preprocess" in sys.argv:
        df = read_csvs_to_df(Path.MOVIES_FOLDER, COLS_TO_LOAD)
        df = preprocess_movie_dataset(df)
    else:
        df = read_csvs_to_df(Path.PREPROCESSED_MOVIES_FOLDER)
    df.info()

    if "plot" in sys.argv:
        n_components = None
    else:
        n_components = N_COMPONENTS
    df = reduce_features_and_normalize(df, n_components)
    df.info()

    if "plot" not in sys.argv:
        write_df_to_csvs(df, Path.REDUCED_PREPROCESSED_MOVIES_FOLDER, [COL_TO_DUMP])


if __name__ == "__main__":
    main()

