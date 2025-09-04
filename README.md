# Dagster × dbt — Hands-On Course Project

 > "This repository is a hands-on practice project following the Dagster & dbt course.
The codebase is based on the course’s starter project; my work here focused on configuration, running, observing, and troubleshooting the dbt ↔ Dagster integration—primarily on Windows."

# Objectives

- Load dbt models into Dagster using @dbt_assets.
- Explore the Asset Graph, lineage, and metadata in the Dagster UI.
- Materialize:
1. Staging models: stg_trips, stg_zones
2. Mart model: location_metrics
3. A downstream Python asset: airport_trips (chart)
- Practice an incremental dbt model (daily_metrics) and run it as daily partitions via Dagster (--vars passthrough).
- Get familiar with jobs/selections and resolve common configuration issues (manifest, env vars, file locks).
- Note: I am not the original author of the starter code; this repo is for learning purposes.

# What’s Included

- dbt project (DuckDB adapter) with staging & marts
- Dagster assets generated from dbt via @dbt_assets
- Optional translator to align dbt sources with existing Dagster assets
- Python asset airport_trips that renders a stacked bar chart (Matplotlib) from location_metrics
- Incremental model daily_metrics wired to daily partitions in Dagster
- Example job (trip_update_job) and selection patterns (dbt-style selectors)

# Tech Stack

- Dagster, dagster-dbt, dagster-duckdb
- dbt-duckdb (DuckDB 1.x)
- Python 3.11+

# Project Layout

```
src/
  dagster_and_dbt/
    __init__.py
    defs/
      assets/
        dbt.py                 # @dbt_assets (+ optional translator) + incremental (partitioned)
        metrics.py             # airport_trips (Matplotlib chart, embeds preview)
        constants.py
      jobs.py                  # example job + selection
      partitions.py            # daily_partition, monthly_partition
      project.py               # dbt_project + prepare_if_dev() for dev UX
    analytics/                 # dbt project (DuckDB)
      dbt_project.yml
      profiles.yml
      models/
        staging/{stg_trips.sql, stg_zones.sql}
        marts/{location_metrics.sql, daily_metrics.sql}
      duckdb/local.duckdb      # (gitignored)
data/
  raw/                         # parquet samples (consider Git LFS)
  outputs/                     # charts/images (gitignored)
```

# Getting Started (Windows-friendly)
## 1) Create & activate a virtual environment

```
python -m venv .venv
.\.venv\Scripts\activate.bat
pip install -U pip
pip install dagster dagster-webserver dagster-dbt dagster-duckdb duckdb dbt-duckdb pandas matplotlib
```
## 2) DuckDB configuration

The repository uses a fixed path in profiles.yml:
```
src/dagster_and_dbt/analytics/duckdb/local.duckdb
```

Dagster’s DuckDBResource points to the same file and creates the folder if missing—no env var required.
Prefer env vars? Set DUCKDB_PATH and update profiles.yml to use {{ env_var('DUCKDB_PATH') }}.

## 3) Run Dagster
```
$env:PYTHONPATH = ".\src"
dagster dev -m dagster_and_dbt
```

# Key Integration Notes

## Loading dbt models as assets

- The project uses @dbt_assets(manifest=dbt_project.manifest_path, ...).
- During development, dbt_project.prepare_if_dev() keeps the manifest up to date automatically on reload—no manual dbt parse loop.

## Example: Python asset depending on a dbt model

```
@dg.asset(deps=["location_metrics"])
def airport_trips(database: DuckDBResource) -> dg.MaterializeResult:
    df = database.get_connection().execute("""
        select zone, destination_borough, trips
        from location_metrics
        where from_airport
    """).fetch_df()

    fig, ax = plt.subplots(figsize=(10, 6))
    df.groupby(['zone','destination_borough']).sum()['trips'].unstack().plot(
        kind='bar', stacked=True, ax=ax
    )
    plt.savefig(constants.AIRPORT_TRIPS_FILE_PATH, format="png", bbox_inches="tight")
    # read file → base64 → embed preview in MaterializeResult metadata
```
## Incremental model with partitions

models/marts/daily_metrics.sql is incremental and filters by a supplied date window:
```
{% if is_incremental() %}
  where date_of_business between '{{ var("min_date") }}' and '{{ var("max_date") }}'
{% endif %}
```

The partitioned @dbt_assets definition passes the window to dbt:
```
tw = context.partition_time_window
vars = {"min_date": tw.start.strftime("%Y-%m-%d"),
        "max_date": tw.end.strftime("%Y-%m-%d")}
yield from dbt.cli(["build", "--vars", json.dumps(vars)], context=context).stream()
```

# Troubleshooting (what I encountered)

- Manifest not found → ensure prepare_if_dev() is executed or run dbt compile once.
- Env var required: DUCKDB_PATH → either set the variable or stick with the fixed path used by this repo.
- DuckDB “file in use” → close any process holding the .duckdb file (e.g., notebooks, DB viewers) or use a separate DB for experiments.
- PowerShell Unexpected token : when using --vars → wrap the JSON in single quotes as shown above.

# Recommended .gitignore
```
.venv/
.env
__pycache__/
*.pyc
.dagster_home/
src/dagster_and_dbt/analytics/target/
src/dagster_and_dbt/analytics/logs/
src/dagster_and_dbt/analytics/duckdb/*.duckdb
data/outputs/
```
If you keep large sample files (e.g., Parquet > 50 MB), consider Git LFS.

# Attribution

- Code structure and most logic come from the Dagster & dbt course starter project.
- This repository is for educational purposes, with additional configuration notes and Windows-friendly instructions authored by me.

# Possible Next Steps

- Add dbt tests and Dagster asset checks.
- CI for dbt build + linting on pull requests.
- Deploy to Dagster+ (GitHub integration & manifest build during deployment).

If you’re following the same course, I hope this README makes setup and experimentation smoother. Happy orchestrating! 🚀
