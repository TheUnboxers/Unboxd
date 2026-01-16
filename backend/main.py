import requests
from threading import Lock
from http import HTTPStatus
from contextlib import asynccontextmanager
from typing import Annotated
import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker
from apscheduler.schedulers.background import BackgroundScheduler 

if __name__ == "__main__":
    from helpers.scrape_letterboxd import scrape_ratings, scrape_pfp_url
    from helpers.scrape_trailer_ids import scrape_trailer_ids
    from helpers.models import ProperlyFormedLetterboxdUsername, UsernameRequest, Status, Movie
    from helpers.db_models import Movie as DBMovie
    from helpers.db import (
            NoDataException,
            UserInsertionException,
            get_engine, 
            get_letterboxd_user_id,
            get_cached_recommendation,
            extract_imdb_ids_from_recommendation,
            has_expired,
            get_recommendation_imdb_ids, 
            cache_recommendation,
            delete_expired_recommendations,
            delete_recommendations,
            get_movies,
            cache_trailer_ids,
            )
    from helpers.test import dummy_data
else:
    from .helpers.scrape_letterboxd import scrape_ratings, scrape_pfp_url
    from .helpers.scrape_trailer_ids import scrape_trailer_ids
    from .helpers.models import ProperlyFormedLetterboxdUsername, UsernameRequest, Status, Movie
    from .helpers.db_models import Movie as DBMovie
    from .helpers.db import (
            NoDataException,
            UserInsertionException,
            get_engine, 
            get_letterboxd_user_id,
            get_cached_recommendation,
            extract_imdb_ids_from_recommendation,
            has_expired,
            get_recommendation_imdb_ids, 
            cache_recommendation,
            delete_expired_recommendations,
            delete_recommendations,
            get_movies,
            cache_trailer_ids,
            )
    from .helpers.test import dummy_data


