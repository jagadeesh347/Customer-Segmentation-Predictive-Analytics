
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("customer_segments.csv")

for segment in sorted(df["segment"].unique()):
    group = df[df["segment"] == segment]

    plt.scatter(
        group["frequency"],
        group["monetary"],
        label="Segment " + str(segment),
        s=100
    )

plt.xlabel("Purchase Frequency")
plt.ylabel("Total Spending")
plt.title("Customer Segmentation")
plt.legend()
plt.grid(True)

plt.show()
