import numpy as np
import pandas as pd

np.random.seed(42)

def noisy(value, std):
    return value + np.random.normal(0, std)


# ─────────────────────────────────────────────
# SCENARIO 1 — Normal operation
# ─────────────────────────────────────────────
def gen_normal(n=500):
    records = []
    for _ in range(n):
        temp       = noisy(21, 1.5)
        humidity   = noisy(50, 4)
        power      = noisy(60, 6)
        airflow    = noisy(800, 60)
        water_flow = noisy(10, 2)
        smoke      = noisy(50, 10)        # MQ-2 clean air baseline ~50 ppm
        hour       = np.random.randint(0, 24)
        pue        = round(1.4 + np.random.uniform(0, 0.2), 3)
        wue        = round(0.6 + np.random.uniform(0, 0.4), 3)
        records.append({
            "temperature_C":   round(np.clip(temp,       15,  28),  2),
            "humidity_pct":    round(np.clip(humidity,   40,  65),  2),
            "power_kW":        round(np.clip(power,      45,  80),  2),
            "airflow_cfm":     round(np.clip(airflow,   600,1000),  1),
            "water_flow_L":    round(np.clip(water_flow,  5,  20),  2),
            "smoke_ppm":       round(np.clip(smoke,       0, 200),  1),
            "water_leak":      0,
            "motion_detected": int(np.random.random() < 0.05),
            "door_open":       int(np.random.random() < 0.05),
            "hour_of_day":     hour,
            "cooling_mode":    "air",
            "PUE":             pue,
            "WUE":             wue,
            "alert_flag":      0,
        })
    return records


# ─────────────────────────────────────────────
# SCENARIO 2 — High server load
# ─────────────────────────────────────────────
def gen_high_load(n=400):
    records = []
    for _ in range(n):
        temp       = noisy(31, 2.5)
        humidity   = noisy(48, 5)
        power      = noisy(95, 8)
        airflow    = noisy(1200, 80)
        water_flow = noisy(55, 8)
        smoke      = noisy(80, 15)        # slightly elevated from heat
        hour       = np.random.randint(0, 24)
        pue        = round(1.2 + np.random.uniform(0, 0.15), 3)
        wue        = round(1.8 + np.random.uniform(0, 1.2),  3)
        records.append({
            "temperature_C":   round(np.clip(temp,       26,  38),  2),
            "humidity_pct":    round(np.clip(humidity,   38,  60),  2),
            "power_kW":        round(np.clip(power,      80, 120),  2),
            "airflow_cfm":     round(np.clip(airflow,  1000,1400),  1),
            "water_flow_L":    round(np.clip(water_flow, 40,  80),  2),
            "smoke_ppm":       round(np.clip(smoke,       0, 200),  1),
            "water_leak":      0,
            "motion_detected": int(np.random.random() < 0.05),
            "door_open":       int(np.random.random() < 0.05),
            "hour_of_day":     hour,
            "cooling_mode":    "evaporative",
            "PUE":             pue,
            "WUE":             wue,
            "alert_flag":      1,
        })
    return records


# ─────────────────────────────────────────────
# SCENARIO 3 — Cooling failure / fire risk
# ─────────────────────────────────────────────
def gen_cooling_failure(n=150):
    records = []
    for _ in range(n):
        temp       = noisy(46, 4)
        humidity   = noisy(35, 6)
        power      = noisy(100, 10)
        airflow    = noisy(150, 50)
        water_flow = noisy(5, 3)
        smoke      = noisy(420, 60)       # MQ-2 danger zone — >300 ppm
        hour       = np.random.randint(0, 24)
        pue        = round(2.2 + np.random.uniform(0, 0.5), 3)
        wue        = round(0.2 + np.random.uniform(0, 0.3), 3)
        records.append({
            "temperature_C":   round(np.clip(temp,       36,  60),  2),
            "humidity_pct":    round(np.clip(humidity,   20,  50),  2),
            "power_kW":        round(np.clip(power,      85, 125),  2),
            "airflow_cfm":     round(np.clip(airflow,     0, 300),  1),
            "water_flow_L":    round(np.clip(water_flow,  0,  15),  2),
            "smoke_ppm":       round(np.clip(smoke,     200, 700),  1),
            "water_leak":      0,
            "motion_detected": int(np.random.random() < 0.05),
            "door_open":       int(np.random.random() < 0.05),
            "hour_of_day":     hour,
            "cooling_mode":    "emergency",
            "PUE":             pue,
            "WUE":             wue,
            "alert_flag":      2,
        })
    return records