Session = sessionmaker(get_engine())
letterboxd_scraper_lock = Lock()
youtube_scraper_lock = Lock()
status: dict[str, Status] = dict()
failed = [
    Status.FAILED_INVALID_USERNAME,
    Status.FAILED_NO_RATINGS,
    Status.FAILED_SCRAPING,
    Status.FAILED_NO_DATA,
    Status.FAILED_DB_OPERATION,
    Status.FAILED_NO_RECOMMENDATIONS
]
scheduler = BackgroundScheduler()
scheduler.add_job(lambda: clear_stale_entries(Session, status), "interval", days=0.5)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown tasks.
    """
    # Uncomment to reset the recommendations cache before server startup
    # delete_recommendations(Session)
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
origins = ["http://localhost:3000", "http://192.168.11.1:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def clear_stale_entries(Session: sessionmaker, status: dict[str, Status]) -> None:
    """
    (1) Deletes expired recommendations from the DB.         
    (2) Removes entries from `status` with a value in `failed`. 
    (3) Removes entries from `status` of value `Status.FINISHED`. 
    
    (1) will lead to an error in the following case: the recommendation system assumes 
    it only has to retrieve a cached recommendation after a POST to /usernames, but 
    the recommendation expires and is deleted before a GET to /movies. The recommendation 
    did technically expire, so it is reasonable to have the user retry.

    For the removed usernames, (2) will cause GET requests to /status to error. However, 
    that was going to happen regardless because the recommendation system failed.

    (3) will cause users to have to retry, but their recommendation will be in the cache
    at that point, so retries will be quick.
    """
    delete_expired_recommendations(Session)

    usernames_to_pop = []
    for username, system_status in status.items():
        if system_status in failed or system_status == Status.FINISHED:
            usernames_to_pop.append(username)
    for username in usernames_to_pop:
        status.pop(username)


def convert_movies(movies: list[DBMovie]) -> list[Movie]:
    """
    Converts `Movie` objects from the DB to `Movie` objects for the API to respond with.
    """
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
                      trailerID=movie.trailer_id
                      )
                )
    return result


def recommendation_system(username: str) -> None:
    """
    Completes the movie recommendation system for `username`, and updates `status` 
    along the way to reflect the progress of the system.
    """
    status[username] = Status.VALIDATING_USERNAME
    profile_response = requests.get(f"https://www.letterboxd.com/{username}/")
    if profile_response.status_code != HTTPStatus.OK:
        status[username] = Status.FAILED_INVALID_USERNAME
        return

    status[username] = Status.WAITING_FOR_LETTERBOXD_SCRAPER

    # Have only one active Letterboxd scraper at any given time 
    with letterboxd_scraper_lock:
        status[username] = Status.SCRAPING_RATINGS
        try:
            scraped_ratings = scrape_ratings(username)
        except Exception:
            status[username] = Status.FAILED_SCRAPING
            return
    if len(scraped_ratings) == 0:
        status[username] = Status.FAILED_NO_RATINGS
        return

    status[username] = Status.FINDING_RECOMMENDATION
    recommendation_imdb_ids = []
    with Session() as session:
        try:
            letterboxd_user_id = get_letterboxd_user_id(session, username)
        except UserInsertionException:
            status[username] = Status.FAILED_DB_OPERATION
            return
        try:
            recommendation_imdb_ids = get_recommendation_imdb_ids(
                session, letterboxd_user_id, scraped_ratings
            )
        except NoDataException:
            status[username] = Status.FAILED_NO_DATA
            return
        if len(recommendation_imdb_ids) == 0:
            status[username] = Status.FAILED_NO_RECOMMENDATIONS
            return
        cache_recommendation(
            session, letterboxd_user_id, len(scraped_ratings), recommendation_imdb_ids
        )
        movies = get_movies(session, recommendation_imdb_ids)
        movies_without_trailer_ids = [movie for movie in movies if movie.trailer_id is None]

        status[username] = Status.WAITING_FOR_YOUTUBE_SCRAPER

        # Have only one active YouTube scraper at any given time 
        with youtube_scraper_lock:
            status[username] = Status.SCRAPING_TRAILER_IDS
            try:
                trailer_ids = scrape_trailer_ids(movies_without_trailer_ids)
            except Exception:
                trailer_ids = []
        imdb_ids_of_movies_without_trailer_ids = [
            movie.imdb_id for movie in movies_without_trailer_ids
        ]
        cache_trailer_ids(session, imdb_ids_of_movies_without_trailer_ids, trailer_ids)

    status[username] = Status.FINISHED

    # For testing purposes only - comment out above and uncomment below to use dummy data
    # recommendations[username] = dummy_data
    # status[username] = Status.FINISHED


@app.post("/usernames/", status_code=HTTPStatus.ACCEPTED)
def init_system(request: UsernameRequest, background_tasks: BackgroundTasks):
    is_system_in_progress = (
        request.username in status
        and status[request.username] not in failed
        and status[request.username] != Status.FINISHED
    )
    if is_system_in_progress:
        return

    with Session() as session:
        try:
            letterboxd_user_id = get_letterboxd_user_id(session, request.username)
        except UserInsertionException:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, 
                detail=Status.FAILED_DB_OPERATION
            )
        recommendation = get_cached_recommendation(session, letterboxd_user_id)

    is_valid_recommendation_available = (
        recommendation is not None and not has_expired(recommendation)
    )
    if is_valid_recommendation_available:
        status[request.username] = Status.FINISHED
        return

    status[request.username] = Status.STARTING
    background_tasks.add_task(recommendation_system, request.username)
    

@app.get("/status/", response_model=Status)
def check_status(username: Annotated[str, ProperlyFormedLetterboxdUsername]):
    if username not in status:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"The recommendation system is not in progress for {username}. \
                    This may be due to its completion, or due its failure"
        )

    username_status = status[username]
    if username_status in (Status.FAILED_INVALID_USERNAME, Status.FAILED_NO_RATINGS):
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=username_status)
    elif username_status in (
        Status.FAILED_SCRAPING,
        Status.FAILED_NO_DATA,
        Status.FAILED_DB_OPERATION,
        Status.FAILED_NO_RECOMMENDATIONS,
    ):
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=username_status
        )

    return username_status
    

@app.get("/movies/", response_model=list[Movie])
def get_recommendation(username: Annotated[str, ProperlyFormedLetterboxdUsername]):
    with Session() as session:
        try:
            letterboxd_user_id = get_letterboxd_user_id(session, username)
        except UserInsertionException:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, 
                detail=Status.FAILED_DB_OPERATION
            )
        recommendation = get_cached_recommendation(session, letterboxd_user_id)
        if recommendation is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"There is no recommendation for {username}. Either the \
                        recommendation system has not started, or a previous recommendation \
                        was deleted after it expired, or the system is in progress"
            )

        recommendation_imdb_ids = extract_imdb_ids_from_recommendation(recommendation)
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

    return pfp_url


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

