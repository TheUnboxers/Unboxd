## Backend Development 

### Running tests

- Ensure you are in the project's root directory `Unboxd`
- Run the tests: `uv run -m pytest`

### Creating Datasets

- Download the following datasets from Kaggle, and move them to `data`:
    - The inner `movie_dataset` of [(international) movies dataset](https://www.kaggle.com/datasets/pavan4kalyan/imdb-dataset-of-600k-international-movies)
    - [Trending movies dataset](https://www.kaggle.com/datasets/amitksingh2103/trending-movies-over-the-years) 
- `cd helpers`
- Initialize the movies dataset and merged trending movies dataset: `uv run initialize_datasets.py`
- Preprocess the movies dataset: `uv run preprocess_features.py`
- Split the preprocessed movies dataset: `uv run split_csv.py`
- Retrieve the preprocessed features of the trending movies dataset: `uv run retrieve_preprocessed.py`
- **(Optional, Very slow ~ 6 hrs)** Scrape movie trailer YouTube video ids for the merged trending movies dataset: `uv run scrape_trailer_ids.py`

### Scraping and Merging of Letterboxd Data

- If not done already: `cd helpers`
- Select a Letterboxd user's `username` to use 

#### Scraping Letterboxd

- Out of `ratings`, and `pfp`, pass the desired item names after `username` when running `scrape_letterboxd.py`
- For example, `uv run scrape_letterboxd.py username pfp ratings`:
    - Scrapes ratings and saves them at `../data/ratings/username.csv` or `..\data\ratings\username.csv`
    - Prints the url of the user's pfp

#### Merging

- To merge movie data with the scraped ratings from the previous step: `uv run merge_ratings.py username`
- Find the results at `../data/merged_ratings/username.csv` or `..\data\merged_ratings\username.csv` 

## Frontend Development
- When changing backend model types, to ensure changes are imported to the frontend, run `uv run main.py` in `backend` and run `npm run openapi-ts` in `frontend` to run HeyAPI.

## File architecture
`root`
- `backend` backend folder
  - `main.py` fastapi server 
  - `data` all datasheets
    - `movies.csv` (international) movies dataset
    - `preprocessed_movies` preprocessed splits of the movies dataset
    - `merged_trending_movies.csv` trending movies with features from the movies dataset
    - `preprocessed_trending_movies.csv` trending movies with features from the preprocessed movies dataset
    - `trending_movie_trailers.csv` movie trailer YouTube video ids of the merged trending movies dataset
    - `ratings` scraped Letterboxd user ratings
    - `merged_ratings` scraped Letterboxd user ratings combined with movie data from the movies dataset
  - `helpers` helper methods
    - `models.py` type modelling
    - `paths.py` enumerates the paths of the contents of `data`
    - `initialize_datasets.py` initializes the movies dataset and the merged trending movies dataset
    - `scrape_letterboxd.py` provides method for scraping Letterboxd user data 
    - `scrape_trailer_ids.py` scrapes YouTube for merged trending movie trailer ids
    - `merge_ratings.py` provides methods for merging the movies dataset with scraped Letterboxd user ratings 
    - `recommender.py` provides cosine similarity and knn recommender methods
    - `preprocess_features.py` preprocesses the movies dataset
    - `split_csv.py` splits the preprocessed movies dataset into multiple files
    - `retrieve_preprocessed.py` provides methods for retrieving the preprocessed versions of movie data
    - `test.py` tests the recommendation system on mock data
- `frontend` frontend folder
  - `app`
    - `api`
      - `index.ts` backend api setup
    - `recommendations`
      - `page.tsx` recommendations page ("/recommendations")
    - `globals.css` global css file
    - `layout.tsx` main layout
    - `page.tsx` main landing page ("/")
    - `types.tsx` type modelling
  - `components`
    - `ui` shadcn ui components
    - `error.tsx` error component
    - `movie-card.tsx` movie card component
    - `nav-bar.tsx` navigation bar component
    - `progress.tsx` progress bar component
    - `result.tsx` result component that shows on loaded results page
    - `theme-provider.tsx` dark/light mode theme provider
    - `theme-toggle.tsx` dark/light mode toggle component
