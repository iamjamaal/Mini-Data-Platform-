
-- SCHEMA: sales
-- Maps to: sales_data.csv




CREATE SCHEMA IF NOT EXISTS sales;
-- RAW STAGING TABLE
-- Mirrors CSV structure exactly. This is the ETL landing zone.
CREATE TABLE IF NOT EXISTS sales.raw_orders (
    row_id          INTEGER PRIMARY KEY,
    order_id        VARCHAR(20) NOT NULL,
    order_date      DATE NOT NULL,
    ship_date       DATE NOT NULL,
    ship_mode       VARCHAR(20) NOT NULL,
    customer_id     VARCHAR(10) NOT NULL,
    customer_name   VARCHAR(100) NOT NULL,
    segment         VARCHAR(20) NOT NULL,
    country         VARCHAR(50) NOT NULL,
    city            VARCHAR(100) NOT NULL,
    state           VARCHAR(50) NOT NULL,
    postal_code     VARCHAR(10),              -- Nullable: ~1,878 missing
    region          VARCHAR(10) NOT NULL,
    product_id      VARCHAR(20) NOT NULL,
    category        VARCHAR(20) NOT NULL,
    sub_category    VARCHAR(20) NOT NULL,
    product_name    VARCHAR(255) NOT NULL,
    sales           NUMERIC(12,4) NOT NULL DEFAULT 0,
    quantity        INTEGER NOT NULL,
    discount        NUMERIC(4,2),             -- Nullable: ~1,833 missing
    profit          NUMERIC(12,4) NOT NULL,
    loaded_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- Index for common query patterns
CREATE INDEX IF NOT EXISTS idx_orders_date ON sales.raw_orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_region ON sales.raw_orders(region);
CREATE INDEX IF NOT EXISTS idx_orders_category ON sales.raw_orders(category);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON sales.raw_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_id ON sales.raw_orders(order_id);




-- ANALYTICAL VIEWS
-- These power the Metabase dashboards directly.

-- 1) Daily revenue & order trends (for time-series charts)
CREATE OR REPLACE VIEW sales.daily_summary AS
SELECT
    order_date,
    COUNT(DISTINCT order_id)           AS order_count,
    COUNT(*)                           AS line_item_count,
    SUM(quantity)                      AS total_units,
    ROUND(SUM(sales)::numeric, 2)     AS total_revenue,
    ROUND(SUM(profit)::numeric, 2)    AS total_profit,
    ROUND(AVG(discount)::numeric, 3)  AS avg_discount
FROM sales.raw_orders
GROUP BY order_date
ORDER BY order_date;


-- 2) Monthly summary (for trend dashboards)
CREATE OR REPLACE VIEW sales.monthly_summary AS
SELECT
    DATE_TRUNC('month', order_date)::date AS month,
    COUNT(DISTINCT order_id)              AS order_count,
    COUNT(DISTINCT customer_id)           AS unique_customers,
    SUM(quantity)                          AS total_units,
    ROUND(SUM(sales)::numeric, 2)         AS total_revenue,
    ROUND(SUM(profit)::numeric, 2)        AS total_profit,
    ROUND(AVG(discount)::numeric, 3)      AS avg_discount,
    ROUND(SUM(profit) / NULLIF(SUM(sales), 0) * 100, 1) AS profit_margin_pct
FROM sales.raw_orders
GROUP BY DATE_TRUNC('month', order_date)
ORDER BY month;


-- 3) Category & sub-category performance
CREATE OR REPLACE VIEW sales.category_performance AS
SELECT
    category,
    sub_category,
    COUNT(DISTINCT order_id)              AS total_orders,
    SUM(quantity)                          AS total_units_sold,
    ROUND(SUM(sales)::numeric, 2)         AS total_revenue,
    ROUND(SUM(profit)::numeric, 2)        AS total_profit,
    ROUND(SUM(profit) / NULLIF(SUM(sales), 0) * 100, 1) AS profit_margin_pct,
    ROUND(AVG(sales)::numeric, 2)         AS avg_sale_amount,
    ROUND(AVG(discount)::numeric, 3)      AS avg_discount
FROM sales.raw_orders
GROUP BY category, sub_category
ORDER BY total_revenue DESC;


