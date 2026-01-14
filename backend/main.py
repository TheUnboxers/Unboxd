import uvicorn
import pandas as pd
import numpy as np
import requests
from ast import literal_eval
from fastapi import FastAPI, BackgroundTasks, HTTPException
from http import HTTPStatus
from fastapi.middleware.cors import CORSMiddleware
from threading import Lock

if __name__ == "__main__":
    from helpers.paths import Path
    from helpers.models import UsernameRequest, Status, Movie
    from helpers.scrape_letterboxd import scrape_ratings, scrape_pfp_url
    from helpers.recommender import recommend_movies
    from helpers.merge_ratings import obtain_ids_and_weights
    from helpers.retrieve_preprocessed import retrieve_data, retrieve_preprocessed_data
    from helpers.test import dummy_data
else:
    from .helpers.paths import Path
    from .helpers.models import UsernameRequest, Status, Movie
    from .helpers.scrape_letterboxd import scrape_ratings, scrape_pfp_url
    from .helpers.recommender import recommend_movies
    from .helpers.merge_ratings import obtain_ids_and_weights
    from .helpers.retrieve_preprocessed import retrieve_data, retrieve_preprocessed_data
    from .helpers.test import dummy_data


scraper_lock = Lock()
status: dict[str, Status] = dict()
recommendations: dict[str, list[Movie]] = dict()

movies = pd.read_csv(Path.MOVIES)
trending_movies = pd.read_csv(Path.MERGED_TRENDING_MOVIES)

complete_preprocessed_trending_movies = pd.read_csv(Path.PREPROCESSED_TRENDING_MOVIES)
indexed_preprocessed_trending_movies = complete_preprocessed_trending_movies.drop(columns=["imdb_id"]).to_numpy()
preprocessed_trending_movies = np.delete(arr=indexed_preprocessed_trending_movies, obj=0, axis=1)
preprocessed_trending_movies_ids = complete_preprocessed_trending_movies["imdb_id"].to_list()

trailers = pd.read_csv(Path.TRENDING_MOVIE_TRAILERS)
trailer_ids = set(trailers["imdb_id"].values)

failed = [
    Status.FAILED_INVALID_USERNAME,
    Status.FAILED_NO_RATINGS,
    Status.FAILED_SCRAPING,
    Status.FAILED_NO_DATA,
    Status.FAILED_NO_RECOMMENDATIONS
]

app = FastAPI()
origins = [
        "http://localhost:3000",
        "http://192.168.11.1:3000"
]
app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
)

def get_movies(recs: dict[str, float]) -> list[Movie]:
    """
    Converts the (movie id : similarity score) mappings from the recommender 
    into full Movie objects using the trending movies dataset
    """
    result = []
    imdb_ids = set(recs.keys())
    for movie in retrieve_data(imdb_ids, trending_movies).itertuples():
        result.append(Movie(
            movieId=movie.imdb_id,
            name=movie.original_title,
            year=int(movie.release_year),
            genre=literal_eval(movie.genres),
            description=movie.plot,
            posterURL=movie.poster_url,
            letterboxdURL=f'https://www.letterboxd.com/imdb/{movie.imdb_id}',
            trailerID=movie.imdb_id if movie.imdb_id in trailer_ids else "",
            similarityScore=recs[movie.imdb_id]
        ))
    return result 

def recommendation_system(username: str): 
    """
    Completes the trending movie recommendation system for the Letterboxd user `username`, 
    updating the `status` of the system for `username` along the way, and storing the
    the result in `recommendations` for `username`
    """
    status[username] = Status.VALIDATING_USERNAME
    profile_response = requests.get(f"https://www.letterboxd.com/{username}/")
    if profile_response.status_code != 200:
        status[username] = Status.FAILED_INVALID_USERNAME
        return

    status[username] = Status.WAITING_FOR_SCRAPER
    with scraper_lock:
        status[username] = Status.SCRAPING_RATINGS
        try:
            ratings = scrape_ratings(username)
        except:
            status[username] = Status.FAILED_SCRAPING
            return
    if len(ratings) == 0:
        status[username] = Status.FAILED_NO_RATINGS
        return

    status[username] = Status.PREPROCESSING_DATA
    user_movie_ids, weights = obtain_ids_and_weights(movies, ratings)
    if len(user_movie_ids) == 0:
        status[username] = Status.FAILED_NO_DATA
        return
    complete_preprocessed_user_movies = retrieve_preprocessed_data(user_movie_ids.copy())
    preprocessed_user_movies = complete_preprocessed_user_movies.drop(columns=["imdb_id"]).to_numpy()

    status[username] = Status.FINDING_RECOMMENDATION
    recs = recommend_movies(
        user_movies=preprocessed_user_movies,
        weights=weights,
        user_movie_ids=user_movie_ids,
        all_movies=preprocessed_trending_movies,
        all_movie_ids=preprocessed_trending_movies_ids,
        k=10
    )
    if len(recs) == 0:
        status[username] = Status.FAILED_NO_RECOMMENDATIONS 
        return
    recommendations[username] = get_movies(recs)

    status[username] = Status.FINISHED
    
    # For testing purposes only - comment out above and uncomment below to use dummy data
    # recommendations[username] = dummy_data
    # status[username] = Status.FINISHED
    
@app.post("/usernames/", status_code=HTTPStatus.ACCEPTED)
def init_system(request: UsernameRequest, background_tasks: BackgroundTasks):
    # Recommendation system has not started or has failed previously - start/restart it
    if request.username not in status or status[request.username] in failed:
        status[request.username] = Status.STARTING
        background_tasks.add_task(recommendation_system, request.username)
    return

@app.get("/status/", response_model=Status)
def check_status(username: str):
    if username not in status:
        raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"the recommendation system has not run for {username}, \
                        post /usernames/ to start it."
        )
    username_status = status[username]
    if username_status in (Status.FAILED_INVALID_USERNAME, Status.FAILED_NO_RATINGS):
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=username_status)
    elif username_status in (Status.FAILED_SCRAPING, Status.FAILED_NO_DATA, Status.FAILED_NO_RECOMMENDATIONS):
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=username_status)
    else:
        return username_status 

@app.get("/movies/", response_model=list[Movie])
def get_recommend_movies(username: str):
    if username not in recommendations:
        raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"The recommendation system is incomplete for {username}, \
                        get /status/ for more info."
        )
    else:
        return recommendations[username]

@app.get("/pfp-urls/", response_model=str)
def get_pfp_url(username: str):
    pfp_url = scrape_pfp_url(username)
    if len(pfp_url) == 0:
        raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Failed to get profile picture URL for Letterboxd user: {username}, \
                        retry if Letterboxd username is valid"
        )
    else:
        return pfp_url

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
