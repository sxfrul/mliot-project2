
import numpy as np
import pickle
import warnings
warnings.filterwarnings("ignore")

from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    accuracy_score, classification_report,
    mean_absolute_error, r2_score
)

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

print("=" * 55)
print("PHASE 3 — Model Training & Evaluation")
print("=" * 55)

# ── Load classification data ──────────────────
X_train = np.load("datacenter_X_train.npy")
X_test  = np.load("datacenter_X_test.npy")
y_train = np.load("datacenter_y_train.npy")
y_test  = np.load("datacenter_y_test.npy")

# ── Load regression targets ───────────────────
pue_train = np.load("datacenter_pue_train.npy")
pue_test  = np.load("datacenter_pue_test.npy")
wue_train = np.load("datacenter_wue_train.npy")
wue_test  = np.load("datacenter_wue_test.npy")

with open("label_encoder.pkl", "rb") as f:
    le = pickle.load(f)

CLASS_NAMES = list(le.classes_)
N_CLASSES   = len(CLASS_NAMES)
N_FEATURES  = X_train.shape[1]

print(f"\nTraining samples : {X_train.shape[0]}")
print(f"Test samples     : {X_test.shape[0]}")
print(f"Features         : {N_FEATURES}")
print(f"Classes          : {CLASS_NAMES}")
print(f"PUE range        : {pue_train.min():.3f} – {pue_train.max():.3f}")
print(f"WUE range        : {wue_train.min():.3f} – {wue_train.max():.3f}")


# ═════════════════════════════════════════════
# APPROACH 1 — Rule-based baseline
# ═════════════════════════════════════════════
# Flag column indices in the 31-feature vector:
#   23: flag_temp_high     24: flag_smoke_warn    25: flag_smoke_crit
#   26: flag_humidity_low  27: flag_humidity_high 28: flag_power_high
#   29: flag_airflow_low   30: flag_night_motion
#    6: water_leak (binary sensor, not a flag)
# ─────────────────────────────────────────────

print("\n" + "─" * 55)
print("APPROACH 1 — Rule-based baseline")
print("─" * 55)

IDX = {
    "temp_high":     23,
    "smoke_warn":    24,
    "smoke_crit":    25,
    "humidity_low":  26,
    "humidity_high": 27,
    "power_high":    28,
    "airflow_low":   29,
    "night_motion":  30,
    "water_leak":     6,
}

def rule_based_predict(X):
    preds = []
    for row in X:
        if row[IDX["smoke_crit"]] or (row[IDX["airflow_low"]] and row[IDX["temp_high"]]):
            preds.append(le.transform(["emergency"])[0])
        elif row[IDX["water_leak"]] > 0.5 or row[IDX["humidity_high"]]:
            preds.append(le.transform(["emergency"])[0])
        elif row[IDX["night_motion"]]:
            preds.append(le.transform(["security_alert"])[0])
        elif row[IDX["humidity_low"]]:
            preds.append(le.transform(["humidity_warn"])[0])
        elif row[IDX["power_high"]] or row[IDX["smoke_warn"]]:
            preds.append(le.transform(["evaporative"])[0])
        else:
            preds.append(le.transform(["air"])[0])
    return np.array(preds)

y_rule   = rule_based_predict(X_test)
rule_acc = accuracy_score(y_test, y_rule)
print(f"\nRule-based accuracy : {rule_acc * 100:.1f}%")
print(classification_report(y_test, y_rule, target_names=CLASS_NAMES))


# ═════════════════════════════════════════════
# APPROACH 2 — Random Forest Classifier
# ═════════════════════════════════════════════

print("─" * 55)
print("APPROACH 2 — Random Forest Classifier")
print("─" * 55)

rf = RandomForestClassifier(
    n_estimators=100, max_depth=12,
    min_samples_split=4, random_state=42, n_jobs=-1
)
rf.fit(X_train, y_train)
y_rf   = rf.predict(X_test)
rf_acc = accuracy_score(y_test, y_rf)

