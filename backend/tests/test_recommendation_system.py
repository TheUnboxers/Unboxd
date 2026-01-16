from unittest.mock import patch, Mock
from backend.main import recommendation_system, status
from backend.helpers.models import Status
from backend.helpers.db_models import Movie


# reset global state
def teardown_function():
    status.clear()


@patch("backend.main.requests.get")
@patch("backend.main.scrape_ratings")
@patch("backend.main.get_letterboxd_user_id")
@patch("backend.main.get_recommendation_imdb_ids")
@patch("backend.main.cache_recommendation")
@patch("backend.main.get_movies")
@patch("backend.main.scrape_trailer_ids")
@patch("backend.main.cache_trailer_ids")
def test_recommendation_system_success(
    mock_cache_trailer_ids: Mock,
    mock_scrape_trailer_ids: Mock,
    mock_get_movies: Mock,
    mock_cache_rec: Mock,
    mock_get_rec_imdb_ids: Mock,
    mock_get_id: Mock,
    mock_scrape_ratings: Mock,
    mock_requests: Mock,
):
    # Mock
    username = "testuser"
    mock_requests.return_value.status_code = 200
    mock_scrape_ratings.return_value = [("Barbie", 2023, 4.5)]
    mock_get_id.return_value = 21
    mock_get_rec_imdb_ids.return_value = ["tt1"]
    mock_cache_rec.return_value = None
    mock_get_movies.return_value = [
        Movie(
            imdb_id="tt1",
            original_title="Recommended Movie",
            release_year=2023,
            trailer_id="abcd",
            genres=["Drama"],
            poster_url="poster_url",
            plot="A great movie.",
        )
    ]
    mock_scrape_trailer_ids.return_value = None
    mock_cache_trailer_ids.return_value = None
    recommendation_system(username)

    assert status[username] == Status.FINISHED


@patch("backend.main.requests.get")
def test_invalid_username(mock_requests: Mock):
    '''testing invalid username handling'''
    # Mock
    username = "baduser"
    mock_requests.return_value.status_code = 404
    recommendation_system(username)

    assert status[username] == Status.FAILED_INVALID_USERNAME


@patch("backend.main.requests.get")
@patch("backend.main.scrape_ratings")
def test_no_ratings(mock_scrape_ratings: Mock, mock_requests: Mock):
    '''testing no ratings handling'''
    # Mock
    username = "norating"
    mock_requests.return_value.status_code = 200
    mock_scrape_ratings.return_value = []
    recommendation_system(username)

    assert status[username] == Status.FAILED_NO_RATINGS


@patch("backend.main.requests.get")
@patch("backend.main.scrape_ratings")
@patch("backend.main.get_letterboxd_user_id")
@patch("backend.main.get_recommendation_imdb_ids")
def test_no_recommendations(
    mock_get_rec_imdb_ids: Mock,
    mock_get_id: Mock,
    mock_scrape_ratings: Mock,
    mock_requests: Mock,
):
    '''testing no recommendations handling'''
    # Mock
    username = "empty"
    mock_requests.return_value.status_code = 200
    mock_scrape_ratings.return_value = [("Barbie", 2023, 4.5)]
    mock_get_id.return_value = 21
    mock_get_rec_imdb_ids.return_value = []
    recommendation_system(username)

    assert status[username] == Status.FAILED_NO_RECOMMENDATIONS

