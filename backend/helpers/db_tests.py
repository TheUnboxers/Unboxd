from sqlalchemy import delete
from sqlalchemy.orm import sessionmaker
from db_models import Recommendation
from db import (
    NoDataException,
    UserInsertionException,
    get_engine,
    get_letterboxd_user_id,
    get_recommendation_imdb_ids,
    get_cached_recommendation,
    cache_recommendation,
    get_movies,
    cache_trailer_ids,
)

username = 'username' 
ratings = [
            ("Five Nights at Freddy's 2", 2025, 3.0),
            ("Avatar: Fire and Ash", 2025, 3.0),
            ("Marty Supreme", 2025, 4.0),
            ("Chainsaw Man – The Movie: Reze Arc", 2025, 5.0),
            ("The Conjuring: Last Rites", 2025, 2.0),
            ("Demon Slayer: Kimetsu no Yaiba Infinity Castle", 2025, None),
            ("The Fragrant Flower Blooms with Dignity", 2025, 4.0),
            ("Takopi's Original Sin", 2025, 3.0),
            ("KPop Demon Hunters", 2025, 3.0),
            ("F1", 2025, None),
            ]
         

def mock_recommendation_system():
    engine = get_engine()
    Session = sessionmaker(engine)

    with Session() as session:
        print("Adding letterboxd user...")
        try:
            letterboxd_user_id = get_letterboxd_user_id(session, username)
        except UserInsertionException:
            print("This shouldn't have happened part 1")
            return

        print("Getting recommendation imdb_ids...")
        try:
            recommendation_imdb_ids = get_recommendation_imdb_ids(
                session, letterboxd_user_id, ratings
            )
        except NoDataException:
            print("This shouldn't have happened part 2")
            return
        assert len(recommendation_imdb_ids) == 10

        print(
            "Pre-caching recommendation:", 
            get_cached_recommendation(session, letterboxd_user_id)
        )

        print("Caching recommendation...")
        cache_recommendation(session, letterboxd_user_id, len(ratings), recommendation_imdb_ids)

        print(
            "Post-caching recommendation:",
            get_cached_recommendation(session, letterboxd_user_id)
        )

        # Simulate recommendation expiration
        session.execute(delete(Recommendation))
        session.commit()
        print(
            "Post-expiration recommendation:", 
            get_cached_recommendation(session, letterboxd_user_id)
        )

        print("Getting corresponding movies...")
        movies = get_movies(session, recommendation_imdb_ids)
        print("Initial movie trailer_ids:")
        print([movie.trailer_id for movie in movies])

        trailer_ids = [
                'BbzwLMIgcNQ', 'sU_SQo1wbos', 'pZEvB2z644U', 'PFB-M1suyuY', 
                'OTbhQ0ct1as', 'ZK92E588K-0', '1NIXWgBkJNU', 'GLEY5ea3HjU', 
                'EIhlE3lfu6w', '0t-xZOwFHjE'
                ]
        print("Caching trailer ids...")
        cache_trailer_ids(session, recommendation_imdb_ids, trailer_ids)

        print("Post-caching movie trailer_ids:")
        movies = get_movies(session, recommendation_imdb_ids)
        print([movie.trailer_id for movie in movies])


if __name__ == "__main__":
    mock_recommendation_system()
    
