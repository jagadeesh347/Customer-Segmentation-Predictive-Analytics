
import os
import joblib
import pandas as pd

from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CSV_PATH = os.path.join(BASE_DIR, "customer_features.csv")
MODEL_PATH = os.path.join(BASE_DIR, "churn_model.joblib")
SCALER_PATH = os.path.join(BASE_DIR, "churn_scaler.joblib")

df = pd.read_csv(CSV_PATH)

features = ["recency", "frequency", "monetary"]

df = df.dropna(subset=features + ["churn"])

X = df[features]
y = df["churn"].astype(int)

print("CUSTOMER CHURN MODEL EVALUATION")
print("-" * 40)
print("Dataset rows:", len(df))
print("Churn label counts:")
print(y.value_counts().sort_index().to_string())

if len(df) < 20 or y.nunique() < 2 or y.value_counts().min() < 2:
    print("\nWARNING: Dataset is too small for reliable evaluation.")
    print("Metrics may be unstable, especially if labels are demo-generated.")

# Cross-validation with scaling performed separately inside each fold.
model_pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("model", LogisticRegression(random_state=42, max_iter=1000))
])

if y.nunique() >= 2 and y.value_counts().min() >= 3:
    cv = StratifiedKFold(
        n_splits=3,
        shuffle=True,
        random_state=42
    )

    scores = cross_val_score(
        model_pipeline,
        X,
        y,
        cv=cv,
        scoring="accuracy"
    )

    print("\n3-Fold Cross-Validation Accuracy:")
    print("Scores:", scores.round(3))
    print("Mean Accuracy:", round(scores.mean(), 3))
else:
    print("\nCross-validation skipped: insufficient examples per class.")

# Train final model on all available labeled data.
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

model = LogisticRegression(random_state=42, max_iter=1000)
model.fit(X_scaled, y)

predictions = model.predict(X_scaled)

print("\nTRAINING-SET METRICS (not independent test results)")
print("Accuracy: ", round(accuracy_score(y, predictions), 3))
print("Precision:", round(precision_score(y, predictions, zero_division=0), 3))
print("Recall:   ", round(recall_score(y, predictions, zero_division=0), 3))
print("F1-score: ", round(f1_score(y, predictions, zero_division=0), 3))

print("\nConfusion matrix (labels 0, 1):")
print(confusion_matrix(y, predictions, labels=[0, 1]))

print("\nDetailed report:")
print(classification_report(y, predictions, labels=[0, 1], zero_division=0))

# Explore how different classification thresholds affect churn detection.
print("\nTHRESHOLD COMPARISON")

probabilities = model.predict_proba(X_scaled)[:, 1]

for threshold in [0.3, 0.4, 0.5, 0.6]:
    threshold_predictions = (
        probabilities >= threshold
    ).astype(int)

    threshold_recall = recall_score(
        y, threshold_predictions, zero_division=0
    )

    false_alarms = int(
        ((threshold_predictions == 1) & (y == 0)).sum()
    )

    detected_churn = int(
        ((threshold_predictions == 1) & (y == 1)).sum()
    )

    print(
        f"Threshold: {threshold:.1f}"
        f" | Churn detected: {detected_churn}/{int((y == 1).sum())}"
        f" | Recall: {threshold_recall:.3f}"
        f" | False alarms: {false_alarms}"
    )

# Keep separate model and scaler files for Flask compatibility.
joblib.dump(model, MODEL_PATH)
joblib.dump(scaler, SCALER_PATH)

print("\nModel saved:", MODEL_PATH)
print("Scaler saved:", SCALER_PATH)
