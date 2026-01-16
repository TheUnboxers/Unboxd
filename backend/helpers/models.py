from enum import Enum
from typing import Annotated
import re
from pydantic import AfterValidator, BaseModel
from fastapi import Query


# Letterboxd usernames are made up of 2-15 digits, underscores, or English alphabet letters
LETTERBOXD_USERNAME_MIN_LENGTH = 2
LETTERBOXD_USERNAME_MAX_LENGTH = 15
LETTERBOXD_USERNAME_VALID_CHARS = r"[a-zA-Z0-9_]"
ProperlyFormedLetterboxdUsername = Query(
        min_length=LETTERBOXD_USERNAME_MIN_LENGTH, 
        max_length=LETTERBOXD_USERNAME_MAX_LENGTH, 
        pattern=LETTERBOXD_USERNAME_VALID_CHARS
        )


def is_properly_formed_letterboxd_username(username: str) -> str:
    """
    Args: 
        `username`: The username to validate.
    Returns:
        `username`, if it is a properly formed Letterboxd username, i.e. 
            it could be used to create Letterboxd account.
    Raises:
        `ValueError`, if `username` is not properly formed.
    """
    is_properly_formed = (length := len(username)) >= LETTERBOXD_USERNAME_MIN_LENGTH \
            and length <= LETTERBOXD_USERNAME_MAX_LENGTH \
            and re.match(LETTERBOXD_USERNAME_VALID_CHARS, username) != None
    if not is_properly_formed:
        raise ValueError("Received an invalid Letterboxd username")
    return username


class UsernameRequest(BaseModel):
    username: Annotated[str, AfterValidator(is_properly_formed_letterboxd_username)]


class Status(str, Enum):
    STARTING = "Starting"
    VALIDATING_USERNAME = "Validating username"
    FAILED_INVALID_USERNAME = "Failed. Invalid username"
    WAITING_FOR_LETTERBOXD_SCRAPER = "Waiting for Letterboxd scraper"
    SCRAPING_RATINGS = "Scraping user ratings"
    FAILED_NO_RATINGS = "Failed. No ratings to scrape for the user"
    FAILED_SCRAPING = "Failed. Error while scraping"
    PREPROCESSING_DATA = "Preprocessing data"
    FAILED_NO_DATA = "Failed. No data available about the user-rated movies"
    FAILED_DB_OPERATION = "Failed. Something went wrong with the database"
    FINDING_RECOMMENDATION = "Finding recommendations"
    FAILED_NO_RECOMMENDATIONS = (
        "Failed. No movies not already rated are available for recommendation"
    )
    WAITING_FOR_YOUTUBE_SCRAPER = "Waiting for YouTube scraper"
    SCRAPING_TRAILER_IDS = "Scraping YouTube trailer ids"
    FINISHED = "Finished"


class Movie(BaseModel):
    movieId: str
    name: str
    year: str
    genre: list[str]
    description: str | None
    posterURL: str | None
    letterboxdURL: str
    trailerID: str | None

