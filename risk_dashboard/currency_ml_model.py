# ============================================
# MACHINE LEARNING MODELL FÜR WÄHRUNGSRISIKEN
# ============================================

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier, XGBRegressor

# ------------------------------------------------
# 1. DATEN LADEN
# ------------------------------------------------
df = pd.read_csv("currency_dataset.csv")

# ------------------------------------------------
# 2. FEATURES DEFINIEREN
# ------------------------------------------------
features = [
    "inflation_yoy",
    "inflation_3m_change",
    "policy_rate",
    "policy_rate_change_3m",
    "fx_volatility_30d",
    "reserves_usd",
    "reserves_change_3m",
    "debt_to_gdp",
    "current_account_balance_pct_gdp",
    "cb_independence_score",
    "corruption_index",
    "political_stability_index",
    "peg_type"
]

target_class = "crisis_12m"        # 0/1
target_reg = "stability_score"     # 0–100

# ------------------------------------------------
# 3. KATEGORISCHE UND NUMERISCHE FEATURES
# ------------------------------------------------
numeric_features = [
    "inflation_yoy",
    "inflation_3m_change",
    "policy_rate",
    "policy_rate_change_3m",
    "fx_volatility_30d",
    "reserves_usd",
    "reserves_change_3m",
    "debt_to_gdp",
    "current_account_balance_pct_gdp",
    "cb_independence_score",
    "corruption_index",
    "political_stability_index"
]

categorical_features = ["peg_type"]

# ------------------------------------------------
# 4. PREPROCESSING PIPELINE
# ------------------------------------------------
numeric_transformer = StandardScaler()
categorical_transformer = OneHotEncoder(handle_unknown="ignore")

preprocessor = ColumnTransformer(
    transformers=[
        ("num", numeric_transformer, numeric_features),
        ("cat", categorical_transformer, categorical_features)
    ]
)

# ------------------------------------------------
# 5. KLASSIFIKATIONSMODELL (Crisis_12m)
# ------------------------------------------------
clf_model = Pipeline(steps=[
    ("preprocess", preprocessor),
    ("model", XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8
    ))
])

X = df[features]
y_class = df[target_class]

X_train, X_test, y_train, y_test = train_test_split(X, y_class, test_size=0.2, random_state=42)

clf_model.fit(X_train, y_train)

print("Crisis_12m Accuracy:", clf_model.score(X_test, y_test))

# ------------------------------------------------
# 6. REGRESSIONSMODELL (Stability_Score)
# ------------------------------------------------
reg_model = Pipeline(steps=[
    ("preprocess", preprocessor),
    ("model", XGBRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8
    ))
])

y_reg = df[target_reg]

X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(X, y_reg, test_size=0.2, random_state=42)

reg_model.fit(X_train_r, y_train_r)

print("Stability_Score R2:", reg_model.score(X_test_r, y_test_r))

# ------------------------------------------------
# 7. FEATURE IMPORTANCE (optional)
# ------------------------------------------------
model = reg_model.named_steps["model"]
importances = model.feature_importances_

print("Feature Importances:", importances)

# ------------------------------------------------
# 8. VORHERSAGE FÜR NEUE WÄHRUNG
# ------------------------------------------------
new_currency = pd.DataFrame([{
    "inflation_yoy": 1.2,
    "inflation_3m_change": 0.1,
    "policy_rate": 5.5,
    "policy_rate_change_3m": 0.0,
    "fx_volatility_30d": 0.02,
    "reserves_usd": 18000000000,
    "reserves_change_3m": 0.05,
    "debt_to_gdp": 40,
    "current_account_balance_pct_gdp": 3.5,
    "cb_independence_score": 0.8,
    "corruption_index": 0.1,
    "political_stability_index": 0.9,
    "peg_type": "fixed"
}])

crisis_prob = clf_model.predict_proba(new_currency)[0][1]
stability_pred = reg_model.predict(new_currency)[0]

print("Krisenwahrscheinlichkeit:", crisis_prob)
print("Stabilitäts-Score:", stability_pred)
