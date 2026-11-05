
import pandas as pd
import numpy as np
import mysql.connector
import os

connection = mysql.connector.connect(
    host="127.0.0.1",
    port=3306,
    user="root",
    password="root",
    database="customer_segmentation"
)

query = """
SELECT
    c.customer_id,
    c.customer_code,
    MAX(o.order_date) AS last_order_date,
    COUNT(DISTINCT o.order_id) AS frequency,
    COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS monetary
FROM customers c
LEFT JOIN orders o
    ON c.customer_id = o.customer_id
    AND o.order_status = 'Completed'
LEFT JOIN order_items oi
    ON o.order_id = oi.order_id
GROUP BY c.customer_id, c.customer_code
"""

try:
    df = pd.read_sql(query, connection)
finally:
    connection.close()

# Clean data
df["last_order_date"] = pd.to_datetime(
    df["last_order_date"], errors="coerce"
)

df["frequency"] = df["frequency"].fillna(0).astype(int)
df["monetary"] = df["monetary"].fillna(0)

# NumPy calculation: average customer spending
average_spending = np.mean(df["monetary"].to_numpy())

print("\nOverall Average Customer Spending:",
      round(average_spending, 2))

# Calculate RFM recency
reference_date = pd.Timestamp.today().normalize()

df["recency"] = (
    reference_date - df["last_order_date"].dt.normalize()
).dt.days

df["recency"] = df["recency"].fillna(-1).astype(int)

# Assign rule-based segments
def assign_segment(row):
    if row["frequency"] == 0:
        return "New Customers"
    elif (
        row["recency"] >= 0
        and row["recency"] <= 90
        and row["monetary"] >= 1500
    ):
        return "High-Value Customers"
    elif row["recency"] >= 0 and row["recency"] <= 180:
        return "Regular Customers"
    else:
        return "Low-Activity Customers"


df["segment_name"] = df.apply(assign_segment, axis=1)

# Display RFM data
print("\nCustomer RFM Data:")
print(
    df[
        [
            "customer_id",
            "customer_code",
            "recency",
            "frequency",
            "monetary",
            "segment_name"
        ]
    ].to_string(index=False)
)

# Display segment summary
print("\nRule-Based Segment Summary:")
print(
    df.groupby("segment_name").agg(
        customers=("customer_code", "count"),
        average_recency=("recency", "mean"),
        average_frequency=("frequency", "mean"),
        average_spending=("monetary", "mean")
    ).round(2)
)

# Save results to CSV
base_dir = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(base_dir, "rfm_segments.csv")

df.to_csv(output_path, index=False)

print("\nRule-based results saved to:", output_path)