print(f"\nRandom Forest accuracy : {rf_acc * 100:.1f}%")
print(classification_report(y_test, y_rf, target_names=CLASS_NAMES))

feature_names = (
    ["temperature_C","humidity_pct","power_kW","airflow_cfm","water_flow_L","smoke_ppm"]
    + ["water_leak","motion_detected","door_open"]
    + [c+"_delta"   for c in ["temperature_C","humidity_pct","power_kW","airflow_cfm","water_flow_L","smoke_ppm"]]
    + [c+"_rollstd" for c in ["temperature_C","humidity_pct","power_kW","airflow_cfm","water_flow_L","smoke_ppm"]]
    + ["hour_sin","hour_cos"]
    + ["flag_temp_high","flag_smoke_warn","flag_smoke_crit",
       "flag_humidity_low","flag_humidity_high","flag_power_high",
       "flag_airflow_low","flag_night_motion"]
)

top10 = np.argsort(rf.feature_importances_)[::-1][:10]
print("Top 10 feature importances:")
for i in top10:
    name = feature_names[i] if i < len(feature_names) else f"feature_{i}"
    print(f"  {name:35s}  {rf.feature_importances_[i]:.4f}")

with open("rf_model.pkl", "wb") as f:
    pickle.dump(rf, f)
print("\nrf_model.pkl saved ✓")


# ═════════════════════════════════════════════
# APPROACH 3 — Keras Neural Network
# ═════════════════════════════════════════════

print("\n" + "─" * 55)
print("APPROACH 3 — Keras Neural Network")
print("─" * 55)

def build_model(n_features, n_classes):
    """
    Small Dense network — intentionally compact for TFLite.
    31 → 64 → 32 → 16 → 5 (softmax)
    BatchNorm stabilizes training.
    Dropout(0.2) prevents overfitting on 1350 samples.
    """
    model = keras.Sequential([
        layers.Input(shape=(n_features,)),
        layers.Dense(64, activation="relu"),
        layers.BatchNormalization(),
        layers.Dropout(0.2),
        layers.Dense(32, activation="relu"),
        layers.BatchNormalization(),
        layers.Dropout(0.2),
        layers.Dense(16, activation="relu"),
        layers.Dense(n_classes, activation="softmax"),
    ], name="datacenter_classifier")
    return model

model = build_model(N_FEATURES, N_CLASSES)
model.summary()

model.compile(
    optimizer=keras.optimizers.Adam(learning_rate=0.001),
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"]
)

early_stop = keras.callbacks.EarlyStopping(
    monitor="val_loss", patience=10, restore_best_weights=True
)
reduce_lr = keras.callbacks.ReduceLROnPlateau(
    monitor="val_loss", factor=0.5, patience=5, min_lr=1e-5, verbose=0
)

print("\nTraining...")
history = model.fit(
    X_train, y_train,
    validation_split=0.15,
    epochs=80,
    batch_size=32,
    callbacks=[early_stop, reduce_lr],
    verbose=1
)

y_nn   = np.argmax(model.predict(X_test, verbose=0), axis=1)
nn_acc = accuracy_score(y_test, y_nn)

print(f"\nNeural Network accuracy : {nn_acc * 100:.1f}%")
print(classification_report(y_test, y_nn, target_names=CLASS_NAMES))

model.save("dc_model.keras")
np.save("training_history.npy", history.history)
print("dc_model.keras saved ✓")
print("training_history.npy saved ✓")


# ═════════════════════════════════════════════
# APPROACH 4 — PUE & WUE Regression
# Predicts actual efficiency values, not just mode
# This is what satisfies "balance PUE and WUE"
# ═════════════════════════════════════════════

print("\n" + "─" * 55)
print("APPROACH 4 — PUE & WUE Regression")
print("─" * 55)
print("Predicts actual PUE and WUE values from sensor readings")
print("Lower PUE = better power efficiency  (target: close to 1.0)")
print("Lower WUE = better water efficiency  (target: close to 0.0)")

