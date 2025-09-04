# src/dagster_and_dbt/defs/assets/dbt.py
import json
import dagster as dg
from dagster_dbt import DagsterDbtTranslator, DbtCliResource, dbt_assets

from dagster_and_dbt.defs.project import dbt_project
from dagster_and_dbt.defs.partitions import daily_partition

# chọn tất cả models có materialized=incremental (cú pháp selector của dbt)
INCREMENTAL_SELECTOR = "config.materialized:incremental"


class CustomizedDagsterDbtTranslator(DagsterDbtTranslator):
    def get_asset_key(self, dbt_resource_props):
        resource_type = dbt_resource_props["resource_type"]
        name = dbt_resource_props["name"]
        if resource_type == "source":
            return dg.AssetKey(f"taxi_{name}")
        return super().get_asset_key(dbt_resource_props)


# 3a) Chạy toàn bộ dbt (trừ incremental) như trước
@dbt_assets(
    manifest=dbt_project.manifest_path,
    dagster_dbt_translator=CustomizedDagsterDbtTranslator(),
    exclude=INCREMENTAL_SELECTOR,   # loại incremental ra để hàm bên dưới xử lý theo partition
)
def dbt_analytics(context: dg.AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()


# 3b) Hàm riêng cho các incremental models + partition theo ngày
@dbt_assets(
    manifest=dbt_project.manifest_path,
    dagster_dbt_translator=CustomizedDagsterDbtTranslator(),
    select=INCREMENTAL_SELECTOR,    # chỉ lấy incremental models
    partitions_def=daily_partition, # partition theo ngày
)
def incremental_dbt_models(context: dg.AssetExecutionContext, dbt: DbtCliResource):
    # Lấy khoảng thời gian của partition đang chạy
    time_window = context.partition_time_window
    dbt_vars = {
        # dùng YYYY-MM-DD là đủ cho filter theo ngày
        "min_date": time_window.start.strftime("%Y-%m-%d"),
        "max_date": time_window.end.strftime("%Y-%m-%d"),
    }

    # Truyền biến cho dbt bằng --vars
    yield from dbt.cli(
        ["build", "--vars", json.dumps(dbt_vars)],
        context=context,
    ).stream()