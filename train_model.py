import pandas as pd
import numpy as np
import joblib
import os

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier
from imblearn.over_sampling import SMOTE

# ---------------------------------------------------
# LOAD DATASET
# ---------------------------------------------------

data = pd.read_csv("dataset/tax_fraud_dataset.csv")

print("Dataset Loaded Successfully")
print(data.head())

# ---------------------------------------------------
# FEATURES AND TARGET
# ---------------------------------------------------

X = data.drop("Fraud", axis=1)
y = data["Fraud"]

# ---------------------------------------------------
# TRAIN TEST SPLIT
# ---------------------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

# ---------------------------------------------------
# FEATURE SCALING
# ---------------------------------------------------

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)
# ---------------------------------------------------
# APPLY SMOTE
# ---------------------------------------------------

smote = SMOTE(random_state=42)

X_train_smote, y_train_smote = smote.fit_resample(
    X_train_scaled,
    y_train
)

print("\nBefore SMOTE:")
print(y_train.value_counts())

print("\nAfter SMOTE:")
print(pd.Series(y_train_smote).value_counts())

# ---------------------------------------------------
# CREATE MODELS
# ---------------------------------------------------

lr_model = LogisticRegression(max_iter=1000)

rf_model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

xgb_model = XGBClassifier(
    eval_metric='logloss',
    random_state=42
)

# ---------------------------------------------------
# TRAIN MODELS
# ---------------------------------------------------

print("\nTraining Logistic Regression...")
lr_model.fit(X_train_smote, y_train_smote)

print("Training Random Forest...")
rf_model.fit(X_train_smote, y_train_smote)

print("Training XGBoost...")
xgb_model.fit(X_train_smote, y_train_smote)


# ---------------------------------------------------
# PREDICTIONS
# ---------------------------------------------------

lr_pred = lr_model.predict(X_test_scaled)
rf_pred = rf_model.predict(X_test_scaled)
xgb_pred = xgb_model.predict(X_test_scaled)

# ---------------------------------------------------
# ACCURACY
# ---------------------------------------------------

lr_acc = accuracy_score(y_test, lr_pred)
rf_acc = accuracy_score(y_test, rf_pred)
xgb_acc = accuracy_score(y_test, xgb_pred)

print("\nMODEL ACCURACIES")
print("----------------------")

print(f"Logistic Regression: {lr_acc:.4f}")
print(f"Random Forest: {rf_acc:.4f}")
print(f"XGBoost: {xgb_acc:.4f}")

# ---------------------------------------------------
# SAVE MODELS
# ---------------------------------------------------

os.makedirs("model_artifacts", exist_ok=True)

joblib.dump(lr_model,
            "model_artifacts/logistic_regression.pkl")

joblib.dump(rf_model,
            "model_artifacts/random_forest.pkl")

joblib.dump(xgb_model,
            "model_artifacts/xgboost.pkl")

joblib.dump(scaler,
            "model_artifacts/scaler.pkl")

print("\nModels Saved Successfully")