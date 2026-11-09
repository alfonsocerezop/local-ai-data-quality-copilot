import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DBT_DIR = PROJECT_ROOT / "dbt"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

GROUNDED_FAILURES_PATH = OUTPUTS_DIR / "grounded_failures.json"
AI_EXPLANATIONS_PATH = OUTPUTS_DIR / "ai_explanations.json"

PYTHON_EXECUTABLE = sys.executable

if sys.platform.startswith("win"):
    DBT_EXECUTABLE = PROJECT_ROOT / ".venv" / "Scripts" / "dbt.exe"
else:
    DBT_EXECUTABLE = PROJECT_ROOT / ".venv" / "bin" / "dbt"


st.set_page_config(
    page_title="Local AI Data Quality Copilot",
    page_icon="🧪",
    layout="wide",
)


def run_command(command):
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    return {
        "command": " ".join(str(item) for item in command),
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def load_json(path):
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def run_pipeline(dataset):
    results = {}

    results["ingestion"] = run_command(
        [
            PYTHON_EXECUTABLE,
            str(PROJECT_ROOT / "ingestion" / "load_orders.py"),
            "--dataset",
            dataset,
        ]
    )

    if results["ingestion"]["returncode"] != 0:
        return results

    results["dbt_run"] = run_command(
        [
            str(DBT_EXECUTABLE),
            "run",
            "--project-dir",
            str(DBT_DIR),
            "--profiles-dir",
            str(DBT_DIR),
        ]
    )

    if results["dbt_run"]["returncode"] != 0:
        return results

    results["dbt_test"] = run_command(
        [
            str(DBT_EXECUTABLE),
            "test",
            "--project-dir",
            str(DBT_DIR),
            "--profiles-dir",
            str(DBT_DIR),
        ]
    )

    # dbt test returns a non-zero code when tests fail.
    # In this lab, failures may be expected and should still
    # continue to the evidence-grounding step.

    results["parser"] = run_command(
        [
            PYTHON_EXECUTABLE,
            str(PROJECT_ROOT / "copilot" / "parse_failures.py"),
        ]
    )

    if results["parser"]["returncode"] != 0:
        return results

    failures = load_json(GROUNDED_FAILURES_PATH)

    if failures:
        results["ai"] = run_command(
            [
                PYTHON_EXECUTABLE,
                str(PROJECT_ROOT / "copilot" / "explain_failure.py"),
            ]
        )
    else:
        results["ai"] = {
            "command": "AI explanation skipped",
            "returncode": 0,
            "stdout": "No data quality failures detected.",
            "stderr": "",
        }

        with AI_EXPLANATIONS_PATH.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump([], file)

    return results


def status_badge(success):
    return "✅ PASS" if success else "❌ FAIL"


def display_execution_details(results):
    with st.expander("Technical execution details"):
        for step_name, result in results.items():
            st.markdown(f"### {step_name}")

            st.code(result["command"])

            if result["stdout"]:
                st.text(result["stdout"])

            if result["stderr"]:
                st.text(result["stderr"])


def display_failure(failure, explanation=None):
    test_name = failure.get("test", "unknown")
    column = failure.get("column", "unknown")
    affected_records = failure.get("affected_records", [])

    with st.expander(
        f"❌ {test_name} — {column}",
        expanded=True,
    ):
        left, right = st.columns([1, 1])

        with left:
            st.markdown("### Deterministic Evidence")

            st.write(
                f"**Model:** `{failure.get('model')}`"
            )

            st.write(
                f"**Column:** `{column}`"
            )

            st.write(
                f"**Failures:** `{failure.get('failures')}`"
            )

            expected_values = failure.get("expected_values")

            if expected_values:
                st.write("**Expected values:**")

                st.code(
                    "\n".join(
                        str(value)
                        for value in expected_values
                    )
                )

            if affected_records:
                st.markdown("#### Affected Records")

                dataframe = pd.DataFrame(
                    affected_records
                )

                preferred_columns = [
                    "record_reference",
                    "source_row_number",
                    "order_id",
                    "customer_id",
                    "order_date",
                    "order_amount",
                    "order_status",
                ]

                visible_columns = [
                    column_name
                    for column_name in preferred_columns
                    if column_name in dataframe.columns
                ]

                st.dataframe(
                    dataframe[visible_columns],
                    use_container_width=True,
                    hide_index=True,
                )

        with right:
            st.markdown("### Grounded AI Explanation")

            if explanation:
                st.markdown(explanation)
            else:
                st.info(
                    "No AI explanation was generated."
                )


st.title("🧪 Local AI Data Quality Copilot")

st.caption(
    "Deterministic data quality controls + "
    "record-level evidence + local AI explanation"
)

st.markdown(
    """
**Architecture principle:**  
dbt detects the failure. Python gathers the evidence.
Gemma 3 explains the evidence. A human makes the decision.
"""
)

st.divider()


dataset = st.radio(
    "Choose a dataset",
    options=["good", "broken"],
    horizontal=True,
)

if dataset == "good":
    st.success(
        "Clean dataset: all data quality tests "
        "are expected to pass."
    )
else:
    st.warning(
        "Broken dataset: contains intentional "
        "data quality failures."
    )


if st.button(
    "Run Data Quality Analysis",
    type="primary",
    use_container_width=True,
):
    with st.spinner(
        "Running ingestion, dbt tests, "
        "evidence grounding and local AI..."
    ):
        pipeline_results = run_pipeline(dataset)

        st.session_state["pipeline_results"] = (
            pipeline_results
        )

        st.session_state["dataset"] = dataset

        st.session_state["failures"] = (
            load_json(GROUNDED_FAILURES_PATH)
        )

        st.session_state["explanations"] = (
            load_json(AI_EXPLANATIONS_PATH)
        )


if "pipeline_results" in st.session_state:

    results = st.session_state["pipeline_results"]
    failures = st.session_state.get(
        "failures",
        [],
    )

    explanations = st.session_state.get(
        "explanations",
        [],
    )

    st.divider()

    st.subheader("Execution Summary")

    col1, col2, col3, col4 = st.columns(4)

    ingestion_ok = (
        results.get("ingestion", {})
        .get("returncode") == 0
    )

    models_ok = (
        results.get("dbt_run", {})
        .get("returncode") == 0
    )

    parser_ok = (
        results.get("parser", {})
        .get("returncode") == 0
    )

    data_quality_ok = len(failures) == 0

    col1.metric(
        "Ingestion",
        status_badge(ingestion_ok),
    )

    col2.metric(
        "dbt Models",
        status_badge(models_ok),
    )

    col3.metric(
        "Data Quality",
        status_badge(data_quality_ok),
    )

    col4.metric(
        "Failures",
        len(failures),
    )

    st.divider()

    if not failures:
        st.success(
            "✅ All deterministic data quality "
            "controls passed."
        )

        st.markdown(
            """
### Trusted dataset

No failing records were detected.

The AI explanation layer was not required because
the deterministic controls found no violations.
"""
        )

    else:
        st.error(
            f"❌ {len(failures)} data quality "
            f"rules failed."
        )

        st.markdown(
            """
### Investigation

Each failure below includes:

- the deterministic rule that failed;
- the exact affected records;
- source-row traceability;
- expected versus observed values;
- a grounded local-AI explanation;
- the human decision required before remediation.
"""
        )

        explanation_lookup = {}

        for item in explanations:
            failure_info = item.get(
                "failure",
                {},
            )

            key = (
                failure_info.get("test"),
                failure_info.get("column"),
            )

            explanation_lookup[key] = (
                item.get("ai_explanation")
            )

        for failure in failures:
            key = (
                failure.get("test"),
                failure.get("column"),
            )

            display_failure(
                failure,
                explanation_lookup.get(key),
            )

    display_execution_details(results)