import dagster as dg
from dagster_dbt import DbtCliResource
from dagster_duckdb import DuckDBResource
import os

from dagster_and_dbt.defs.assets.dbt import dbt_analytics, incremental_dbt_models
from dagster_and_dbt.defs.assets.metrics import airport_trips  # nếu có
from dagster_and_dbt.defs.project import dbt_project

dbt_resource = DbtCliResource(project_dir=str(dbt_project.project_dir))

# DuckDBResource – trỏ đúng file bạn đang dùng (như đã fix ở bước trước)
duckdb_path = str((dbt_project.project_dir / "duckdb" / "local.duckdb").resolve())
database = DuckDBResource(database=duckdb_path)

defs = dg.Definitions(
    assets=[
        dbt_analytics,            # non-incremental (build)
        incremental_dbt_models,   # incremental (partitioned)
        airport_trips,            # nếu có
    ],
    resources={"dbt": dbt_resource, "database": database},
)