from datetime import datetime
import os

from sqlalchemy import ForeignKey, DateTime, Integer, Float, String, Identity
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import VECTOR

if os.getcwd().endswith("helpers"):
    from reduce_features import N_COMPONENTS
else:
    from .reduce_features import N_COMPONENTS


MOVIES_TABLE_NAME = "movies"
PREPROCESSED_MOVIES_TABLE_NAME = "preprocessed_movies"
RECOMMENDATIONS_TABLE_NAME = "recommendations"
K = 10
LETTERBOXD_USERS_TABLE_NAME = "letterboxd_users"
RATINGS_TABLE_NAME = "ratings"


class Base(DeclarativeBase):
    pass


class Movie(Base):
    __tablename__ = MOVIES_TABLE_NAME

    imdb_id: Mapped[str] = mapped_column(primary_key=True)
    original_title: Mapped[str] = mapped_column(String)
    release_year: Mapped[int] = mapped_column(Integer)
    trailer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    genres: Mapped[list[str]] = mapped_column(JSONB)
    """
    The choice between JSON and JSONB to store `genres` is kind of arbitrary in our case:
    JSONB ignores whitespace between tokens, is faster to process than JSON, can be 
    indexed, and supports more operators than JSON, but it is slower to insert than JSON.
    However, we don't do any operations on `genres`, and we aren't inserting genres after 
    initializing this table (which isn't slow with JSONB), so it doesn't really matter. 
    """
    poster_url: Mapped[str | None] = mapped_column(String, nullable=True)
    plot: Mapped[str | None] = mapped_column(String, nullable=True)


class PreprocessedMovie(Base):
    __tablename__ = PREPROCESSED_MOVIES_TABLE_NAME

    imdb_id = mapped_column(ForeignKey(f"{MOVIES_TABLE_NAME}.imdb_id"), primary_key=True)
    features: Mapped[list[float]] = mapped_column(VECTOR(N_COMPONENTS))


class Recommendation(Base):
    __tablename__ = RECOMMENDATIONS_TABLE_NAME

    username: Mapped[str] = mapped_column(primary_key=True)
    expiration_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    imdb_id_1: Mapped[str] = mapped_column(ForeignKey(f"{MOVIES_TABLE_NAME}.imdb_id"), nullable=False)
    imdb_id_2: Mapped[str] = mapped_column(ForeignKey(f"{MOVIES_TABLE_NAME}.imdb_id"), nullable=False)
    imdb_id_3: Mapped[str] = mapped_column(ForeignKey(f"{MOVIES_TABLE_NAME}.imdb_id"), nullable=False)
    imdb_id_4: Mapped[str] = mapped_column(ForeignKey(f"{MOVIES_TABLE_NAME}.imdb_id"), nullable=False)
    imdb_id_5: Mapped[str] = mapped_column(ForeignKey(f"{MOVIES_TABLE_NAME}.imdb_id"), nullable=False)
    imdb_id_6: Mapped[str] = mapped_column(ForeignKey(f"{MOVIES_TABLE_NAME}.imdb_id"), nullable=False)
    imdb_id_7: Mapped[str] = mapped_column(ForeignKey(f"{MOVIES_TABLE_NAME}.imdb_id"), nullable=False)
    imdb_id_8: Mapped[str] = mapped_column(ForeignKey(f"{MOVIES_TABLE_NAME}.imdb_id"), nullable=False)
    imdb_id_9: Mapped[str] = mapped_column(ForeignKey(f"{MOVIES_TABLE_NAME}.imdb_id"), nullable=False)
    imdb_id_10: Mapped[str] = mapped_column(ForeignKey(f"{MOVIES_TABLE_NAME}.imdb_id"), nullable=False)
    

class LetterboxdUser(Base):
    __tablename__ = LETTERBOXD_USERS_TABLE_NAME

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String)


class Rating(Base):
    __tablename__ = RATINGS_TABLE_NAME

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    letterboxd_user_id: Mapped[int] = mapped_column(ForeignKey(f"{LETTERBOXD_USERS_TABLE_NAME}.id"), nullable=False)
    original_title: Mapped[str] = mapped_column(String)
    release_year: Mapped[int] = mapped_column(Integer)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    imdb_id: Mapped[str | None] = mapped_column(String, nullable=True)

