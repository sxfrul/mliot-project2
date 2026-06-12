
import numpy as np
import pandas as pd
import pickle
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.model_selection import train_test_split

print("=" * 55)
print("PHASE 2 — Preprocessing & Feature Engineering")
print("=" * 55)

# ── Step 1: Load ──────────────────────────────
df = pd.read_csv("datacenter_dataset.csv")
print(f"\n[1] Loaded: {df.shape[0]} rows, {df.shape[1]} columns")

missing = df.isnull().sum().sum()
if missing > 0:
    df.fillna(df.median(numeric_only=True), inplace=True)
    print(f"    Filled {missing} missing values with column medians")
else:
    print(f"    No missing values ✓")

# ── Step 2: Smoothing / Filtering ─────────────
print("\n[2] Smoothing — rolling average (window=5) + outlier clipping")

SENSOR_COLS = [
    "temperature_C", "humidity_pct", "power_kW",
    "airflow_cfm", "water_flow_L", "smoke_ppm"
]

for col in SENSOR_COLS:
    df[col + "_raw"] = df[col].copy()
    df[col] = df[col].rolling(window=5, min_periods=1).mean().round(3)

for col in SENSOR_COLS:
    mean, std = df[col].mean(), df[col].std()
    df[col] = df[col].clip(lower=mean - 3*std, upper=mean + 3*std).round(3)

print(f"    Applied to: {SENSOR_COLS}")

# ── Step 3: Normalization ─────────────────────
print("\n[3] Normalization — min-max scaling to [0, 1]")

scaler = MinMaxScaler()
df[SENSOR_COLS] = scaler.fit_transform(df[SENSOR_COLS])

with open("scaler.pkl", "wb") as f:
    pickle.dump(scaler, f)

print(f"    Scaled {len(SENSOR_COLS)} sensor columns")
print(f"    scaler.pkl saved ✓")

# ── Step 4: Feature Extraction ────────────────
print("\n[4] Feature extraction")

# 4a — Rate of change
for col in SENSOR_COLS:
    df[col + "_delta"] = df[col].diff().fillna(0).round(4)
print("    ✓ Rate-of-change features (col_delta)")

# 4b — Rolling std dev
for col in SENSOR_COLS:
    df[col + "_rollstd"] = (
        df[col].rolling(window=5, min_periods=1).std().fillna(0).round(4)
    )
print("    ✓ Rolling std dev features (col_rollstd)")

# 4c — Cyclical time encoding
df["hour_sin"] = np.sin(2 * np.pi * df["hour_of_day"] / 24).round(4)
df["hour_cos"] = np.cos(2 * np.pi * df["hour_of_day"] / 24).round(4)
print("    ✓ Time encoding: hour_sin, hour_cos")

# 4d — Rule-based threshold flags
df["flag_temp_high"]     = (df["temperature_C"] > 0.70).astype(int)
df["flag_smoke_warn"]    = (df["smoke_ppm"]      > 0.40).astype(int)
df["flag_smoke_crit"]    = (df["smoke_ppm"]      > 0.75).astype(int)
df["flag_humidity_low"]  = (df["humidity_pct"]   < 0.25).astype(int)
df["flag_humidity_high"] = (df["humidity_pct"]   > 0.80).astype(int)
df["flag_power_high"]    = (df["power_kW"]       > 0.75).astype(int)
df["flag_airflow_low"]   = (df["airflow_cfm"]    < 0.15).astype(int)
df["flag_night_motion"]  = (
    (df["motion_detected"] == 1) &
    ((df["hour_of_day"] < 6) | (df["hour_of_day"] >= 22))
).astype(int)
print("    ✓ Rule-based threshold flags (8 flags)")

# ── Step 5: Label encoding & split ───────────
print("\n[5] Label encoding & train/test split")

le = LabelEncoder()
df["label_encoded"] = le.fit_transform(df["cooling_mode"])

with open("label_encoder.pkl", "wb") as f:
    pickle.dump(le, f)

print(f"    Classes: {list(le.classes_)}")

# Feature columns — exclude labels, IDs, raw copies
DROP_COLS = (
    ["sample_id", "cooling_mode", "label_encoded",
     "PUE", "WUE", "alert_flag", "hour_of_day"]
    + [c + "_raw" for c in SENSOR_COLS]
)
FEATURE_COLS = [c for c in df.columns if c not in DROP_COLS]
TARGET_COL   = "label_encoded"

X = df[FEATURE_COLS].values
y = df[TARGET_COL].values

# PUE and WUE as regression targets — kept separate
y_pue = df["PUE"].values
y_wue = df["WUE"].values

# Single split — same indices used for classification AND regression
# This ensures train/test sets are identical across all models
X_train, X_test, y_train, y_test, pue_train, pue_test, wue_train, wue_test = (
    train_test_split(
        X, y, y_pue, y_wue,
        test_size=0.2, random_state=42, stratify=y
    )
)

# ── Save all outputs ──────────────────────────
df.to_csv("datacenter_processed.csv", index=False)

np.save("datacenter_X_train.npy",   X_train)
np.save("datacenter_X_test.npy",    X_test)
np.save("datacenter_y_train.npy",   y_train)
np.save("datacenter_y_test.npy",    y_test)
np.save("datacenter_pue_train.npy", pue_train)
np.save("datacenter_pue_test.npy",  pue_test)
np.save("datacenter_wue_train.npy", wue_train)
np.save("datacenter_wue_test.npy",  wue_test)

print(f"\n    Total features : {len(FEATURE_COLS)}")
print(f"    Training set   : {X_train.shape[0]} samples")
print(f"    Test set       : {X_test.shape[0]} samples")

print("\n[6] All files saved:")
print("    datacenter_processed.csv")
print("    datacenter_X_train/test.npy")
print("    datacenter_y_train/test.npy")
print("    datacenter_pue_train/test.npy  ← new (for regression)")
print("    datacenter_wue_train/test.npy  ← new (for regression)")
print("    scaler.pkl  |  label_encoder.pkl")

print("\n" + "=" * 55)
print("FEATURE SUMMARY")
print("=" * 55)
for i, col in enumerate(FEATURE_COLS):
    print(f"  {i+1:2d}. {col}")