# ─────────────────────────────────────────────
# SCENARIO 4 — Flooding
# ─────────────────────────────────────────────
def gen_flooding(n=100):
    records = []
    for _ in range(n):
        temp       = noisy(23, 2)
        humidity   = noisy(82, 6)
        power      = noisy(65, 8)
        airflow    = noisy(750, 80)
        water_flow = noisy(200, 30)
        smoke      = noisy(55, 10)        # water, not fire — smoke normal
        hour       = np.random.randint(0, 24)
        pue        = round(1.6 + np.random.uniform(0, 0.4), 3)
        wue        = round(5.0 + np.random.uniform(0, 2.0), 3)
        records.append({
            "temperature_C":   round(np.clip(temp,       18,  30),  2),
            "humidity_pct":    round(np.clip(humidity,   70,  98),  2),
            "power_kW":        round(np.clip(power,      50,  85),  2),
            "airflow_cfm":     round(np.clip(airflow,   600, 950),  1),
            "water_flow_L":    round(np.clip(water_flow,150, 280),  2),
            "smoke_ppm":       round(np.clip(smoke,       0, 200),  1),
            "water_leak":      1,
            "motion_detected": int(np.random.random() < 0.05),
            "door_open":       int(np.random.random() < 0.1),
            "hour_of_day":     hour,
            "cooling_mode":    "emergency",
            "PUE":             pue,
            "WUE":             wue,
            "alert_flag":      2,
        })
    return records


# ─────────────────────────────────────────────
# SCENARIO 5 — Unauthorized entry
# ─────────────────────────────────────────────
def gen_intrusion(n=100):
    records = []
    for _ in range(n):
        hour = int(np.random.choice(
            list(range(0, 6)) + list(range(22, 24)),
            p=[1/8]*6 + [1/8]*2
        ))
        temp       = noisy(21, 1.5)
        humidity   = noisy(50, 4)
        power      = noisy(55, 5)
        airflow    = noisy(750, 60)
        water_flow = noisy(8, 2)
        smoke      = noisy(50, 10)        # no fire, just intrusion
        pue        = round(1.5 + np.random.uniform(0, 0.2), 3)
        wue        = round(0.7 + np.random.uniform(0, 0.3), 3)
        records.append({
            "temperature_C":   round(np.clip(temp,       16,  27),  2),
            "humidity_pct":    round(np.clip(humidity,   40,  62),  2),
            "power_kW":        round(np.clip(power,      45,  70),  2),
            "airflow_cfm":     round(np.clip(airflow,   600, 900),  1),
            "water_flow_L":    round(np.clip(water_flow,  4,  18),  2),
            "smoke_ppm":       round(np.clip(smoke,       0, 200),  1),
            "water_leak":      0,
            "motion_detected": 1,
            "door_open":       int(np.random.random() < 0.7),
            "hour_of_day":     hour,
            "cooling_mode":    "security_alert",
            "PUE":             pue,
            "WUE":             wue,
            "alert_flag":      2,
        })
    return records


# ─────────────────────────────────────────────
# SCENARIO 6 — Static discharge risk
# ─────────────────────────────────────────────
def gen_static_risk(n=100):
    records = []
    for _ in range(n):
        temp       = noisy(22, 2)
        humidity   = noisy(23, 4)
        power      = noisy(62, 6)
        airflow    = noisy(820, 60)
        water_flow = noisy(12, 2)
        smoke      = noisy(50, 10)        # normal — dry air, not smoke
        hour       = np.random.randint(0, 24)
        pue        = round(1.45 + np.random.uniform(0, 0.2), 3)
        wue        = round(0.55 + np.random.uniform(0, 0.3), 3)
        records.append({
            "temperature_C":   round(np.clip(temp,       17,  28),  2),
            "humidity_pct":    round(np.clip(humidity,   10,  30),  2),
            "power_kW":        round(np.clip(power,      50,  78),  2),
            "airflow_cfm":     round(np.clip(airflow,   680, 980),  1),
            "water_flow_L":    round(np.clip(water_flow,  6,  20),  2),
            "smoke_ppm":       round(np.clip(smoke,       0, 200),  1),
            "water_leak":      0,
            "motion_detected": int(np.random.random() < 0.05),
            "door_open":       int(np.random.random() < 0.05),
            "hour_of_day":     hour,
            "cooling_mode":    "humidity_warn",
            "PUE":             pue,
            "WUE":             wue,
            "alert_flag":      1,
        })
    return records


# ─────────────────────────────────────────────
# ASSEMBLE & SAVE
# ─────────────────────────────────────────────
def generate_dataset():
    print("Generating synthetic data center sensor dataset...\n")
    all_records = []
    scenarios = [
        ("Normal operation",   gen_normal,          500),
        ("High load",          gen_high_load,       400),
        ("Cooling failure",    gen_cooling_failure, 150),
        ("Flooding risk",      gen_flooding,        100),
        ("Unauthorized entry", gen_intrusion,       100),
        ("Static risk",        gen_static_risk,     100),
    ]
    for label, fn, n in scenarios:
        records = fn(n)
        all_records.extend(records)
        print(f"  ✓ {label:25s} — {n} samples")

    df = pd.DataFrame(all_records)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    df.insert(0, "sample_id", range(1, len(df) + 1))
    return df


if __name__ == "__main__":
    df = generate_dataset()
    df.to_csv("datacenter_dataset.csv", index=False)

    print(f"\nTotal samples  : {len(df)}")
    print(f"Total columns  : {df.shape[1]}")
    print(f"\nClass balance:\n{df['cooling_mode'].value_counts().to_string()}")
    print(f"\nSmoke ppm stats:\n{df['smoke_ppm'].describe().round(2).to_string()}")
    print(f"\nDataset saved → datacenter_dataset.csv")
