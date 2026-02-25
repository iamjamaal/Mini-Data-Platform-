┌──────────────────┐     ┌──────────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│     MinIO         │     │    Apache Airflow     │     │   PostgreSQL     │     │    Metabase      │
│  (Object Store)   │────▶│   (Orchestrator)      │────▶│  (Warehouse)     │────▶│   (BI / Viz)     │
│                   │     │                       │     │                  │     │                  │
│  raw-data/        │     │  sales_etl_pipeline   │     │  sales schema    │     │  2 Dashboards    │
│  └─ sales_data.csv│     │  ┌─────────────────┐  │     │  ├─ raw_orders   │     │  ├─ Executive    │
│     (250K rows)   │     │  │ extract         │  │     │  ├─ 9 views     │     │  └─ Operations   │
│     (55 MB)       │     │  │ transform       │  │     │  └─ 5 indexes   │     │                  │
│                   │     │  │ load (batched)  │  │     │                  │     │  17 charts       │
│  Port: 9000/9001  │     │  │ validate        │  │     │  Port: 5432     │     │  4 filters       │
│                   │     │  └─────────────────┘  │     │                  │     │  Port: 3000      │
└──────────────────┘     │  Port: 8080           │     └──────────────────┘     └──────────────────┘
                          └──────────────────────┘

                          GitHub Actions CI/CD
                    ┌─────────────────────────────────┐
                    │  CI: Build + Schema Validation   │
                    │  CD: Auto-deploy on push to main │
                    │  Validation: End-to-end flow     │
                    │  (MinIO → Airflow → PG → MB)     │
                    └─────────────────────────────────┘