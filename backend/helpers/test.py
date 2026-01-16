import os
import numpy as np

if os.getcwd().endswith("helpers"):
    from models import Movie
else:
    from .models import Movie


dummy_data = [
    Movie(
        movieId="1000001",
        name="Barbie",
        year="2023",
        genre=["Comedy", "Fantasy"],
        description="Barbie and Ken are having the time of their lives in the colorful and seemingly perfect world of Barbie Land. However, when they get a chance to go to the real world, they soon discover the joys and perils of living among humans.",
        posterURL="https://a.ltrbxd.com/resized/film-poster/2/7/7/0/6/4/277064-barbie-0-230-0-345-crop.jpg?v=1b83dc7a71",
        letterboxdURL="https://letterboxd.com/film/barbie/",
        trailerID="Ml0bijl4IoA",
    ),
    Movie(
        movieId="1000002",
        name="Oppenheimer",
        year="2023",
        genre=["Drama", "History"],
        description="The story of J. Robert Oppenheimer's role in the development of the atomic bomb during World War II.",
        posterURL="https://a.ltrbxd.com/resized/film-poster/7/8/4/3/2/8/784328-oppenheimer-0-230-0-345-crop.jpg?v=e3c6e7a32c",
        letterboxdURL="https://letterboxd.com/film/oppenheimer-2023/",
        trailerID="pXTvDfOjbh0",
    ),
    Movie(
        movieId="1000003",
        name="Parasite",
        year="2019",
        genre=["Comedy", "Thriller", "Drama"],
        description="All unemployed, Ki-taek's family takes peculiar interest in the wealthy and glamorous Parks for their livelihood until they get entangled in an unexpected incident.",
        posterURL="https://a.ltrbxd.com/resized/film-poster/4/2/6/4/0/6/426406-parasite-0-230-0-345-crop.jpg?v=8f5653f710",
        letterboxdURL="https://letterboxd.com/film/parasite-2019/",
        trailerID="bM9QabAojCg",
    ),
    Movie(
        movieId="1000004",
        name="Everything Everywhere All at Once",
        year="2022",
        genre=["Science Fiction", "Adventure", "Comedy", "Action"],
        description="An aging Chinese immigrant is swept up in an insane adventure, where she alone can save what's important to her by connecting with the lives she could have led in other universes.",
        posterURL="https://a.ltrbxd.com/resized/film-poster/4/7/4/4/7/4/474474-everything-everywhere-all-at-once-0-230-0-345-crop.jpg?v=281f1a041e",
        letterboxdURL="https://letterboxd.com/film/everything-everywhere-all-at-once",
        trailerID="wxN1T1uxQ2g",
    ),
    Movie(
        movieId="1000005",
        name="Fight Club",
        year="1999",
        genre=["Drama"],
        description='A ticking-time-bomb insomniac and a slippery soap salesman channel primal male aggression into a shocking new form of therapy. Their concept catches on, with underground "fight clubs" forming in every town, until an eccentric gets in the way and ignites an out-of-control spiral toward oblivion.',
        posterURL="https://a.ltrbxd.com/resized/film-poster/5/1/5/6/8/51568-fight-club-0-230-0-345-crop.jpg?v=768b32dfa4",
        letterboxdURL="https://letterboxd.com/film/fight-club",
        trailerID="dfeUzm6KF4g",
    ),
    Movie(
        movieId="1000006",
        name="La La Land",
        year="2016",
        genre=["Drama", "Comedy", "Music", "Romance"],
        description="Mia, an aspiring actress, serves lattes to movie stars in between auditions and Sebastian, a jazz musician, scrapes by playing cocktail party gigs in dingy bars, but as success mounts they are faced with decisions that begin to fray the fragile fabric of their love affair, and the dreams they worked so hard to maintain in each other threaten to rip them apart.",
        posterURL="https://a.ltrbxd.com/resized/film-poster/2/4/0/3/4/4/240344-la-la-land-0-230-0-345-crop.jpg?v=053670ff84",
        letterboxdURL="https://letterboxd.com/film/la-la-land/",
        trailerID="0pdqf4P9MB8",
    ),
]


def create_mock_data() -> tuple[
    np.ndarray, list[float], set[str], np.ndarray, list[str]
]:
    """
    Creates sample data structures needed by `recommender.py` for testing
    """
    # Ensure all feature vectors are NumPy arrays for compatibility with recommender.py
    user_movies = np.array(
        [
            [0.9, 0.1, 0.7],  # Movie A
            [0.1, 0.9, 0.2],  # Movie B
        ]
    )
    weights = [0.8, 0.4]
    user_movie_ids = set(
        ["1000001", "1000002"]
    )  # Mock watched movies (IDs must match dummy_data)
    all_movies = np.array(
        [
            [0.9, 0.1, 0.7],
            [0.1, 0.9, 0.2],
            [0.85, 0.15, 0.8],
            [0.2, 0.8, 0.3],
            [0.5, 0.5, 0.5],
            [0.9, 0.1, 0.9],
        ]
    )
    all_movie_ids = [
        "1000001",
        "1000002",
        "1000003",
        "1000004",
        "1000005",
        "1000006",
    ]
    return user_movies, weights, user_movie_ids, all_movies, all_movie_ids


def get_mock_movie_metadata(recs: dict[str, float]) -> list[Movie]:
    """
    Converts (movie id, score) tuples from the recommender
    into full `Movie` objects using dummy data for metadata lookup
    """
    # Create a mapping of movie_id to the full Movie object from your dummy data
    id_to_movie = {m.movieId: m for m in dummy_data}

    final_recs = []
    for movie_id, score in recs.items():
        if movie_id in id_to_movie:
            # Create a copy and update the similarity score field
            movie = id_to_movie[movie_id].model_copy(update={"similarityScore": score})
            final_recs.append(movie)
    return final_recs

