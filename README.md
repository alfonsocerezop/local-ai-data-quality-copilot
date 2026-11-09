# Local AI Data Quality Copilot

A fully local hands-on lab that combines deterministic data-quality validation, record-level evidence, and grounded AI explanations.

**No cloud account. No paid API. No external data warehouse.**

---

## Why this project exists

A data pipeline can run successfully and still deliver data the business should not trust.

This lab demonstrates the difference between:

```text
Pipeline success
```

and:

```text
Data trust
```

The project intentionally introduces data-quality problems, detects them with deterministic dbt tests, identifies the exact affected records, and then uses a local LLM to explain the verified evidence.

The AI does **not** decide whether the data is valid.

The deterministic controls do.

---

# Architecture

```text
CSV
 │
 ▼
Python Ingestion
 │
 ▼
DuckDB
 │
 ▼
dbt Models
 │
 ▼
dbt Data Quality Tests
 │
 ├──────── PASS ────────► Trusted Dataset
 │
 └──────── FAIL
            │
            ▼
    dbt Artifacts
    run_results.json
    manifest.json
            │
            ▼
    Python Evidence Grounding
            │
            ├─ Failed rule
            ├─ Expected values
            ├─ Observed values
            ├─ Source file
            ├─ Source row
            └─ Affected records
            │
            ▼
       Gemma 3 via Ollama
            │
            ▼
     Grounded Explanation
            │
            ▼
       Human Decision
```

---

# Core Architecture Principle

> **AI should not guess why data failed.  
> It should explain verified evidence and help a human decide what to do next.**

The responsibilities are intentionally separated:

```text
DuckDB
stores the data

dbt
defines and evaluates deterministic rules

Python
structures and grounds the evidence

Gemma 3
explains the evidence

Human
makes the remediation decision
```

---

# What the Lab Demonstrates

The lab currently validates three fundamental data-quality rules:

### 1. Completeness

```text
not_null
```

Example failure:

```text
customer_id = NULL
```

### 2. Uniqueness

```text
unique
```

Example failure:

```text
order_id = 1009
```

appears in two records.

### 3. Business Validity

```text
accepted_values
```

Expected:

```text
pending
paid
cancelled
```

Observed invalid value:

```text
completed
```

---

# Record-Level Traceability

A key objective of this project is not only to identify **what rule failed**, but also:

> **Which exact record failed?**

Every ingested row receives traceability metadata:

```text
source_row_number
source_dataset
source_file
```

This allows the Copilot to produce references such as:

```text
orders.csv:row_4
orders.csv:row_6
orders.csv:row_10
orders.csv:row_11
```

Instead of telling an engineer:

```text
customer_id contains NULL values
```

the system can identify:

```text
orders.csv:row_4
order_id: 1003
customer_id: NULL
```

This makes the output immediately actionable.

---

# Project Structure

```text
local-ai-data-quality-copilot/
│
├── app/
│   └── streamlit_app.py
│
├── copilot/
│   ├── parse_failures.py
│   └── explain_failure.py
│
├── data/
│   ├── good/
│   │   └── orders.csv
│   └── broken/
│       └── orders.csv
│
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   │
│   └── models/
│       ├── sources.yml
│       │
│       ├── staging/
│       │   └── stg_orders.sql
│       │
│       └── mart/
│           ├── fct_orders.sql
│           └── fct_orders.yml
│
├── ingestion/
│   └── load_orders.py
│
├── outputs/
│   └── .gitkeep
│
├── challenges/
├── tests/
├── warehouse/
│
├── .gitignore
├── README.md
└── requirements.txt
```

The DuckDB database and generated AI outputs are intentionally not stored in Git.

They are rebuilt locally.

---

# Technology Stack

This lab was validated with:

```text
Python       3.13.2
DuckDB       2.0.0
dbt Core     1.12.6
dbt-duckdb   1.11.1
Streamlit    1.67.0
pytest       9.2.0
Ollama       0.6.3 Python client
pandas       3.1.1
```

Local LLM:

```text
Gemma 3 4B
```

Runtime:

```text
Ollama
```

The complete clean-room workflow was validated on Windows 11.

---

# Prerequisites

Install:

- Python 3.13 or compatible version
- Git
- Ollama
- VS Code or another editor

No cloud platform is required.

You do **not** need:

```text
AWS
Azure
GCP
Snowflake
Databricks
OpenAI API
Google AI API
Anthropic API
Paid LLM APIs
```

---

# Quick Start

## 1. Clone the repository

```powershell
git clone https://github.com/alfonsocerezop/local-ai-data-quality-copilot.git
cd local-ai-data-quality-copilot
```

---

## 2. Create a virtual environment

```powershell
python -m venv .venv
```

On Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

You should see:

```text
(.venv) PS ...\local-ai-data-quality-copilot>
```

---

## 3. Install Python dependencies

```powershell
python -m pip install --upgrade pip
```

Then:

```powershell
pip install -r requirements.txt
```

---

# Install Ollama

Download and install Ollama for your operating system.

Validate the installation:

```powershell
ollama --version
```

Then download Gemma 3 4B:

```powershell
ollama pull gemma3:4b
```

Confirm the model exists:

```powershell
ollama list
```

You should see:

```text
gemma3:4b
```

Optional direct test:

```powershell
ollama run gemma3:4b
```

Exit with:

