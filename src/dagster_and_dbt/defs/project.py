# src/dagster_and_dbt/defs/project.py
from pathlib import Path
from dagster_dbt import DbtProject

# project.py nằm ở: src/dagster_and_dbt/defs/project.py
# dbt project nằm ở: src/dagster_and_dbt/analytics
DBT_PROJECT_DIR = (Path(__file__).resolve().parents[1] / "analytics").resolve()

dbt_project = DbtProject(project_dir=DBT_PROJECT_DIR)

# Tiện cho DEV: nếu thiếu manifest thì tự build để tạo target/manifest.json
dbt_project.prepare_if_dev()