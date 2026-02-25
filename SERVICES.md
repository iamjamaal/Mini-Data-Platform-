# Mini Data Platform — Services & Ports

| Service      | Container      | Host Port | Container Port | URL                          | Description                  |
|--------------|----------------|-----------|----------------|------------------------------|------------------------------|
| PostgreSQL   | `postgres`     | 5432      | 5432           | `localhost:5432`             | Primary data warehouse (SQL) |
| MinIO API    | `minio`        | 9000      | 9000           | `http://localhost:9000`      | Object storage S3 API        |
| MinIO Console| `minio`        | 9001      | 9001           | `http://localhost:9001`      | MinIO web UI                 |
| Airflow      | `airflow`      | 8080      | 8080           | `http://localhost:8080`      | Workflow orchestration UI    |
| Jupyter Lab  | `jupyter`      | 8888      | 8888           | `http://localhost:8888`      | Notebook environment         |
| Metabase     | `metabase`     | 3001      | 3000           | `http://localhost:3001`      | BI / visualization dashboard |

## Default Credentials

| Service        | Username           | Password            |
|----------------|--------------------|---------------------|
| PostgreSQL     | `dataplatform`     | `dataplatform_pass` |
| MinIO          | `minioadmin`       | `minioadmin123`     |
| Airflow        | `admin`            | `admin`             |
| Metabase       | `dataplatform`     | `dataplatform_pass` |

## Notes

- `minio-init` is a one-off init container — it creates the `raw-data` bucket and uploads `sales_data.csv`. It has no exposed ports.
- Metabase maps host port **3001** → container port **3000** to avoid conflicts.
- All services communicate internally over the `data-platform` bridge network.