-- 4) Regional breakdown
CREATE OR REPLACE VIEW sales.regional_performance AS
SELECT
    region,
    state,
    segment,
    COUNT(DISTINCT order_id)              AS order_count,
    COUNT(DISTINCT customer_id)           AS unique_customers,
    ROUND(SUM(sales)::numeric, 2)         AS total_revenue,
    ROUND(SUM(profit)::numeric, 2)        AS total_profit,
    ROUND(SUM(profit) / NULLIF(SUM(sales), 0) * 100, 1) AS profit_margin_pct
FROM sales.raw_orders
GROUP BY region, state, segment
ORDER BY total_revenue DESC;


-- 5) Customer segments
CREATE OR REPLACE VIEW sales.customer_segments AS
SELECT
    segment,
    COUNT(DISTINCT customer_id)           AS customer_count,
    COUNT(DISTINCT order_id)              AS order_count,
    ROUND(SUM(sales)::numeric, 2)         AS total_revenue,
    ROUND(SUM(profit)::numeric, 2)        AS total_profit,
    ROUND(AVG(sales)::numeric, 2)         AS avg_order_value,
    ROUND(AVG(discount)::numeric, 3)      AS avg_discount
FROM sales.raw_orders
GROUP BY segment
ORDER BY total_revenue DESC;


-- 6) Shipping analysis
CREATE OR REPLACE VIEW sales.shipping_analysis AS
SELECT
    ship_mode,
    COUNT(DISTINCT order_id)              AS order_count,
    ROUND(AVG(ship_date - order_date), 1) AS avg_ship_days,
    ROUND(SUM(sales)::numeric, 2)         AS total_revenue,
    ROUND(SUM(profit)::numeric, 2)        AS total_profit
FROM sales.raw_orders
GROUP BY ship_mode
ORDER BY order_count DESC;


-- 7) Top customers (for table/leaderboard)
CREATE OR REPLACE VIEW sales.top_customers AS
SELECT
    customer_id,
    customer_name,
    segment,
    COUNT(DISTINCT order_id)              AS order_count,
    SUM(quantity)                          AS total_items,
    ROUND(SUM(sales)::numeric, 2)         AS total_revenue,
    ROUND(SUM(profit)::numeric, 2)        AS total_profit,
    MIN(order_date)                        AS first_order,
    MAX(order_date)                        AS last_order
FROM sales.raw_orders
GROUP BY customer_id, customer_name, segment
ORDER BY total_revenue DESC;


-- 8) Discount impact analysis
CREATE OR REPLACE VIEW sales.discount_impact AS
SELECT
    CASE
        WHEN discount IS NULL THEN 'Missing'
        WHEN discount = 0 THEN 'No Discount'
        WHEN discount <= 0.2 THEN '1-20%'
        WHEN discount <= 0.4 THEN '21-40%'
        ELSE '41%+'
    END AS discount_band,
    COUNT(*)                              AS row_count,
    ROUND(SUM(sales)::numeric, 2)         AS total_revenue,
    ROUND(SUM(profit)::numeric, 2)        AS total_profit,
    ROUND(SUM(profit) / NULLIF(SUM(sales), 0) * 100, 1) AS profit_margin_pct
FROM sales.raw_orders
GROUP BY discount_band
ORDER BY discount_band;


-- 9) Data quality dashboard (meta-view for monitoring)
CREATE OR REPLACE VIEW sales.data_quality AS
SELECT
    COUNT(*)                                                    AS total_rows,
    COUNT(*) FILTER (WHERE postal_code IS NULL OR postal_code = '')  AS missing_postal_codes,
    COUNT(*) FILTER (WHERE discount IS NULL)                    AS missing_discounts,
    COUNT(*) FILTER (WHERE customer_name != TRIM(customer_name)) AS whitespace_names,
    COUNT(*) FILTER (WHERE sales = 0)                           AS zero_sales,
    MIN(order_date)                                             AS earliest_order,
    MAX(order_date)                                             AS latest_order,
    COUNT(DISTINCT order_id)                                    AS unique_orders,
    COUNT(DISTINCT customer_id)                                 AS unique_customers,
    COUNT(DISTINCT product_id)                                  AS unique_products
FROM sales.raw_orders;


-- Grant read access for Metabase
GRANT USAGE ON SCHEMA sales TO PUBLIC;
GRANT SELECT ON ALL TABLES IN SCHEMA sales TO PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA sales GRANT SELECT ON TABLES TO PUBLIC;