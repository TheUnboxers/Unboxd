from enum import Enum
from typing import Annotated
import re

from pydantic import AfterValidator, BaseModel
from fastapi import Query


# Letterboxd usernames must be comprised of 2-15 digits, underscores, or English alphabet letters
LETTERBOXD_USERNAME_MIN_LENGTH = 2
LETTERBOXD_USERNAME_MAX_LENGTH = 15
LETTERBOXD_USERNAME_VALID_CHARS = r"[a-zA-Z0-9_]"


def is_properly_formed_letterboxd_username(username: str) -> str:
    """
    Letterboxd username validator.

    Args: 
        `username`: The username to validate.

    Returns:
        `username`, if it is valid.

    Raises:
        `ValueError`, if `username` is not valid.
    """
    is_valid = (length := len(username)) >= LETTERBOXD_USERNAME_MIN_LENGTH \
            and length <= LETTERBOXD_USERNAME_MAX_LENGTH \
            and re.match(LETTERBOXD_USERNAME_VALID_CHARS, username) != None
    if not is_valid:
        raise ValueError("Received an invalid Letterboxd username")
    return username


ProperlyFormedLetterboxdUsername = Query(
        min_length=LETTERBOXD_USERNAME_MIN_LENGTH, 
        max_length=LETTERBOXD_USERNAME_MAX_LENGTH, 
        regex=LETTERBOXD_USERNAME_VALID_CHARS
        )


class UsernameRequest(BaseModel):
    username: Annotated[str, AfterValidator(is_properly_formed_letterboxd_username)]


class Status(str, Enum):
    STARTING = "Starting"
    VALIDATING_USERNAME = "Validating username"
    FAILED_INVALID_USERNAME = "Failed. Invalid username"
    WAITING_FOR_SCRAPER = "Waiting for scraper"
    SCRAPING_RATINGS = "Scraping user ratings"
    FAILED_NO_RATINGS = "Failed. No ratings to scrape for the user"
    FAILED_SCRAPING = "Failed. Error while scraping"
    PREPROCESSING_DATA = "Preprocessing data"
    FAILED_NO_DATA = "Failed. No data available about the user-rated movies"
    FINDING_RECOMMENDATION = "Finding recommendations"
    FAILED_NO_RECOMMENDATIONS = (
        "Failed. No movies not already rated are available for recommendation"
    )
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
