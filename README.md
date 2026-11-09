# Local AI Data Quality Copilot

A fully local data quality lab that combines deterministic validation with grounded AI explanations.

No cloud account.
No paid API.
No external data warehouse.

## What this lab demonstrates

A data pipeline can execute successfully while still producing data that should not be trusted.

This lab uses deterministic dbt tests to detect data quality failures and a local LLM to explain the verified evidence.

## Architecture

CSV
↓
DuckDB
↓
dbt models
↓
dbt data quality tests
↓
dbt artifacts
↓
Python evidence grounding
↓
Record-level traceability
↓
Gemma 3 via Ollama
↓
Streamlit UI
↓
Human decision

## Core Principle

> AI should not guess why data failed.
> It should explain verified evidence and help a human decide what to do next.

## Data Quality Tests

The lab currently validates:

- `not_null`
- `unique`
- `accepted_values`

## Example Failures

The broken dataset intentionally contains:

- a missing `customer_id`
- a duplicated `order_id`
- an invalid `order_status`

## Grounded AI

The AI layer does not determine whether data is valid.

dbt determines the failure.

Python collects:

- the failed rule
- expected values
- affected records
- source file
- source row
- business key values

Gemma 3 explains that evidence locally.

The final remediation decision remains with a human.

## Stack

- Python
- DuckDB
- dbt Core
- dbt-duckdb
- pandas
- Ollama
- Gemma 3 4B
- Streamlit
- pytest

## Local-first

This project does not require:

- AWS
- Azure
- GCP
- Snowflake
- Databricks
- OpenAI API
- paid LLM APIs

## Project Status

Core end-to-end workflow: complete.

Additional documentation, tests, and reproducibility validation are in progress.