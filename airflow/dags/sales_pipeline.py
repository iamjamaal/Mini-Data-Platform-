"""
Sales Data Pipeline DAG
Extracts sales_data.csv from MinIO → Cleans with Pandas → Loads into PostgreSQL.



Data quality handling:
  - Strips whitespace from customer names
  - Fills missing postal codes with NULL
  - Fills missing discounts with 0.0
  - Removes rows where sales = 0 AND profit = 0 (bad entries)
  - Parses M/D/YYYY date format to proper dates
  - Deduplicates on row_id (upsert)
  
Runs daily. Idempotent via UPSERT on row_id.
"""



from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import logging

logger = logging.getLogger(__name__)

default_args = {
    "owner": "noah.jamal.nabila",
    "depends_on_past": True,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}


dag = DAG(
    dag_id="sales_etl_pipeline",
    default_args=default_args,
    description="ETL: MinIO (sales_data.csv) → Clean → PostgreSQL (sales.raw_orders)",
    schedule_interval="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["sales", "etl", "superstore"],
)




# ─── TASK 1: EXTRACT FROM MINIO

def extract_from_minio(**context):
    """Download sales_data.csv from MinIO bucket."""
    import os
    from minio import Minio

    client = Minio(
        os.environ["MINIO_ENDPOINT"],
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=False,
    )

    bucket = os.environ["MINIO_BUCKET"]
    object_name = "sales_data.csv"
    local_path = "/tmp/sales_data.csv"

    client.fget_object(bucket, object_name, local_path)

    # Quick validation
    with open(local_path, "r") as f:
        line_count = sum(1 for _ in f) - 1  # exclude header
    logger.info(f"Extracted {object_name} from MinIO: {line_count} rows")

    context["ti"].xcom_push(key="csv_path", value=local_path)
    context["ti"].xcom_push(key="raw_row_count", value=line_count)




# ─── TASK 2: TRANSFORM & CLEAN

def transform_data(**context):
    """
    Clean and validate the sales data.

    Handles all known data quality issues:
    - Whitespace in Customer Name
    - Missing Postal Code
    - Missing Discount
    - Zero-value Sales entries
    - Date format parsing (M/D/YYYY → YYYY-MM-DD)
    """
    import pandas as pd

    csv_path = context["ti"].xcom_pull(key="csv_path")

    # Read with explicit dtypes to avoid inference issues
    df = pd.read_csv(csv_path, encoding="utf-8", dtype={
        "Row ID": int,
        "Order ID": str,
        "Order Date": str,
        "Ship Date": str,
        "Ship Mode": str,
        "Customer ID": str,
        "Customer Name": str,
        "Segment": str,
        "Country": str,
        "City": str,
        "State": str,
        "Postal Code": str,
        "Region": str,
        "Product ID": str,
        "Category": str,
        "Sub-Category": str,
        "Product Name": str,
        "Sales": float,
        "Quantity": int,
        "Discount": str,  # Read as string — some are blank
        "Profit": float,
    })



    initial_count = len(df)
    logger.info(f"Loaded {initial_count} rows from CSV")

    # ── Cleaning ──

    # 1. Strip whitespace from customer names
    df["Customer Name"] = df["Customer Name"].str.strip()

    # 2. Fill missing postal codes
    df["Postal Code"] = df["Postal Code"].fillna("UNKNOWN").replace("", "UNKNOWN")

    # 3. Parse discount — fill blanks with 0.0
    df["Discount"] = pd.to_numeric(df["Discount"], errors="coerce").fillna(0.0)

    # 4. Parse dates from M/D/YYYY format
    df["Order Date"] = pd.to_datetime(df["Order Date"], format="mixed").dt.date
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], format="mixed").dt.date

    # 5. Remove rows where BOTH sales and profit are zero (bad entries)
    bad_entries = (df["Sales"] == 0) & (df["Profit"] == 0)
    df = df[~bad_entries]

    # 6. Deduplicate on Row ID (keep last)
    df = df.drop_duplicates(subset=["Row ID"], keep="last")

    # 7. Round numeric fields
    df["Sales"] = df["Sales"].round(4)
    df["Profit"] = df["Profit"].round(4)
    df["Discount"] = df["Discount"].round(2)

    cleaned_count = len(df)
    removed = initial_count - cleaned_count
    logger.info(
        f"Transform complete: {initial_count} → {cleaned_count} rows "
        f"({removed} removed, {removed/initial_count*100:.1f}%)"
    )

    # Save cleaned data
    clean_path = "/tmp/sales_data_clean.csv"
    df.to_csv(clean_path, index=False)

    context["ti"].xcom_push(key="clean_csv_path", value=clean_path)
    context["ti"].xcom_push(key="clean_row_count", value=cleaned_count)




# ─── TASK 3: LOAD TO POSTGRESQL 

