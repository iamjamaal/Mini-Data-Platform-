# Mini Data Platform

[![CI — Build & Test](https://github.com/iamjamaal/Mini-Data-Platform-/actions/workflows/ci.yml/badge.svg)](https://github.com/iamjamaal/Mini-Data-Platform-/actions/workflows/ci.yml)
[![CD — Deploy to Test](https://github.com/iamjamaal/Mini-Data-Platform-/actions/workflows/cd.yml/badge.svg)](https://github.com/iamjamaal/Mini-Data-Platform-/actions/workflows/cd.yml)
[![Data Flow Validation](https://github.com/iamjamaal/Mini-Data-Platform-/actions/workflows/data-validation.yml/badge.svg)](https://github.com/iamjamaal/Mini-Data-Platform-/actions/workflows/data-validation.yml)

A fully containerised, end-to-end sales data platform built with Docker Compose. Raw CSV files land in object storage, an orchestrated ETL pipeline cleans and loads them into a relational data warehouse, and a business intelligence tool turns the data into interactive dashboards — all automated through a three-stage CI/CD pipeline.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture & Data Flow](#architecture--data-flow)
3. [Tech Stack](#tech-stack)
4. [Prerequisites](#prerequisites)
5. [Quick Start](#quick-start)
6. [Project Structure](#project-structure)
7. [Services & Access](#services--access)
8. [Data Pipeline](#data-pipeline)
9. [Data Model](#data-model)
10. [Metabase Dashboards](#metabase-dashboards)
11. [CI/CD Pipelines](#cicd-pipelines)
12. [Environment Variables](#environment-variables)
13. [Troubleshooting](#troubleshooting)

---

## Overview

This project implements a **mini data platform** for analysing retail sales data. It was built as a CI/CD module lab (AmaliTech DEM012) to demonstrate how the four core components of a modern data stack — ingestion, orchestration, storage, and visualisation — fit together and can be automated end-to-end.

### What the platform does

1. **Ingests** a 249,704-row sales CSV file into MinIO object storage (an S3-compatible data lake layer).
2. **Processes** the raw file daily through an Apache Airflow ETL pipeline that cleans, validates, and loads the data into PostgreSQL.
3. **Stores** the cleaned data in a structured data warehouse schema with 9 pre-built analytical views covering revenue, products, regions, customers, shipping, and data quality.
4. **Visualises** the data through Metabase dashboards that connect directly to the PostgreSQL views and serve as the reporting layer.

### Dataset

The sample dataset is a retail superstore sales dataset spanning **January 2023 – June 2025**:

| Metric | Value |
|---|---|
| Total rows | 249,704 |
| Total revenue | $48.4 million |
| Total profit | $2.9 million |
| Unique orders | 100,240 |
| Unique customers | 4,968 |
| Unique products | 1,862 |
| Categories | Furniture, Technology, Office Supplies |
| Regions | West, Central, East, South (US) |

---

## Architecture & Data Flow

```
                        MINI DATA PLATFORM — DATA FLOW
  ─────────────────────────────────────────────────────────────────────────

  ┌──────────────┐   CSV file   ┌──────────────┐  cleaned rows  ┌──────────────┐
  │              │─────────────▶│              │───────────────▶│              │
  │    MinIO     │              │   Airflow    │                │  PostgreSQL  │
  │  Data Lake   │              │  ETL Pipeline│                │    Data      │
  │              │◀─────────────│              │                │  Warehouse   │
  │  port 9001   │  download    │  port 8080   │                │  port 5432   │
  └──────────────┘              └──────────────┘                └──────────────┘
                                                                       │
                                                                       │ SQL queries
                                                                       ▼
                                                               ┌──────────────┐
                                                               │              │
                                                               │   Metabase   │
                                                               │  Dashboards  │
                                                               │              │
                                                               │  port 3001   │
                                                               └──────────────┘

  ─────────────────────────────────────────────────────────────────────────
  PIPELINE TASKS (Airflow DAG: sales_etl_pipeline, runs @daily)

    extract_from_minio  ──▶  transform_data  ──▶  load_to_postgres  ──▶  validate_load

    1. Extract:   Download sales_data.csv from MinIO raw-data bucket
    2. Transform: Clean with Pandas — parse dates, strip whitespace,
                  fill nulls, remove zero-value rows, deduplicate
    3. Load:      Batch UPSERT into sales.raw_orders (5,000 rows/batch)
    4. Validate:  Assert row count, no null dates, positive revenue,
                  plausible date range
  ─────────────────────────────────────────────────────────────────────────
```

---

## Tech Stack

| Component | Tool | Version | Role |
|---|---|---|---|
| Containerisation | Docker + Docker Compose | Compose v2 | Runs all services in isolation |
| Object Storage | MinIO | latest | S3-compatible data lake (raw files) |
| Orchestration | Apache Airflow | 2.8.1 | Schedules and runs the ETL pipeline |
| Data Warehouse | PostgreSQL | 15 | Stores cleaned, queryable data |
| BI / Dashboards | Metabase | latest | Charts, tables, and KPI dashboards |
| Notebooks | JupyterLab | scipy-notebook | Ad-hoc data exploration |
| CI/CD | GitHub Actions | — | Automated build, deploy, and validation |
| Data Processing | Pandas | 2.1.4 | In-pipeline data cleaning and transformation |
| Python Runtime | Python | 3.11 | Airflow DAG language |

---

## Prerequisites

Before running this project you will need the following installed on your machine:

| Tool | Minimum Version | Notes |
|---|---|---|
| Docker Desktop | 24.0+ | Includes Docker Compose v2 |
| Git | 2.30+ | — |
| Git LFS | 3.0+ | Required — the 55 MB CSV is stored in Git LFS |

> **Git LFS is required.** The sales CSV (`minio/sample-data/sales_data.csv`) is tracked via Git LFS. Without it the file will be a pointer stub and the pipeline will fail.
>
> Install: https://git-lfs.com/ — then run `git lfs install` once.

**System resources recommended:** 4 GB RAM, 10 GB free disk space (Docker images + data volumes).

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/iamjamaal/Mini-Data-Platform-.git
cd Mini-Data-Platform-
```

Git LFS will automatically download the CSV during clone. Verify it with:

```bash
ls -lh minio/sample-data/sales_data.csv
# Expected: ~55 MB file, NOT a text pointer
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

The defaults in `.env.example` work out of the box for local development. See [Environment Variables](#environment-variables) for details.

> For production use, generate a real Fernet key for Airflow:
> ```bash
> python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
> ```
> Replace the `AIRFLOW__CORE__FERNET_KEY` value in `.env` with the output.

### 3. Start the platform

```bash
docker compose up -d
```

This starts all 6 services. First-time startup takes 3–5 minutes as Docker pulls images and runs initialisers.

### 4. Wait for services to become healthy

```bash
# Check status of all services
docker compose ps

# Or watch until all show "healthy"
watch docker compose ps
```

All four core services — `postgres`, `minio`, `airflow`, `metabase` — must show `healthy` before proceeding.

### 5. Trigger the ETL pipeline

The `sales_etl_pipeline` DAG runs on a `@daily` schedule. To run it immediately:

```bash
# Option A — via Airflow web UI
# Go to http://localhost:8080, log in, click the toggle to unpause the DAG,
# then click the play button (▶) to trigger a manual run.

# Option B — via CLI
docker exec airflow airflow dags unpause sales_etl_pipeline
docker exec airflow airflow dags trigger sales_etl_pipeline
```

The pipeline takes approximately **4–5 minutes** to process all 249,704 rows.

### 6. Access the services

| Service | URL | Username | Password |
|---|---|---|---|
| Airflow | http://localhost:8080 | `admin` | `admin` |
| MinIO Console | http://localhost:9001 | `minioadmin` | `minioadmin123` |
| Metabase | http://localhost:3001 | `admin@dataplatform.com` | `Admin1234!` |
| JupyterLab | http://localhost:8888 | — | No password |

### 7. Shut down

```bash
# Stop all services (preserves data volumes)
docker compose down

# Stop and wipe all data volumes (full reset)
docker compose down -v
```

---

## Project Structure

```
Mini-Data-Platform-/
│
├── .github/
│   └── workflows/
│       ├── ci.yml                  # CI: builds images and checks service health on every commit
│       ├── cd.yml                  # CD: full deploy + endpoint verification on push to main
│       └── data-validation.yml     # Data flow: end-to-end MinIO → Airflow → PG → Metabase check
│
├── airflow/
│   ├── dags/
│   │   └── sales_pipeline.py       # The ETL DAG — 4 tasks, @daily, idempotent via UPSERT
│   ├── logs/                       # Airflow task logs (gitignored)
│   ├── Dockerfile                  # Extends apache/airflow:2.8.1, adds minio+psycopg2+pandas
│   └── entrypoint.sh               # Waits for PG, runs db migrations, creates admin user
│
├── postgres/
│   └── init.sql                    # Schema, raw_orders table, 9 analytical views, 5 indexes
│
├── minio/
│   └── sample-data/
│       └── sales_data.csv          # 249,704-row retail sales dataset (Git LFS, ~55 MB)
│
├── docs/
│   ├── architecture_diagram.png    # Visual architecture overview
│   └── screenshots/
│       ├── airflow/                # 6 screenshots: login, DAG list, graph, logs, success
│       └── metabase/               # 13 screenshots: dashboards, individual questions
│
├── .env.example                    # Template for all environment variables (safe to commit)
├── .env                            # Your local config (gitignored — never commit this)
├── .gitignore                      # Ignores .env, volumes, logs, __pycache__, .venv
├── .gitattributes                  # Git LFS tracking for *.csv files
├── docker-compose.yml              # Defines all 6 services + volumes + network
├── SERVICES.md                     # Quick-reference: ports and credentials
└── README.md                       # This file
```

---

## Services & Access

### Service Overview

| Service | Container | Host Port | Purpose |
|---|---|---|---|
| PostgreSQL | `postgres` | 5432 | Primary data warehouse |
| MinIO API | `minio` | 9000 | S3-compatible object storage API |
| MinIO Console | `minio` | 9001 | MinIO web UI for browsing buckets |
| Airflow | `airflow` | 8080 | Pipeline orchestration web UI |
| Metabase | `metabase` | 3001 | BI dashboards and visualisations |
| JupyterLab | `jupyter` | 8888 | Python notebook environment |

> `minio-init` is a one-time initialisation container. It creates the `raw-data` bucket and uploads `sales_data.csv` on first startup. It exits after that and has no exposed port.

### Internal Networking

All services communicate over a private Docker bridge network named `data-platform`. From inside any container, services are reachable by their container name — for example, Airflow connects to PostgreSQL at `postgres:5432`, not `localhost:5432`.

### Credentials Reference

| Service | Username / Email | Password |
|---|---|---|
| PostgreSQL | `dataplatform` | `dataplatform_pass` |
| MinIO | `minioadmin` | `minioadmin123` |
| Airflow | `admin` | `admin` |
| Metabase | `admin@dataplatform.com` | `Admin1234!` |

---

## Data Pipeline

The pipeline is defined in `airflow/dags/sales_pipeline.py` as a DAG named `sales_etl_pipeline`.

### DAG Properties

| Property | Value |
|---|---|
| DAG ID | `sales_etl_pipeline` |
| Schedule | `@daily` |
| Start date | 2025-01-01 |
| Catchup | Disabled |
| Retries | 2 per task, 2-minute delay |
| Owner | `noah.jamal.nabila` |
| Tags | `etl`, `sales`, `superstore` |

### Task Breakdown

#### Task 1 — `extract_from_minio`

Downloads `sales_data.csv` from the `raw-data` MinIO bucket to `/tmp/sales_data.csv` inside the Airflow container. Counts the rows and pushes `csv_path` and `raw_row_count` to XCom for downstream tasks.

#### Task 2 — `transform_data`

Reads the CSV with Pandas and applies the following cleaning operations in order:

| Step | Operation | Reason |
|---|---|---|
| 1 | Strip whitespace from `Customer Name` | Leading/trailing spaces cause duplicate customers |
| 2 | Fill missing `Postal Code` with `NULL` | ~1,878 entries have no postal code |
| 3 | Parse `Discount` to float, fill blank with `0.0` | ~1,833 entries have no discount value |
| 4 | Parse `Order Date` / `Ship Date` from `M/D/YYYY` to `DATE` | Source format is non-standard |
| 5 | Remove rows where both `Sales = 0` AND `Profit = 0` | These are data entry errors |
| 6 | Deduplicate on `Row ID` (keep last) | Prevents primary key conflicts on reload |
| 7 | Round `Sales`, `Profit`, `Discount` to 4, 4, 2 dp respectively | Matches the database column precision |

The cleaned DataFrame is written to `/tmp/sales_data_clean.csv`. The cleaned row count is pushed to XCom.

#### Task 3 — `load_to_postgres`

Reads the cleaned CSV and performs a batched **UPSERT** (`INSERT ... ON CONFLICT (row_id) DO UPDATE`) into `sales.raw_orders`. Processing is done in batches of 5,000 rows to keep memory usage low on the 249,704-row dataset.

Because it uses `ON CONFLICT ... DO UPDATE`, the pipeline is **idempotent** — re-running it will update existing rows rather than create duplicates.

#### Task 4 — `validate_load`

Runs four post-load assertions against the database:

| Check | Assertion |
|---|---|
| Row count | `COUNT(*) >= expected_clean_rows` |
| Null dates | `COUNT(*) WHERE order_date IS NULL = 0` |
| Revenue | `SUM(sales) > 0` |
| Date range | Logged for human inspection |

If any assertion fails, the task raises a `ValueError` and the DAG run is marked as failed.

### Viewing Logs

Task logs are available in the Airflow UI under **DAGs → sales_etl_pipeline → Grid → [run] → [task] → Logs**, or via CLI:

```bash
docker exec airflow airflow tasks logs sales_etl_pipeline load_to_postgres -1
```

---

## Data Model

All objects live in the `sales` PostgreSQL schema inside the `sales_warehouse` database.

### Raw Table — `sales.raw_orders`

The ETL landing table. Mirrors the CSV structure exactly with 21 columns:

| Column | Type | Notes |
|---|---|---|
| `row_id` | `INTEGER` | Primary key |
| `order_id` | `VARCHAR(20)` | — |
| `order_date` | `DATE` | — |
| `ship_date` | `DATE` | — |
| `ship_mode` | `VARCHAR(20)` | Standard Class, Second Class, First Class, Same Day |
| `customer_id` | `VARCHAR(10)` | — |
| `customer_name` | `VARCHAR(100)` | — |
| `segment` | `VARCHAR(20)` | Consumer, Corporate, Home Office |
| `country` | `VARCHAR(50)` | US only in this dataset |
| `city` | `VARCHAR(100)` | — |
| `state` | `VARCHAR(50)` | — |
| `postal_code` | `VARCHAR(10)` | Nullable (~1,878 missing) |
| `region` | `VARCHAR(10)` | West, Central, East, South |
| `product_id` | `VARCHAR(20)` | — |
| `category` | `VARCHAR(20)` | Furniture, Technology, Office Supplies |
| `sub_category` | `VARCHAR(20)` | 17 sub-categories |
| `product_name` | `VARCHAR(255)` | — |
| `sales` | `NUMERIC(12,4)` | Revenue in USD |
| `quantity` | `INTEGER` | — |
| `discount` | `NUMERIC(4,2)` | Nullable (~1,833 missing) |
| `profit` | `NUMERIC(12,4)` | Can be negative |
| `loaded_at` | `TIMESTAMP` | Set by the ETL on each load |

**Indexes:** `order_date`, `region`, `category`, `customer_id`, `order_id`

### Analytical Views

Nine read-only views are built on top of `raw_orders`. These are what Metabase queries:

| View | Description |
|---|---|
| `sales.daily_summary` | Orders, units, revenue, and profit aggregated by day |
| `sales.monthly_summary` | Same metrics aggregated by month, plus profit margin % |
| `sales.category_performance` | Revenue, profit, margin, and avg discount by category and sub-category |
| `sales.regional_performance` | Revenue and profit broken down by region, state, and customer segment |
| `sales.customer_segments` | Aggregate stats for Consumer, Corporate, and Home Office segments |
| `sales.shipping_analysis` | Order count, average ship time, and revenue by ship mode |
| `sales.top_customers` | Per-customer lifetime value: order count, total revenue, first/last order |
| `sales.discount_impact` | Revenue and margin grouped by discount band (none, 1–20%, 21–40%, 41%+) |
| `sales.data_quality` | Meta-view: row counts, null counts, date range — used for data monitoring |

All views are granted `SELECT` to `PUBLIC` so Metabase can query them without elevated privileges.

### Querying Directly

```bash
# Connect via psql
docker exec -it postgres psql -U dataplatform -d sales_warehouse

# Example queries
SELECT * FROM sales.monthly_summary ORDER BY month DESC LIMIT 6;
SELECT * FROM sales.data_quality;
SELECT category, total_revenue FROM sales.category_performance ORDER BY total_revenue DESC;
```

---

## Metabase Dashboards

Metabase is available at **http://localhost:3001** after the platform starts.

The **Sales Warehouse** collection contains the following saved questions and one dashboard:

### Sales Analytics Dashboard

The main dashboard (`Sales Analytics`) provides an executive-level view of the entire dataset:

| Tile | Chart Type | Source View |
|---|---|---|
| Total Revenue | KPI Card | `raw_orders` |
| Total Orders | KPI Card | `raw_orders` |
| Unique Customers | KPI Card | `raw_orders` |
| Overall Profit Margin | KPI Card | `raw_orders` |
| Monthly Revenue and Profit | Line Chart | `monthly_summary` |
| Revenue by Product Category | Bar Chart | `category_performance` |
| Revenue by Region | Bar Chart | `regional_performance` |
| Revenue by Customer Segment | Donut Chart | `customer_segments` |
| Top 10 Customers by Revenue | Table | `top_customers` |
| Orders and Revenue by Ship Mode | Bar Chart | `shipping_analysis` |
| Profit Margin by Sub-Category | Bar Chart | `category_performance` |

### Individual Questions (Saved)

| Question | What It Shows |
|---|---|
| Revenue and Orders Over Time | Quarterly bar + trend line |
| Category Performance | Full sub-category breakdown table |
| Customer Segments | Consumer / Corporate / Home Office comparison |
| Daily Summary | Day-by-day orders and revenue |
| Data Quality | Row counts, nulls, date range — pipeline health check |
| Discount Impact | Margin analysis by discount band |
| Monthly Summary | Month-by-month revenue trend table |
| Raw Orders | Row-level order data browser |
| Regional Performance | State and segment-level revenue table |
| Shipping Analysis | Ship mode comparison |
| Top Customers | Customer lifetime value leaderboard |

### Connecting a New Database (if needed)

If Metabase loses its database connection after a reset:

1. Go to **Settings (gear icon) → Admin → Databases**
2. Click **Add a database**
3. Select **PostgreSQL** and fill in:
   - Host: `postgres`
   - Port: `5432`
   - Database name: `sales_warehouse`
   - Username: `dataplatform`
   - Password: `dataplatform_pass`

---

## CI/CD Pipelines

Three GitHub Actions workflows automate the full software delivery lifecycle:

### 1. CI — Build & Test (`ci.yml`)

**Triggers:** Every push to `main` or `develop`, and every pull request to `main`.

**What it does:**

| Step | Description |
|---|---|
| Checkout + LFS | Clones the repo and downloads the CSV via Git LFS |
| Build images | Runs `docker compose build` for all services |
| Start services | Brings up the full stack |
| Health check | Asserts all four core services reach `healthy` state |
| MinIO check | Verifies `sales_data.csv` is present in the `raw-data` bucket |
| PostgreSQL check | Lists the `sales` schema tables and views |
| DAG syntax check | Confirms `sales_etl_pipeline` is parsed and registered by the Airflow scheduler |
| Tear down | Runs `docker compose down -v` to clean up |

**Purpose:** Catches broken images, missing schema objects, and unparseable DAGs before they reach `main`.

### 2. CD — Deploy to Test (`cd.yml`)

**Triggers:** Every push to `main`.

**What it does:**

| Step | Description |
|---|---|
| Full rebuild | `docker compose build --no-cache` — no caching ensures a clean image |
| Deploy | `docker compose up -d` |
| Health polling | Waits up to 10 minutes for all services to reach `healthy` |
| Endpoint checks | `curl` verifies Airflow, Metabase, and MinIO API all respond |
| Schema verification | Asserts 9 views exist in the `sales` schema |
| Tear down | Clean up after deployment verification |

**Purpose:** Simulates a production deployment and verifies the entire platform is accessible and correctly configured.

### 3. Data Flow Validation (`data-validation.yml`)

**Triggers:** Every push to `main`.

**What it does — end-to-end pipeline validation:**

| Step | What is validated |
|---|---|
| Step 1 — Ingestion | `sales_data.csv` is present and accessible in the MinIO `raw-data` bucket |
| Step 2 — Processing | Triggers the `sales_etl_pipeline` DAG and polls until it reaches `success` state (up to 10 minutes) |
| Step 3 — Storage | Queries PostgreSQL and asserts 200,000+ rows loaded with correct revenue figures |
| Step 4 — Visualisation | Hits the Metabase `/api/health` endpoint and asserts `"status":"ok"` |

**Purpose:** The only workflow that actually runs the pipeline end-to-end. This is the source-of-truth for whether the full data flow — MinIO → Airflow → PostgreSQL → Metabase — works correctly.

---

## Environment Variables

All configuration lives in `.env`. Copy `.env.example` to `.env` to get started. The `.env` file is gitignored and must never be committed.

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_USER` | `dataplatform` | PostgreSQL superuser username |
| `POSTGRES_PASSWORD` | `dataplatform_pass` | PostgreSQL superuser password |
| `POSTGRES_DB` | `sales_warehouse` | Database name |
| `MINIO_ROOT_USER` | `minioadmin` | MinIO root access key |
| `MINIO_ROOT_PASSWORD` | `minioadmin123` | MinIO root secret key |
| `MINIO_BUCKET` | `raw-data` | Bucket name for raw CSV files |
| `AIRFLOW__CORE__FERNET_KEY` | `<generate>` | Encryption key for Airflow connection passwords |
| `AIRFLOW_ADMIN_USER` | `admin` | Airflow web UI username |
| `AIRFLOW_ADMIN_PASSWORD` | `admin` | Airflow web UI password |
| `MB_DB_TYPE` | `postgres` | Metabase backend database type |
| `MB_DB_DBNAME` | `sales_warehouse` | Metabase metadata database name |
| `MB_DB_PORT` | `5432` | Metabase database port |
| `MB_DB_USER` | `dataplatform` | Metabase database user |
| `MB_DB_PASS` | `dataplatform_pass` | Metabase database password |
| `MB_DB_HOST` | `postgres` | Metabase database host (container name) |

> Metabase stores its own internal metadata (dashboards, questions, users) in the same PostgreSQL database as the sales data, using a separate schema managed by Metabase itself.

---

## Troubleshooting

### Services are not becoming healthy

```bash
# Check individual service logs
docker logs airflow --tail 50
docker logs metabase --tail 50
docker logs postgres --tail 50

# Check what state each service is in
docker compose ps
```

Airflow typically takes the longest (60–90 seconds). Metabase takes up to 2 minutes on first startup while it initialises its internal schema.

### The CSV is a pointer file, not actual data

```bash
# Check Git LFS status
git lfs status

# Pull LFS objects if missing
git lfs pull
```

If `ls -lh minio/sample-data/sales_data.csv` shows a file smaller than 1 KB, Git LFS was not installed before cloning. Run `git lfs install` then `git lfs pull`.

### MinIO bucket is empty / sales_data.csv missing

The `minio-init` container runs once and exits. If MinIO data was wiped with `docker compose down -v`, re-run:

```bash
docker compose up minio-init
```

### Airflow DAG is not appearing

```bash
# Check if the DAG file has Python syntax errors
docker exec airflow python /opt/airflow/dags/sales_pipeline.py

# Force the scheduler to rescan DAGs
docker exec airflow airflow dags reserialize
```

### Metabase cannot connect to PostgreSQL

Metabase connects to PostgreSQL using the `MB_DB_*` variables in `.env`. If the connection is broken:

1. Verify `.env` has `MB_DB_HOST=postgres` (the container name, not `localhost`)
2. Confirm PostgreSQL is healthy: `docker inspect --format='{{.State.Health.Status}}' postgres`
3. In Metabase admin, remove and re-add the database connection (see [Connecting a New Database](#connecting-a-new-database-if-needed))

### Pipeline DAG fails with connection errors

The DAG uses environment variables for MinIO and PostgreSQL connections. If the pipeline fails at `extract_from_minio` or `load_to_postgres`, check that the Airflow container has the correct env vars:

```bash
docker exec airflow env | grep -E 'MINIO|TARGET_DB'
```

### Full reset

To wipe everything and start clean:

```bash
docker compose down -v          # Remove containers and volumes
docker volume prune -f          # Remove any orphaned volumes
docker compose up -d            # Fresh start
```
