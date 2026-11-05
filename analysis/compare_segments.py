
import os
import pandas as pd
import matplotlib.pyplot as plt

folder = os.path.dirname(os.path.abspath(__file__))

rfm = pd.read_csv(os.path.join(folder, "rfm_segments.csv"))
km = pd.read_csv(os.path.join(folder, "customer_segments.csv"))

a = rfm[["customer_code", "segment_name"]].rename(
    columns={"segment_name": "Rule-Based"}
)

b = km[["customer_code", "segment_name"]].rename(
    columns={"segment_name": "K-Means"}
)

result = pd.merge(a, b, on="customer_code", how="outer")

print("\nRule-Based vs K-Means Comparison:")
print(result.to_string(index=False))

print("\nRule-Based Segment Counts:")
print(result["Rule-Based"].value_counts())

print("\nK-Means Segment Counts:")
print(result["K-Means"].value_counts())

result.to_csv(os.path.join(folder, "segment_comparison.csv"), index=False)

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

result["Rule-Based"].value_counts().plot(
    kind="bar", ax=axes[0], title="Rule-Based RFM"
)
result["K-Means"].value_counts().plot(
    kind="bar", ax=axes[1], title="K-Means"
)

axes[0].set_ylabel("Number of Customers")
axes[1].set_ylabel("Number of Customers")

plt.tight_layout()
plt.savefig(os.path.join(folder, "segment_comparison.png"))
plt.show()

print("\nComparison CSV and chart saved successfully!")