# ── PUE Regressor ─────────────────────────────
rf_pue = RandomForestRegressor(
    n_estimators=100, max_depth=12, random_state=42, n_jobs=-1
)
rf_pue.fit(X_train, pue_train)
pue_pred = rf_pue.predict(X_test)

pue_mae = mean_absolute_error(pue_test, pue_pred)
pue_r2  = r2_score(pue_test, pue_pred)
print(f"\nPUE Regressor:")
print(f"  MAE : {pue_mae:.4f}  (average prediction error in PUE units)")
print(f"  R²  : {pue_r2:.4f}  (1.0 = perfect, above 0.85 is good)")

# ── WUE Regressor ─────────────────────────────
rf_wue = RandomForestRegressor(
    n_estimators=100, max_depth=12, random_state=42, n_jobs=-1
)
rf_wue.fit(X_train, wue_train)
wue_pred = rf_wue.predict(X_test)

wue_mae = mean_absolute_error(wue_test, wue_pred)
wue_r2  = r2_score(wue_test, wue_pred)
print(f"\nWUE Regressor:")
print(f"  MAE : {wue_mae:.4f}  (average prediction error in WUE units)")
print(f"  R²  : {wue_r2:.4f}  (1.0 = perfect, above 0.85 is good)")

# ── Save regressors ───────────────────────────
with open("rf_pue_model.pkl", "wb") as f: pickle.dump(rf_pue, f)
with open("rf_wue_model.pkl", "wb") as f: pickle.dump(rf_wue, f)
print("\nrf_pue_model.pkl saved ✓")
print("rf_wue_model.pkl saved ✓")

# ── Balancing decision example ────────────────
print("\n--- PUE vs WUE Balancing Decision Examples ---")
print(f"{'Sample':<8} {'Actual Mode':<16} {'Pred PUE':>9} {'Pred WUE':>9}  {'Recommendation'}")
print("─" * 65)

with open("label_encoder.pkl", "rb") as f:
    le_check = pickle.load(f)

for i in range(0, min(10, len(X_test))):
    sample      = X_test[i:i+1]
    pue_val     = rf_pue.predict(sample)[0]
    wue_val     = rf_wue.predict(sample)[0]
    actual_mode = le_check.inverse_transform([y_test[i]])[0]

    # Balancing logic:
    # If predicted PUE is high (power inefficient) AND WUE is still low
    # → switch to evaporative to improve power efficiency
    # If predicted WUE is very high (water wasteful)
    # → switch to air to conserve water
    if pue_val > 1.6 and wue_val < 2.0:
        recommendation = "switch to evaporative → save power"
    elif wue_val > 3.5:
        recommendation = "switch to air        → save water"
    elif pue_val > 2.0:
        recommendation = "emergency cooling    → critical"
    else:
        recommendation = "maintain current     → balanced"

    print(f"  {i:<6} {actual_mode:<16} {pue_val:>9.3f} {wue_val:>9.3f}  {recommendation}")


# ═════════════════════════════════════════════
# PLOTS
# ═════════════════════════════════════════════

print("\n" + "─" * 55)
print("Generating plots...")
print("─" * 55)

import matplotlib.pyplot as plt
from sklearn.metrics import ConfusionMatrixDisplay, confusion_matrix

# Plot 1 — Confusion matrix (Neural Network)
cm   = confusion_matrix(y_test, y_nn)
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=CLASS_NAMES)
fig, ax = plt.subplots(figsize=(8, 6))
disp.plot(ax=ax, cmap="Blues", colorbar=False)
plt.title("Neural Network — Confusion Matrix")
plt.tight_layout()
plt.savefig("confusion_matrix.png", dpi=150)
plt.close()
print("  confusion_matrix.png saved ✓")

# Plot 2 — Training loss and accuracy curves
history_data = np.load("training_history.npy", allow_pickle=True).item()
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

ax1.plot(history_data["loss"],     label="Train loss")
ax1.plot(history_data["val_loss"], label="Val loss")
ax1.set_title("Loss curve")
ax1.set_xlabel("Epoch")
ax1.legend()

