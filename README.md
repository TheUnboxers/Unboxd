# Unboxd

A recommendation system for Letterboxd movies.\
You can download the recommended movies list and import it to your Letterboxd watchlist. See [here](https://letterboxd.com/about/importing-data/) for the Letterboxd guide on importing data.

[Protoype demo](https://www.linkedin.com/posts/christinechen04_just-wanted-to-share-what-dhruv-chavan-eric-activity-7409682403075522560-uDkS)

## Setup

> [!NOTE] 
> For further development setup see [DEVELOPMENT.md](./DEVELOPMENT.md)

### Backend 

- Download the [movies dataset](https://www.kaggle.com/datasets/pavan4kalyan/imdb-dataset-of-600k-international-movies) 
and move the inner `movie_dataset` to `data`.

#### Installation 

- Install [uv](https://docs.astral.sh/uv/getting-started/installation/) for handling 
python versions, packages, and virtual environments.

```sh
cd backend
```

- Create virtual environment (one time only):
```cmd
uv venv
```

- Prior to running scripts, activate the venv:
```sh
source .venv/bin/activate
```
> macOS/Linux 
```sh
source .venv\Scripts\activate
```
> Windows

- Install [PostgreSQL 18](https://www.postgresql.org/download/), it is the database used by 
the FastAPI server. Take note of the values used by PostgreSQL during the installation,
these will be needed in the [environment setup](#environment).

- Create a database named `unboxd` using [pgAdmin](https://www.pgadmin.org/), which 
should have come installed with PostgreSQL. If a connection to the PostgreSQL server 
was not established upon installation, do so through pgAdmin.

- Install [pgvector](https://github.com/pgvector/pgvector?tab=readme-ov-file#installation-notes---linux-and-mac),
a PostgreSQL extension that enables vector operations in DB queries.

#### Environment 

- Ensure the following environment variables are set using the same values used
during the PostgreSQL installation. These can alternatively be set in a `.env` file:
```
PGUSER=postgres
PGHOST=localhost
PGPORT=5432
```
> [!NOTE]
> These are example values, but it is likely that you will use these. Also, these variables 
> may already be set by PostgreSQL during installation.

```
PGPASSWORD=<insert_password_used_to_setup_posgres_here>
```
> This one needs to be set manually.

#### Server

```sh
cd helpers 
```

- Initialize the DB: 
```cmd
uv run init_db.py 
```
> If they don't already exist, this will initialize the `trimmed_movies` and 
> `reduced_preprocessed_movies` datasets in `data`. The datasets can be deleted, 
> but re-initializing the DB is much quicker with the datasets already created.

```sh
cd ..
```

- Run the server
```cmd
uv run main.py
```

- Deactivate the venv when done:
```cmd
deactivate
```

### Frontend Setup

- Install [Node.js](https://nodejs.org/en/download) to get npm

```sh
cd frontend
```

- Install all dependencies: 
```cmd
npm install
```

- Run the frontend: 
```cmd
npm run dev
```
