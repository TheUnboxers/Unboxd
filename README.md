# Unboxd

A recommendation system for Letterboxd movies.\
You can download the recommended movies list and import it to your Letterboxd watchlist. See [here](https://letterboxd.com/about/importing-data/) for the Letterboxd guide on importing data.

[Protoype demo](https://www.linkedin.com/posts/christinechen04_just-wanted-to-share-what-dhruv-chavan-eric-activity-7409682403075522560-uDkS)

## Setup

> [!NOTE] 
> For further development setup see [DEVELOPMENT.md](./DEVELOPMENT.md)

### Backend 

- Install [uv](https://docs.astral.sh/uv/getting-started/installation/) for handling python versions, 
packages, and virtual environments

```sh
cd backend
```

> [!NOTE] 
For the following two steps, macOS users can alternatively install [Postgres.app](https://postgresapp.com/downloads.html), 
it includes PostgreSQL 18 and pgvector. The PostgreSQL server can be started through the app.

- Install [PostgreSQL 18](https://www.postgresql.org/download/), the database used by the FastAPI server
    - If the PostgreSQL server has not started on its own, see 
    [pg_ctl](https://www.postgresql.org/docs/current/app-pg-ctl.html) for how to manage the server.

- Install [pgvector](https://github.com/pgvector/pgvector?tab=readme-ov-file#installation-notes---linux-and-mac),
a PostgreSQL extension that enables vector operations in DB queries

- Download the [movies dataset](https://www.kaggle.com/datasets/pavan4kalyan/imdb-dataset-of-600k-international-movies) 
and move it to `data` as `movies.csv`

- Create the database (one time only):
```cmd
createdb unboxd
```
> Making the `createdb` command available may require exporting a `PATH` variable to 
the PostgreSQL 18 installation.

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

```sh
cd helpers 
```

- Create a `.env` file with the following entry:
```cmd
POSTGRESQL_PASSWORD=<insert_password_used_to_setup_posgres_here>
```

- Initialize the DB: 
```cmd
uv run init_db.py 
```
> If they don't already exist, this will initialize the `trimmed_movies` and 
`reduced_preprocessed_movies` datasets in `data`. The datasets can be deleted, but if 
the need arises to re-initialize the DB, it would be much quicker with the datasets 
already created. For reference, on a 2017 MacBook Air, this took 8 minutes and 30
seconds with no pre-existing datasets, but only 1 minute 30 seconds with the datasets.

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