ax2.plot(history_data["accuracy"],     label="Train acc")
ax2.plot(history_data["val_accuracy"], label="Val acc")
ax2.set_title("Accuracy curve")
ax2.set_xlabel("Epoch")
ax2.legend()

plt.tight_layout()
plt.savefig("training_curves.png", dpi=150)
plt.close()
print("  training_curves.png saved ✓")

# Plot 3 — Model comparison bar chart
approaches = ["Rule-based\n(baseline)", "Random\nForest", "Neural\nNetwork"]
accuracies = [rule_acc * 100, rf_acc * 100, nn_acc * 100]
colors     = ["#d9534f", "#5bc0de", "#5cb85c"]

plt.figure(figsize=(7, 4))
bars = plt.bar(approaches, accuracies, color=colors, width=0.5)
plt.ylim(0, 100)
plt.ylabel("Accuracy (%)")
plt.title("Model Comparison — Rule-based vs ML")
for bar, acc in zip(bars, accuracies):
    plt.text(bar.get_x() + bar.get_width()/2,
             bar.get_height() + 1, f"{acc:.1f}%", ha="center", fontsize=11)
plt.tight_layout()
plt.savefig("model_comparison.png", dpi=150)
plt.close()
print("  model_comparison.png saved ✓")

# Plot 4 — PUE vs WUE predicted scatter
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

ax1.scatter(pue_test, pue_pred, alpha=0.4, color="#5bc0de", s=20)
ax1.plot([pue_test.min(), pue_test.max()],
         [pue_test.min(), pue_test.max()], 'r--', linewidth=1)
ax1.set_xlabel("Actual PUE")
ax1.set_ylabel("Predicted PUE")
ax1.set_title(f"PUE Prediction  (R²={pue_r2:.3f}  MAE={pue_mae:.4f})")

ax2.scatter(wue_test, wue_pred, alpha=0.4, color="#f0ad4e", s=20)
ax2.plot([wue_test.min(), wue_test.max()],
         [wue_test.min(), wue_test.max()], 'r--', linewidth=1)
ax2.set_xlabel("Actual WUE")
ax2.set_ylabel("Predicted WUE")
ax2.set_title(f"WUE Prediction  (R²={wue_r2:.3f}  MAE={wue_mae:.4f})")

plt.tight_layout()
plt.savefig("pue_wue_regression.png", dpi=150)
plt.close()
print("  pue_wue_regression.png saved ✓")


# ═════════════════════════════════════════════
# FINAL SUMMARY
# ═════════════════════════════════════════════

print("\n" + "=" * 55)
print("COMPLETE MODEL SUMMARY")
print("=" * 55)
print(f"\n  CLASSIFICATION (cooling mode decision):")
print(f"  {'Approach':<25} {'Accuracy':>10}")
print(f"  {'-'*25} {'-'*10}")
print(f"  {'Rule-based (baseline)':<25} {rule_acc*100:>9.1f}%")
print(f"  {'Random Forest':<25} {rf_acc*100:>9.1f}%")
print(f"  {'Neural Network':<25} {nn_acc*100:>9.1f}%")

print(f"\n  REGRESSION (PUE / WUE prediction):")
print(f"  {'Model':<25} {'MAE':>8}  {'R²':>8}")
print(f"  {'-'*25} {'-'*8}  {'-'*8}")
print(f"  {'PUE Regressor':<25} {pue_mae:>8.4f}  {pue_r2:>8.4f}")
print(f"  {'WUE Regressor':<25} {wue_mae:>8.4f}  {wue_r2:>8.4f}")

print(f"\n  Files produced:")
print(f"    rf_model.pkl        — Random Forest classifier")
print(f"    dc_model.keras      — Keras classifier → Phase 4")
print(f"    rf_pue_model.pkl    — PUE regressor")
print(f"    rf_wue_model.pkl    — WUE regressor")
print(f"    training_history.npy")
print(f"    confusion_matrix.png")
print(f"    training_curves.png")
print(f"    model_comparison.png")
print(f"    pue_wue_regression.png")
print("=" * 55)
print("\nNext step: run phase4a_convert.py")
