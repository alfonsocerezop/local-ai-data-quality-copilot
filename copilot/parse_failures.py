import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parent.parent

RUN_RESULTS_PATH = PROJECT_ROOT / "dbt" / "target" / "run_results.json"
MANIFEST_PATH = PROJECT_ROOT / "dbt" / "target" / "manifest.json"
DATABASE_PATH = PROJECT_ROOT / "warehouse" / "lab.duckdb"

OUTPUT_PATH = PROJECT_ROOT / "outputs" / "grounded_failures.json"


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Required artifact not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def json_safe(value):
    if value is None:
        return None

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    return value


def rows_to_dicts(cursor):
    columns = [description[0] for description in cursor.description]

    records = []

    for row in cursor.fetchall():
        record = {
            column: json_safe(value)
            for column, value in zip(columns, row)
        }

        if (
            "source_file" in record
            and "source_row_number" in record
        ):
            record["record_reference"] = (
                f"{record['source_file']}:"
                f"row_{record['source_row_number']}"
            )

        records.append(record)

    return records


def quote_identifier(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def detect_test_type(test_name):
    for test_type in [
        "not_null",
        "unique",
        "accepted_values",
    ]:
        if test_name.startswith(test_type):
            return test_type

    return "unknown"


def get_model_name(test_node, manifest):
    dependencies = (
        test_node
        .get("depends_on", {})
        .get("nodes", [])
    )

    for dependency_id in dependencies:
        dependency = (
            manifest
            .get("nodes", {})
            .get(dependency_id)
        )

        if (
            dependency
            and dependency.get("resource_type") == "model"
        ):
            return (
                dependency.get("alias")
                or dependency.get("name")
            )

    return None


def get_affected_records(
    con,
    test_type,
    model,
    column,
    expected_values=None,
):
    table_name = quote_identifier(model)
    column_name = quote_identifier(column)

    if test_type == "not_null":
        query = f"""
            SELECT *
            FROM main.{table_name}
            WHERE {column_name} IS NULL
            ORDER BY source_row_number
        """

        return rows_to_dicts(
            con.execute(query)
        )

    if test_type == "unique":
        query = f"""
            SELECT *
            FROM main.{table_name}
            WHERE {column_name} IN (
                SELECT {column_name}
                FROM main.{table_name}
                GROUP BY {column_name}
                HAVING COUNT(*) > 1
            )
            ORDER BY
                {column_name},
                source_row_number
        """

        return rows_to_dicts(
            con.execute(query)
        )

    if test_type == "accepted_values":
        if not expected_values:
            return []

        placeholders = ",".join(
            ["?"] * len(expected_values)
        )

        query = f"""
            SELECT *
            FROM main.{table_name}
            WHERE {column_name}
                  NOT IN ({placeholders})
            ORDER BY source_row_number
        """

        return rows_to_dicts(
            con.execute(
                query,
                expected_values,
            )
        )

    return []


def main():
    run_results = load_json(RUN_RESULTS_PATH)
    manifest = load_json(MANIFEST_PATH)

    con = duckdb.connect(str(DATABASE_PATH))

    grounded_failures = []

    for result in run_results.get("results", []):
        if result.get("status") not in {"fail", "error"}:
            continue

        unique_id = result.get("unique_id")

        node = (
            manifest
            .get("nodes", {})
            .get(unique_id, {})
        )

        metadata = node.get("test_metadata", {})
        kwargs = metadata.get("kwargs", {})

        test_name = metadata.get("name", "")
        test_type = detect_test_type(test_name)

        model = get_model_name(
            node,
            manifest,
        )

        column = kwargs.get("column_name")
        expected_values = kwargs.get("values")

        affected_records = get_affected_records(
            con,
            test_type,
            model,
            column,
            expected_values,
        )

        grounded_failure = {
            "test": test_type,
            "model": model,
            "column": column,
            "status": result.get("status"),
            "failures": result.get("failures"),
            "expected_values": expected_values,
            "affected_records": affected_records,
        }

        grounded_failures.append(
            grounded_failure
        )

    con.close()

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            grounded_failures,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print(
        f"Detected failures: "
        f"{len(grounded_failures)}"
    )

    for failure in grounded_failures:
        print(
            f"\n{failure['test']} | "
            f"{failure['column']}"
        )

        print(
            f"Affected records: "
            f"{len(failure['affected_records'])}"
        )

        for record in failure[
            "affected_records"
        ]:
            print(
                f"  - "
                f"{record.get('record_reference')}"
            )

    print(
        f"\nGrounded evidence written to:"
        f"\n{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()