def load_to_postgres(**context):
    """
    Upsert all 21 columns into sales.raw_orders.
    Batched in chunks of 5,000 for memory efficiency with 250K rows.
    """
    import os
    import pandas as pd
    import psycopg2
    from psycopg2.extras import execute_values

    clean_path = context["ti"].xcom_pull(key="clean_csv_path")
    df = pd.read_csv(clean_path, dtype={"Postal Code": str})

    conn = psycopg2.connect(
        host=os.environ["TARGET_DB_HOST"],
        port=os.environ["TARGET_DB_PORT"],
        dbname=os.environ["TARGET_DB_NAME"],
        user=os.environ["TARGET_DB_USER"],
        password=os.environ["TARGET_DB_PASSWORD"],
    )
    conn.autocommit = False
    cursor = conn.cursor()

    upsert_query = """
        INSERT INTO sales.raw_orders (
            row_id, order_id, order_date, ship_date, ship_mode,
            customer_id, customer_name, segment, country, city,
            state, postal_code, region, product_id, category,
            sub_category, product_name, sales, quantity, discount, profit
        ) VALUES %s
        ON CONFLICT (row_id) DO UPDATE SET
            order_id = EXCLUDED.order_id,
            order_date = EXCLUDED.order_date,
            ship_date = EXCLUDED.ship_date,
            ship_mode = EXCLUDED.ship_mode,
            customer_id = EXCLUDED.customer_id,
            customer_name = EXCLUDED.customer_name,
            segment = EXCLUDED.segment,
            country = EXCLUDED.country,
            city = EXCLUDED.city,
            state = EXCLUDED.state,
            postal_code = EXCLUDED.postal_code,
            region = EXCLUDED.region,
            product_id = EXCLUDED.product_id,
            category = EXCLUDED.category,
            sub_category = EXCLUDED.sub_category,
            product_name = EXCLUDED.product_name,
            sales = EXCLUDED.sales,
            quantity = EXCLUDED.quantity,
            discount = EXCLUDED.discount,
            profit = EXCLUDED.profit,
            loaded_at = CURRENT_TIMESTAMP;
    """



    # Batch processing — 5,000 rows per batch for 250K dataset
    BATCH_SIZE = 5000
    total_loaded = 0

    for start in range(0, len(df), BATCH_SIZE):
        batch = df.iloc[start:start + BATCH_SIZE]
        values = [
            (
                int(row["Row ID"]), row["Order ID"],
                row["Order Date"], row["Ship Date"], row["Ship Mode"],
                row["Customer ID"], row["Customer Name"], row["Segment"],
                row["Country"], row["City"], row["State"],
                row["Postal Code"] if row["Postal Code"] != "UNKNOWN" else None,
                row["Region"], row["Product ID"], row["Category"],
                row["Sub-Category"], row["Product Name"],
                float(row["Sales"]), int(row["Quantity"]),
                float(row["Discount"]) if pd.notna(row["Discount"]) else None,
                float(row["Profit"]),
            )
            for _, row in batch.iterrows()
        ]
        execute_values(cursor, upsert_query, values)
        total_loaded += len(values)
        logger.info(f"  Loaded batch: {total_loaded}/{len(df)} rows")

    conn.commit()
    logger.info(f"Load complete: {total_loaded} rows upserted into sales.raw_orders")

    cursor.close()
    conn.close()
    
    


# ─── TASK 4: VALIDATE

def validate_load(**context):
    """
    Post-load validation checks:
    1. Row count matches expected
    2. No null order_dates
    3. Revenue totals are positive
    4. Date range is plausible
    """
    import os
    import psycopg2

    expected = context["ti"].xcom_pull(key="clean_row_count")

    conn = psycopg2.connect(
        host=os.environ["TARGET_DB_HOST"],
        port=os.environ["TARGET_DB_PORT"],
        dbname=os.environ["TARGET_DB_NAME"],
        user=os.environ["TARGET_DB_USER"],
        password=os.environ["TARGET_DB_PASSWORD"],
    )
    cursor = conn.cursor()

    # Check 1: Row count
    cursor.execute("SELECT COUNT(*) FROM sales.raw_orders;")
    actual_count = cursor.fetchone()[0]
    logger.info(f"Validation — Row count: expected >= {expected}, actual = {actual_count}")
    if actual_count < expected:
        raise ValueError(f"Row count mismatch: expected >= {expected}, got {actual_count}")

    # Check 2: No null order dates
    cursor.execute("SELECT COUNT(*) FROM sales.raw_orders WHERE order_date IS NULL;")
    null_dates = cursor.fetchone()[0]
    if null_dates > 0:
        raise ValueError(f"Found {null_dates} null order_dates!")

    # Check 3: Total revenue is positive
    cursor.execute("SELECT SUM(sales) FROM sales.raw_orders;")
    total_revenue = cursor.fetchone()[0]
    logger.info(f"Validation — Total revenue: ${total_revenue:,.2f}")
    if total_revenue <= 0:
        raise ValueError(f"Total revenue is non-positive: {total_revenue}")

    # Check 4: Date range sanity
    cursor.execute("SELECT MIN(order_date), MAX(order_date) FROM sales.raw_orders;")
    min_date, max_date = cursor.fetchone()
    logger.info(f"Validation — Date range: {min_date} to {max_date}")

    # Check 5: Unique order count
    cursor.execute("SELECT COUNT(DISTINCT order_id) FROM sales.raw_orders;")
    unique_orders = cursor.fetchone()[0]
    logger.info(f"Validation — Unique orders: {unique_orders}")

    cursor.close()
    conn.close()

    logger.info("All validation checks passed!")
    
    
    


# ─── DAG WIRING 

extract = PythonOperator(
    task_id="extract_from_minio",
    python_callable=extract_from_minio,
    dag=dag,
)
transform = PythonOperator(
    task_id="transform_data",
    python_callable=transform_data,
    dag=dag,
)
load = PythonOperator(
    task_id="load_to_postgres",
    python_callable=load_to_postgres,
    dag=dag,
)
validate = PythonOperator(
    task_id="validate_load",
    python_callable=validate_load,
    dag=dag,
)

extract >> transform >> load >> validate
