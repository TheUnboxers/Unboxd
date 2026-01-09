import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler

if os.getcwd().endswith("helpers"):
    from paths import Path
    from init_dataset import read_csvs_to_df, write_df_to_csvs, COLS_TO_DUMP
else:
    from .paths import Path
    from .init_dataset import read_csvs_to_df, write_df_to_csvs, COLS_TO_DUMP


COLS_TO_LOAD = COLS_TO_DUMP


def efficient_multi_hot_encode(df: pd.DataFrame, col: str, k: int) -> pd.DataFrame:
    """
    Applies Multi-Hot Encoding, retaining only the Top K most frequent items,
    and converts the resulting DataFrame to a sparse format for memory efficiency.
    """
    print(f"  -> Processing '{col}' with Top K={k} filter...")

    # 1. Identify Top K most frequent items
    # df[col].explode() expands the list column into individual rows
    item_counts = df[col].explode().value_counts()
    top_k_items = set(item_counts.head(k).index)

    # 2. Filter the lists in the DataFrame to only keep Top K items
    # Items not in the Top K set are discarded.
    df[col] = df[col].apply(lambda x: [item for item in x if item in top_k_items])

    # 3. Perform Multi-Hot Encoding
    mlb = MultiLabelBinarizer()
    encoded_data = mlb.fit_transform(df[col])

    # 4. Create DataFrame and convert to Sparse Data Type (Crucial for memory)
    encoded_df = pd.DataFrame(
        encoded_data, columns=[f"{col}_{c}" for c in mlb.classes_]
    ).astype(pd.SparseDtype("uint8", 0))

    # 5. Concatenate
    df = pd.concat([df.drop(columns=[col]), encoded_df], axis=1)

    return df


def preprocess_movie_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocesses the movie dataset, `df`.
    """
    print("Starting feature numerization and scaling for movie dataset...")

    # Drop irrelevant columns and reset index
    df.drop(columns=["original_title", "poster_url"], inplace=True, errors="ignore")
    df.reset_index(drop=True, inplace=True)

    # --- A. Multi-Hot Encoding for List Features (MODIFIED FOR EFFICIENCY) ---
    list_cols_k = {
        "genres": 50,
        "directors": 50,
        "writers": 50,
        "actors": 50,
        "companies": 50,
        "keywords": 75,
        "spoken_languages": 50,
    }

    for col, k in list_cols_k.items():
        df = efficient_multi_hot_encode(df, col, k)

    print("Multi-Hot Encoding complete using Top K filter and Sparse Data.")

    # --- B. One-Hot Encoding for Categorical Feature ---
    df["certificate_rating"] = df["certificate_rating"].fillna("Unknown")
    # Set sparse=True to use SparseDtype, saving memory
    df = pd.get_dummies(df, columns=["certificate_rating"], prefix="cert", sparse=True)
    print(f"One-Hot Encoding complete for certificate_rating.")

    # --- C. TF-IDF Vectorization for Text Feature ---
    # Use direct assignment to avoid FutureWarning/chained assignment
    df["plot"] = df["plot"].fillna("")
    tfidf = TfidfVectorizer(stop_words="english", min_df=50, max_features=75)
    tfidf_matrix = tfidf.fit_transform(df["plot"])

    # This keeps the resulting DataFrame columns sparse and memory-efficient.
    tfidf_df = pd.DataFrame.sparse.from_spmatrix(
        tfidf_matrix, columns=tfidf.get_feature_names_out()
    )
    tfidf_df.columns = [f"plot_tfidf_{col}" for col in tfidf_df.columns]

    df = df.drop(columns=["plot"]).reset_index(drop=True)
    tfidf_df = tfidf_df.reset_index(drop=True)
    df = pd.concat([df, tfidf_df], axis=1)
    print(f"TF-IDF Vectorization complete for plot.")

    # --- D. Scaling Numeric Features ---
    df["runtime_seconds"] = df["runtime_seconds"].fillna(df["runtime_seconds"].mean())

    scaler = StandardScaler()
    numeric_cols = ["release_year", "runtime_seconds"]
    df[numeric_cols] = scaler.fit_transform(df[numeric_cols])
    print(f"Numeric Feature Scaling complete.")

    return df


def main():
    df = read_csvs_to_df(Path.MOVIES_FOLDER, COLS_TO_LOAD)
    df = preprocess_movie_dataset(df)
    df.info()
    write_df_to_csvs(df, Path.PREPROCESSED_MOVIES_FOLDER)


if __name__ == "__main__":
    main()
