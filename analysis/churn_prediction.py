
import os
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_PATH = os.path.join(BASE_DIR, "customer_features.csv")
MODEL_PATH = os.path.join(BASE_DIR, "churn_model.joblib")
SCALER_PATH = os.path.join(BASE_DIR, "churn_scaler.joblib")

# Load existing dataset
df = pd.read_csv(DATA_PATH)

features = ["recency", "frequency", "monetary"]
X = df[features]
y = df["churn"].astype(int)

print("Dataset size:", len(df))
print("\nChurn counts:")
print(y.value_counts())

if len(df) < 20 or y.nunique() != 2 or y.value_counts().min() < 2:
    print("\nWARNING: Dataset is too small for reliable evaluation.")
    print("Using all available records for demonstration training.")

model = LogisticRegression(
    max_iter=1000,
    random_state=42
)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

model.fit(X_scaled, y)

# Save model and scaler for Flask
joblib.dump(model, MODEL_PATH)
joblib.dump(scaler, SCALER_PATH)

print("\nModel and scaler saved successfully.")
print("Model path:", MODEL_PATH)
print("Scaler path:", SCALER_PATH)

# Show training predictions (not independent test results)
predictions = model.predict(X_scaled)

print("\nTraining accuracy:",
      round(accuracy_score(y, predictions) * 100, 2), "%")

print("\nConfusion matrix:")
print(confusion_matrix(y, predictions))

print("\nClassification report:")
print(classification_report(y, predictions, zero_division=0))

# Test the example used in Flask
sample = pd.DataFrame([{
    "recency": 30,
    "frequency": 5,
    "monetary": 5000
}])

sample_scaled = scaler.transform(sample)
probability = model.predict_proba(sample_scaled)[0][1]

print("\nExample customer: Recency=30, Frequency=5, Spending=5000")
print("Predicted churn probability:", round(probability * 100, 2), "%")
print("Note: This is a demonstration prediction, not a reliable business estimate.")
print("\n--- Training Customer Predictions ---")

results = df[["customer_code", "recency", "frequency", "monetary", "churn"]].copy()

results["probability"] = (
    model.predict_proba(scaler.transform(X))[:, 1] * 100
).round(2)

results["predicted_status"] = results["probability"].apply(
    lambda p: "Potential Churn" if p >= 30 else "Active"
)

print(results.to_string(index=False))