import os
import time
import requests
from tqdm import tqdm

if os.getcwd().endswith("helpers"):
    from db_models import Movie
else:
    from .db_models import Movie


def get_trailer_search_url(movie: Movie) -> str:
    """Returns the url for searching for `movie_name`'s trailer on YouTube"""
    search_query = "+".join(movie.original_title.split()) + f"+({movie.release_year})+trailer"
    return f"https://www.youtube.com/results?search_query={search_query}"


def get_trailer_id(html: str) -> str:
    # skip content from YouTube Movies & TV bc they only show trailers for non-rated R content w/out signing in
    id_prefix = '"videoRenderer":{"videoId":"'
    id_start = html.find(id_prefix) + len(id_prefix)
    id_end = html.find('"', id_start)
    video_id = html[id_start:id_end]
    return video_id


def scrape_trailer_ids(movies: list[Movie], print_status: bool = False) -> list[str]:
    """Returns the scraped YouTube video ids of the trailers of the movies specified by `movie_names` and `release_years`"""
    if print_status:
        print("starting scraping...")
    trailer_ids = []
    movie_data = tqdm(movies) if print_status else movies
    for movie in movie_data:
        if print_status:
            tqdm.write(f"scraping for {movie.original_title}...")
        video_id = ""
        try:
            response = requests.get(get_trailer_search_url(movie))
            response.raise_for_status()
            html = response.text
            video_id = get_trailer_id(html)
        except Exception as e:
            if print_status:
                tqdm.write(f"error, failed to scrape for {movie.release_year}: {e}")
        trailer_ids.append(video_id)
        time.sleep(2)
    return trailer_ids

