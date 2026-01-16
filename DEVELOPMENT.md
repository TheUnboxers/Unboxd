## Backend Development 

### Running tests

- Ensure you are in the project's root directory: `Unboxd`
```cmd
uv run -m pytest
```

### Creating Datasets

```cmd
cd helpers
```

1. Initialize the movies dataset, and save the result in `movies`: 
```cmd
uv run init_dataset.py
```

2. Preprocess the movies dataset, and save the result in `preprocessed_movies`: 
```cmd
uv run preprocess_features.py
```
> [!TIP] This can be skipped if saving the `preprocessed_movies` dataset is not necessary.

3. Reduce the features of the movies dataset, and possibly save the result 
in `reduced_preprocessed_movies`:
```cmd 
uv run reduce_features.py 
```
> To skip step (2), pass the argument `preprocess` to preprocess the `movies` dataset,
but not save it, and use it for feature reduction. The argument `plot` can be 
used, with or without `preprocess`, to visualize the variance explained by the different 
numbers of components resulting from reducing the features of the `preprocessed_movies` 
dataset. If `plot` is passed, `reduced_preprocessed_movies` will not be saved.

### Scraping Letterboxd

```cmd
cd helpers
```

- Select a Letterboxd user's `username` to use 

- Out of `ratings`, and `pfp`, pass the desired item names after `username` when 
running `scrape_letterboxd.py`. For example:
```cmd
uv run scrape_letterboxd.py username pfp ratings
```
> This scrapes ratings and saves them at `../data/ratings/username.csv` or 
`..\data\ratings\username.csv`, and prints the url of the user's pfp to `STDOUT`

## Frontend Development

- When changing backend model types, to ensure changes are imported to the frontend, run `uv run main.py` in `backend` and run `npm run openapi-ts` in `frontend` to run HeyAPI.

## File architecture

`root`
- `backend` backend folder
  - `main.py` fastapi server 
  - `data` all datasheets (these won't exist unless they get initialized)
    - `movie_dataset` splits of the international movies dataset used to create `movies`
    - `movies` splits of the movies dataset
    - `trimmed_movies` splits of the movies dataset with the columns needed by the DB
    - `preprocessed_movies` preprocessed splits of the movies dataset
    - `reduced_preprocessed_movies` splits containing dimensionality reduced, and normalized
    feature vectors of the movies dataset
    - `ratings` scraped Letterboxd user ratings
  - `tests` all tests
    - `test_recommendation_system.py` verifies the values assigned to `status` by the 
    recommendation system
    - `test_db.py` tests operations on the db
  - `helpers` helper methods
    - `models.py` type modelling for the FastAPI server
    - `paths.py` enumerates the paths of the contents of `data`
    - `init_dataset.py` initializes the movies dataset
    - `preprocess_features.py` provides a method for preprocessesing the movies dataset
    - `reduce_features.py` provides a method for visualizing feature reduction, and methods for 
    reducing the dimensionality, and normalizing the feature vectors of the preprocessed 
    movies dataset
    - `representative.py` provides method for computing a user's representative movie
    - `db_models.py` type modelling for the DB
    - `init_db.py` initializes the DB
    - `db.py` provides methods for using the DB and the recommendation system
    - `scrape_letterboxd.py` provides methods for scraping Letterboxd user data 
    - `scrape_trailer_ids.py` provides method for scraping YouTube trailer video ids
    - `test.py` (needs updating) tests the recommendation system on mock data 
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