```text
/bye
```

---

# Run the Broken Dataset

Load the intentionally broken dataset:

```powershell
python ingestion\load_orders.py --dataset broken
```

Expected:

```text
Records loaded: 10
Status: SUCCESS
```

This is intentional.

The file contains bad data, but the ingestion pipeline still succeeds.

That demonstrates:

> **Pipeline success does not guarantee data trust.**

---

## Build dbt Models

```powershell
dbt run --project-dir dbt --profiles-dir dbt
```

Expected:

```text
PASS=2
ERROR=0
```

The models should still build successfully.

---

## Run Data Quality Tests

```powershell
dbt test --project-dir dbt --profiles-dir dbt
```

Expected:

```text
PASS=1
ERROR=3
TOTAL=4
```

The expected failures are:

```text
customer_id not_null     FAIL
order_id unique          FAIL
order_status accepted    FAIL

order_id not_null        PASS
```

This failure is expected behavior.

The lab is not broken.

The deterministic controls are doing their job.

---

# Generate Grounded Evidence

After `dbt test`, immediately run:

```powershell
python copilot\parse_failures.py
```

Expected evidence includes:

```text
orders.csv:row_4
orders.csv:row_6
orders.csv:row_10
orders.csv:row_11
```

The parser generates:

```text
outputs/grounded_failures.json
```

This file contains:

- failed test;
- model;
- column;
- expected values;
- exact affected records;
- source file;
- source row;
- business-key values.

---

# Generate the Local AI Explanation

Run:

```powershell
python copilot\explain_failure.py
```

Gemma receives only the grounded evidence produced by the deterministic layer.

It is explicitly instructed not to invent:

- source systems;
- ETL processes;
- business workflows;
- applications;
- data lineage;
- teams;
- root causes.

When the evidence is insufficient, the model must state:

```text
Root cause cannot be determined from the available evidence.
```

The generated explanations are stored in:

```text
outputs/ai_explanations.json
```

---

# Launch the Streamlit Application

Run:

```powershell
streamlit run app\streamlit_app.py
```

The application normally opens at:

```text
http://localhost:8501
```

The UI allows you to select:

```text
good
broken
```

and execute the complete pipeline.

---

# Expected Broken Scenario

```text
Ingestion       PASS
dbt Models      PASS
Data Quality    FAIL
Failures        3
```

For every failure, the UI displays:

- deterministic test;
- affected column;
- exact affected records;
- source-row reference;
- expected values;
- grounded AI explanation;
- human decision.

---

# Expected Good Scenario

Select:

```text
good
```

Expected:

```text
Ingestion       PASS
dbt Models      PASS
Data Quality    PASS
Failures        0
```

The AI layer is skipped.

This is intentional.

The architecture follows:

```text
deterministic controls
        │
        ▼
     failure?
      /     \
    no       yes
    │         │
    ▼         ▼
   stop    invoke AI
```

AI is used only when interpretation is required.

---

# Troubleshooting

## PowerShell says script execution is disabled

Error:

```text
running scripts is disabled on this system
```

Run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate:

```powershell
.\.venv\Scripts\Activate.ps1
```

`Scope Process` applies only to the current PowerShell session.

---

## `ollama` is not recognized

First verify whether Ollama exists:

```powershell
Test-Path "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
```

If it returns:

```text
True
```

test directly:

```powershell
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" --version
```

For the current session, refresh PATH with:

```powershell
$env:PATH = "$env:LOCALAPPDATA\Programs\Ollama;$env:PATH"
```

Then:

```powershell
ollama --version
```

Opening a new PowerShell window may also refresh PATH.

---

## Gemma is not available

Check:

```powershell
ollama list
```

If `gemma3:4b` is missing:

```powershell
ollama pull gemma3:4b
```

---

## DuckDB cannot create `warehouse/lab.duckdb`

The current ingestion script automatically creates the required `warehouse` directory.

If using an older version of the repository, ensure `load_orders.py` contains:

```python
db_path.parent.mkdir(parents=True, exist_ok=True)
```

before:

```python
duckdb.connect(...)
```

---

## dbt cannot find the DuckDB database

Run dbt commands from the repository root:

```text
local-ai-data-quality-copilot
```

Use:

```powershell
dbt run --project-dir dbt --profiles-dir dbt
```

The profile expects:

```yaml
path: "warehouse/lab.duckdb"
```

---

## Parser returns `Detected failures: 0`

This normally means a dbt command overwrote:

```text
dbt/target/run_results.json
```

Use this exact order:

```text
1. load dataset
2. dbt run
3. dbt test
4. parse failures
```

For example:

```powershell
python ingestion\load_orders.py --dataset broken
```

```powershell
dbt run --project-dir dbt --profiles-dir dbt
```

```powershell
dbt test --project-dir dbt --profiles-dir dbt
```

Then immediately:

```powershell
python copilot\parse_failures.py
```

Do not run another dbt command between `dbt test` and the parser.

---

## `source_row_number` not found

This means traceability metadata has not been propagated through the pipeline.

Ensure:

```text
raw_orders
```

contains:

```text
source_row_number
source_dataset
source_file
```

and that both:

```text
stg_orders
fct_orders
```

select those fields.

Then rerun:

```powershell
python ingestion\load_orders.py --dataset broken
```

```powershell
dbt run --project-dir dbt --profiles-dir dbt