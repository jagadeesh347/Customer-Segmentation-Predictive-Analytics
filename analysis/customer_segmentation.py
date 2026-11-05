
import os
import sys
import json
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from app.db import get_connection

# Fetch customer purchase data
connection = get_connection()

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

df["frequency"] = pd.to_numeric(
    df["frequency"], errors="coerce"
).fillna(0)

df["monetary"] = pd.to_numeric(
    df["monetary"], errors="coerce"
).fillna(0)

# Calculate recency
reference_date = pd.Timestamp.today().normalize()

df["recency"] = (
    reference_date - df["last_order_date"].dt.normalize()
).dt.days

# Identify customers without completed purchases
new_customers = (
    (df["frequency"] == 0)
    & (df["monetary"] == 0)
)

df["segment"] = -1
df["segment_name"] = "Not Yet Segmented"

active_df = df[~new_customers].copy()

features = ["recency", "frequency", "monetary"]
segment_names = {}
actual_clusters = 0
score = None

# Perform K-means segmentation
if len(active_df) >= 3:
    active_df["recency"] = active_df["recency"].fillna(
        active_df["recency"].max() + 30
    )

    # Scale RFM features
    scaler = StandardScaler()
    X = scaler.fit_transform(active_df[features])

    # Use up to three clusters
    unique_rows = len(active_df[features].drop_duplicates())
    n_clusters = min(3, unique_rows)

    if 2 <= n_clusters < len(active_df):
        model = KMeans(
            n_clusters=n_clusters,
            random_state=42,
            n_init=10
        )

        active_df["segment"] = model.fit_predict(X)
        actual_clusters = n_clusters

        # Evaluate clustering quality
        score = silhouette_score(
            X, active_df["segment"]
        )

        print("\nClustering Evaluation")
        print("Number of clusters:", actual_clusters)
        print("Silhouette Score:", round(score, 3))
        print("Higher scores generally indicate better-separated clusters.")

        # Rank clusters by scaled RFM characteristics
        centers = model.cluster_centers_
        scores = -centers[:, 0] + centers[:, 1] + centers[:, 2]

        ranked_segments = sorted(
            range(n_clusters),
            key=lambda s: scores[s],
            reverse=True
        )

        labels = [
            "High-Value Customers",
            "Regular Customers",
            "Low-Activity Customers"
        ]

        segment_names = {
            segment_id: labels[rank]
            for rank, segment_id in enumerate(ranked_segments)
        }

        active_df["segment_name"] = active_df["segment"].map(
            segment_names
        )

        df.loc[active_df.index, "segment"] = active_df["segment"]
        df.loc[active_df.index, "segment_name"] = (
            active_df["segment_name"]
        )

    else:
        active_df["segment_name"] = "Regular Customers"
        df.loc[active_df.index, "segment_name"] = (
            "Regular Customers"
        )

elif len(active_df) > 0:
    active_df["segment_name"] = "Regular Customers"
    df.loc[active_df.index, "segment_name"] = (
        "Regular Customers"
    )

# Display customer results
print("\nCustomer Segmentation Results:")
print(
    df[
        [
            "customer_code",
            "recency",
            "frequency",
            "monetary",
            "segment",
            "segment_name"
        ]
    ].to_string(index=False)
)

# Display segment summary
print("\nSegment Summary:")
print(
    df.groupby("segment_name").agg(
        customers=("customer_code", "count"),
        average_recency=("recency", "mean"),
        average_frequency=("frequency", "mean"),
        average_spending=("monetary", "mean")
    ).round(2)
)

# Save results to database
connection = get_connection()
cursor = connection.cursor()

try:
    cursor.execute(
        """
        INSERT INTO segment_runs (method, parameters)
        VALUES (%s, %s)
        """,
        (
            "KMeans",
            json.dumps({
                "clusters": actual_clusters,
                "features": features,
                "scaling": "StandardScaler",
                "silhouette_score": score,
                "random_state": 42
            })
        )
    )

    run_id = cursor.lastrowid

    for _, row in df.iterrows():
        cursor.execute(
            """
            INSERT INTO customer_segments
                (run_id, customer_id, segment_label)
            VALUES (%s, %s, %s)
            """,
            (
                run_id,
                int(row["customer_id"]),
                row["segment_name"]
            )
        )

    connection.commit()

except Exception:
    connection.rollback()
    raise

finally:
    cursor.close()
    connection.close()

# Export results
output_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "customer_segments.csv"
)

df.to_csv(output_path, index=False)

print("\nSegmentation results saved successfully!")
print("Run ID:", run_id)
print("CSV saved at:", output_path)
