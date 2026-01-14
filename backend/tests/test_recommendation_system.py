import numpy as np
import pandas as pd
from unittest.mock import patch
from backend.main import recommendation_system, status, recommendations
from backend.helpers.models import Status, Movie

# reset global state
def teardown_function():
    status.clear()
    recommendations.clear()

@patch("backend.main.requests.get")
@patch("backend.main.scrape_ratings")
@patch("backend.main.obtain_ids_and_weights")
@patch("backend.main.retrieve_preprocessed_data")
@patch("backend.main.recommend_movies")
@patch("backend.main.get_movies")
def test_recommendation_system_success(
    mock_get_movies,
    mock_recommend,
    mock_retrieve_preprocessed,
    mock_obtain_ids,
    mock_scrape,
    mock_requests,
):
    username = "testuser"

    # Mock
    mock_requests.return_value.status_code = 200
    mock_scrape.return_value = {"tt1": 4.5}
    mock_obtain_ids.return_value = (["tt1"], np.array([1.0]))
    mock_retrieve_preprocessed.return_value = pd.DataFrame({
        "imdb_id": ["tt1"],
        "feature1": [0.1],
        "feature2": [0.2]
    })
    mock_recommend.return_value = {"t9": 0.9}
    mock_get_movies.return_value = [
        Movie(
            movieId="t9",
            name="Recommended Movie",
            year=2023,
            genre=["Drama"],
            description="A great movie.",
            posterURL="poster_url",
            letterboxdURL="letterboxd_url",
            trailerID="tt9",
            similarityScore=0.9
        )
    ]
    recommendation_system(username)

    assert status[username] == Status.FINISHED
    assert username in recommendations
    assert len(recommendations[username]) == 1

@patch("backend.main.requests.get")
def test_invalid_username(mock_requests):
    '''testing invalid username handling'''
    # Mock
    mock_requests.return_value.status_code = 404

    recommendation_system("baduser")

    assert status["baduser"] == Status.FAILED_INVALID_USERNAME

@patch("backend.main.requests.get")
@patch("backend.main.scrape_ratings")
def test_no_ratings(mock_scrape, mock_requests):
    '''testing no ratings handling'''
    # Mock
    mock_requests.return_value.status_code = 200
    mock_scrape.return_value = {}
    recommendation_system("norating")
    assert status["norating"] == Status.FAILED_NO_RATINGS

@patch("backend.main.requests.get")
@patch("backend.main.scrape_ratings")
@patch("backend.main.obtain_ids_and_weights")
@patch("backend.main.retrieve_preprocessed_data")
@patch("backend.main.recommend_movies")
def test_no_recommendations(
    mock_recommend,
    mock_retrieve_preprocessed,
    mock_obtain_ids,
    mock_scrape,
    mock_requests,
):
    '''testing no recommendations handling'''
    # Mock
    mock_requests.return_value.status_code = 200
    mock_scrape.return_value = {"t1": 4.5}
    mock_obtain_ids.return_value = (["t1"], np.array([1.0]))
    mock_retrieve_preprocessed.return_value = pd.DataFrame({"imdb_id": ["t1"], "feature1": [0.1]})
    mock_recommend.return_value = {}

    recommendation_system("empty")
    assert status["empty"] == Status.FAILED_NO_RECOMMENDATIONS
