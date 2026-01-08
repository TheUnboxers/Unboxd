import requests
from threading import Lock
from http import HTTPStatus
from contextlib import asynccontextmanager
from typing import Annotated

from sqlalchemy import select
import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler 

from helpers.scrape_letterboxd import scrape_ratings, scrape_pfp_url
from helpers.scrape_trailer_ids import scrape_trailer_ids
from helpers.models import ProperlyFormedLetterboxdUsername, UsernameRequest, Status, Movie
from helpers.db_models import Movie as DBMovie, Recommendation
from helpers.db import (
        NoDataException,
        get_engine, 
        get_cached_recommendation,
        extract_imdb_ids_from_recommendation,
        is_expired,
        get_recommendation_imdb_ids, 
        cache_recommendation,
        delete_expired_recommendations,
        delete_recommendations,
        get_movies,
        cache_trailer_ids,
        )


engine = get_engine()
letterboxd_scraper_lock = Lock()
youtube_scraper_lock = Lock()
status: dict[str, Status] = dict()

# Set up a scheduler to delete expired recommendations every day
scheduler = BackgroundScheduler()
scheduler.add_job(lambda: delete_expired_recommendations(engine), "interval", days=1)
scheduler.start()

app = FastAPI()
origins = ["http://localhost:3000", "http://192.168.11.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def convert_movies(movies: list[DBMovie]) -> list[Movie]:
    """Converts `Movie` objects from the DB into `Movie` objects for the API to respond with"""
    result = []
    for movie in movies:
        result.append(
                Movie( 
                      movieId=movie.imdb_id,
                      name=movie.original_title,
                      year=str(movie.release_year),
                      genre=movie.genres,
                      description=movie.plot,
                      posterURL=movie.poster_url,
                      letterboxdURL=f"https://www.letterboxd.com/imdb/{movie.imdb_id}",
                      trailerID=None
                      )
                )
    return result


def recommendation_system(username: str, prev_recommendation_has_expired: bool) -> None:
    """
    Completes the movie recommendation system, and updates `status` along the way.

    Args: 
        `username`: The Letterboxd user to complete the system for.
        `recommendation_is_expired`: `True` if the a recommendation exists in
            the cache for `username`, but it has expired.
    """
    status[username] = Status.VALIDATING_USERNAME
    profile_response = requests.get(f"https://www.letterboxd.com/{username}/")
    if profile_response.status_code != 200:
        status[username] = Status.FAILED_INVALID_USERNAME
        return

    status[username] = Status.WAITING_FOR_SCRAPER
    # Scrape Letterboxd for only one user at any given time
    with letterboxd_scraper_lock:
        status[username] = Status.SCRAPING_RATINGS
        try:
            ratings = scrape_ratings(username)
        except Exception:
            status[username] = Status.FAILED_SCRAPING
            return
    if len(ratings) == 0:
        status[username] = Status.FAILED_NO_RATINGS
        return
    print("ratings:", ratings)

    status[username] = Status.FINDING_RECOMMENDATION
    recommendation_imdb_ids = []
    with Session(engine) as session:
        try:
            recommendation_imdb_ids = get_recommendation_imdb_ids(session, username, ratings)
            print("recommendation imdb_ids:", recommendation_imdb_ids)
        except NoDataException:
            status[username] = Status.FAILED_NO_DATA
            return

        if len(recommendation_imdb_ids) == 0:
            status[username] = Status.FAILED_NO_RECOMMENDATIONS
            return
        cache_recommendation(
                session, 
                username, 
                len(ratings), 
                recommendation_imdb_ids, 
                prev_recommendation_has_expired
                )
        movies = get_movies(session, recommendation_imdb_ids)
        movies_without_trailer_ids = [movie for movie in movies if movie.trailer_id is None]
        print("number of movies without trailer ids:", len(movies_without_trailer_ids))
        print("trailer ids:", [movie.trailer_id for movie in movies])

        status[username] = Status.SCRAPING_TRAILER_IDS
        # Have only one active YouTube scraper at any given time 
        with youtube_scraper_lock:
            try:
                trailer_ids = scrape_trailer_ids(movies_without_trailer_ids)
            except Exception:
                trailer_ids = []
        print("trailer_ids:", trailer_ids)
        cache_trailer_ids(session, recommendation_imdb_ids, trailer_ids)

    status[username] = Status.FINISHED


# Ensure the scheduler shuts down properly on application exit
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    scheduler.shutdown()
    print("Shutting down sheduler")


@app.post("/usernames/", status_code=HTTPStatus.ACCEPTED)
def init_system(request: UsernameRequest, background_tasks: BackgroundTasks):
    with Session(engine) as session:
        recommendation = get_cached_recommendation(session, request.username)
        print(recommendation)
    has_prev_recommendation_expired = False
    if recommendation is None or (has_prev_recommendation_expired := is_expired(recommendation)):
        status[request.username] = Status.STARTING
        background_tasks.add_task(
                recommendation_system, 
                request.username, 
                has_prev_recommendation_expired
                )
    else:
        status[request.username] = Status.FINISHED


@app.get("/status/", response_model=Status)
def check_status(username: Annotated[str, ProperlyFormedLetterboxdUsername]):
    if username not in status:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"The recommendation system is not in progress for {username}, \
                    but it may have already completed. Either POST /usernames/ to \
                    start it, or GET /movies/ to check the recommendation cache."
        )
    username_status = status[username]
    if username_status in (Status.FAILED_INVALID_USERNAME, Status.FAILED_NO_RATINGS):
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=username_status)
    elif username_status in (
        Status.FAILED_SCRAPING,
        Status.FAILED_NO_DATA,
        Status.FAILED_NO_RECOMMENDATIONS,
    ):
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=username_status
        )
    else:
        return username_status


@app.get("/movies/", response_model=list[Movie])
def get_recommendation(username: Annotated[str, ProperlyFormedLetterboxdUsername]):
    with Session(engine) as session:
        recommendation = get_cached_recommendation(session, username)
        if recommendation is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"There is no recommendation for {username}. Either the recommendation \
                        system has not started, or a previous recommendation was deleted \
                        it expired, or the system is in progress. GET /status/ for more info."
            )
        else:
            if username in status:
                status.pop(username)
            recommendation_imdb_ids = extract_imdb_ids_from_recommendation(recommendation)
            print("recommendation imdb_ids from cache:", recommendation_imdb_ids)
            movies = get_movies(session, recommendation_imdb_ids)
            return convert_movies(movies)


@app.get("/pfp-urls/", response_model=str)
def get_pfp_url(username: Annotated[str, ProperlyFormedLetterboxdUsername]):
    pfp_url = scrape_pfp_url(username)
    if len(pfp_url) == 0:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Failed to get profile picture URL for Letterboxd user: {username}, \
                        retry if Letterboxd username is valid",
        )
    else:
        return pfp_url


if __name__ == "__main__":
    # Uncomment to reset the recommendations cache without having to re-init the DB
    with Session(engine) as sess:
        print("cached recs before deletion:", len(sess.scalars(select(Recommendation)).all()))
    delete_recommendations(engine)
    with Session(engine) as sess:
        print("cached recs after deletion:", len(sess.scalars(select(Recommendation)).all()))
    uvicorn.run(app, host="127.0.0.1", port=8000)
