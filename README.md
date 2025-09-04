# Dagster × dbt – NYC Taxis
# What’s inside

dbt project (DuckDB adapter) with staging + marts

Dagster assets auto-generated from dbt, with a custom translator that links dbt sources → upstream assets (taxi_trips, taxi_zones)

A Python asset airport_trips that charts trips from NYC airports (depends on dbt model location_metrics)

Incremental model daily_metrics + daily partitions in Dagster (passes min_date/max_date to dbt via --vars)

A scheduled Job (trip_update_job) and examples of scoping selections using dbt-style selectors

# Tech stack

Dagster + dagster-dbt + dagster-duckdb

dbt-duckdb (DuckDB 1.x)

Python 3.11+

Windows-centric instructions (PowerShell/CMD), but works on macOS/Linux too

# Project layout (key bits)
src/
  dagster_and_dbt/
    __init__.py                # exposes Definitions for dagster dev -m dagster_and_dbt
    defs/
      __init__.py              # Definitions: assets, resources, jobs, schedules
      assets/
        dbt.py                 # @dbt_assets + translator + incremental partitioned assets
        metrics.py             # airport_trips (Python → Matplotlib chart)
        constants.py
      jobs.py                  # trip_update_job + selection examples
      partitions.py            # daily_partition, monthly_partition
      project.py               # dbt_project + prepare_if_dev()
    analytics/                 # dbt project (DuckDB)
      dbt_project.yml
      profiles.yml
      models/
        staging/
          stg_trips.sql
          stg_zones.sql
        marts/
          location_metrics.sql
          daily_metrics.sql    # incremental facts by day
      duckdb/
        local.duckdb           # (gitignored)
data/
  raw/                         # parquet seeds (git LFS friendly/optional)

# Quickstart
1) Create & activate venv

PowerShell

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install dagster dagster-webserver dagster-dbt dagster-duckdb duckdb dbt-duckdb pandas matplotlib


CMD

python -m venv .venv
.\.venv\Scripts\activate.bat
pip install -U pip
pip install dagster dagster-webserver dagster-dbt dagster-duckdb duckdb dbt-duckdb pandas matplotlib

2) DuckDB config (two options)

A. Fixed path (simple, default in repo)
profiles.yml points to:

src/dagster_and_dbt/analytics/duckdb/local.duckdb


Dagster’s DuckDBResource uses the same file and creates the folder if missing. No env vars needed.

B. Env var (optional)
If you prefer env-driven path, set DUCKDB_PATH and point profiles.yml to {{ env_var('DUCKDB_PATH') }}.

PowerShell:

$env:DUCKDB_PATH = "$PWD\src\dagster_and_dbt\analytics\duckdb\local.duckdb"

3) Run Dagster
$env:PYTHONPATH = ".\src"
dagster dev -m dagster_and_dbt


Open http://localhost:3000
.

If the code location fails to load at first boot, click Deployment → Code locations → Reload.

# dbt ↔ Dagster integration highlights
Custom translator (link sources to assets)

In defs/assets/dbt.py I override DagsterDbtTranslator.get_asset_key so dbt sources like raw_taxis/trips collapse into existing assets taxi_trips / taxi_zones:

class CustomizedDagsterDbtTranslator(DagsterDbtTranslator):
    def get_asset_key(self, props):
        if props["resource_type"] == "source":
            return dg.AssetKey(f"taxi_{props['name']}")
        return super().get_asset_key(props)

Two @dbt_assets functions

dbt_analytics: runs all non-incremental models (exclude="config.materialized:incremental").

incremental_dbt_models: partitioned daily, only incremental models; passes window to dbt via --vars:

time_window = context.partition_time_window
vars = {"min_date": time_window.start.strftime("%Y-%m-%d"),
        "max_date": time_window.end.strftime("%Y-%m-%d")}
yield from dbt.cli(["build", "--vars", json.dumps(vars)], context=context).stream()

Incremental model + partitions

models/marts/daily_metrics.sql:

{{ config(materialized='incremental', unique_key='date_of_business') }}

... aggregate by day ...

{% if is_incremental() %}
  where date_of_business between '{{ var("min_date") }}' and '{{ var("max_date") }}'
{% endif %}


Materialize the daily_metrics asset → Dagster will ask you to pick partitions (days) and inject the window.

# Python asset that depends on dbt

airport_trips (in metrics.py) depends on location_metrics and renders a stacked bar chart in run metadata:

Queries DuckDB via DuckDBResource

Uses Matplotlib

Saves to data/outputs/airport_trips.png (gitignored)

Embeds a base64 preview in the materialization

# Jobs & Automation

trip_update_job demonstrates:

Selecting “everything” via AssetSelection.all()

Then excluding sets using Dagster & dbt-style selectors:

from dagster_dbt import build_dbt_asset_selection
dbt_trips = build_dbt_asset_selection([dbt_analytics], "stg_trips").downstream()
trip_update_job = dg.define_asset_job(
    name="trip_update_job",
    partitions_def=monthly_partition,
    selection=dg.AssetSelection.all() - dbt_trips
)


Easily plug into Dagster+ GitHub deployment; I keep this repo ready for CI/CD.

# Developer experience

dbt_project.prepare_if_dev() auto-parses/updates manifest.json on reload—no more manual dbt parse.

Works great on Windows:

PowerShell quoting for dbt vars:

dbt build --vars '{"min_date":"2023-03-04","max_date":"2023-03-05"}' --select 'config.materialized:incremental'


Resolve “file in use” by closing any process holding .duckdb or using a separate DB file for experiments.

# Troubleshooting I hit (and fixed)

DagsterDbtManifestNotFoundError → ensure prepare_if_dev() is on, or run dbt compile once.

Env var required 'DUCKDB_PATH' → either set it in the shell before dagster dev, or switch to the fixed path pattern above.

DuckDB “cannot open file… being used by another process” → close notebooks/tools holding the file; Dagster + dbt share the same .duckdb.

PowerShell --vars token errors → wrap JSON in single quotes as shown.

# Repo hygiene

Large/derived files are ignored:

.venv/, .dagster_home/, analytics/target/, analytics/logs/, data/outputs/, *.duckdb, .env

If you need to push big inputs (e.g., Parquet > 50MB), consider Git LFS.

📝 Why I built this

I love the clarity dbt brings to transformations—and I wanted observability, orchestration, and asset lineage that feel just as elegant. Dagster’s dbt integration let me keep dbt’s mental model while adding:

Partitioned runs without rewriting models

Downstream Python assets for charts/dashboards

Selections my analytics teammates already understand

If you’re on the same journey, feel free to fork and riff. Happy orchestration! 🚀
