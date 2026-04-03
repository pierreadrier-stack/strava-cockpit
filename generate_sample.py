"""
Script one-shot pour générer data/sample_activities.csv
Lance-le une seule fois : python generate_sample.py
"""
import pandas as pd
import numpy as np
from pathlib import Path

rng = np.random.default_rng(42)

# ── Paramètres de la simulation ──────────────
START = pd.Timestamp("2025-10-01")
END   = pd.Timestamp("2026-04-03")

# Toutes les dates de run (3–4x par semaine)
all_dates = pd.date_range(START, END, freq="D")
run_dates = []
week_runs = 0
for d in all_dates:
    if d.weekday() == 0:    # Lundi = reset compteur
        week_runs = 0
    # Probabilité de courir : plus haute si pas encore 4 runs cette semaine
    prob = 0.58 if week_runs < 3 else 0.25
    if rng.random() < prob:
        run_dates.append(d)
        week_runs += 1

n = len(run_dates)

# ── Types de runs avec distribution réaliste ─
# Semaines longues : dimanche ≥ 40 % du volume
# Mix : sortie longue, fractionné, récup, tempo

def pick_distance(date):
    dow = date.weekday()
    week_num = (date - START).days // 7
    # Progression douce du volume sur 6 mois
    progress = min(week_num / 26, 1.0)
    base_long = 12 + progress * 10   # de 12 km à 22 km
    if dow == 6:   # dimanche = sortie longue
        return rng.normal(base_long, 1.5)
    elif dow in (1, 3):  # mardi/jeudi = tempo ou fractionné
        return rng.normal(8 + progress * 4, 1.0)
    else:
        return rng.normal(6 + progress * 2, 0.8)

distances = [max(2.0, pick_distance(d)) for d in run_dates]

# ── Allures réalistes avec progression ────────
def pick_pace(dist, date):
    week_num = (date - START).days // 7
    progress = min(week_num / 26, 1.0)
    # Amélioration : de ~6:30 /km à ~5:30 /km sur 6 mois
    base_pace = 6.5 - progress * 1.0    # min/km
    if dist > 18:                        # long run = plus lent
        base_pace += 0.5
    elif dist < 7:                       # récup = encore plus lent
        base_pace += 0.3
    elif dist > 10:                      # tempo = plus vite
        base_pace -= 0.3
    noise = rng.normal(0, 0.2)
    return max(4.5, base_pace + noise)

paces_min_km = [pick_pace(d, dt) for d, dt in zip(distances, run_dates)]
moving_times_s = [int(p * dist * 60) for p, dist in zip(paces_min_km, distances)]

# ── Noms des sorties ──────────────────────────
def pick_name(date, dist):
    dow = date.weekday()
    if dow == 6 and dist > 15:
        return rng.choice(["Sortie longue", "Long run dominical", "Grand tour du week-end"])
    elif dist < 6:
        return rng.choice(["Footing récup", "Petite sortie", "Récupération active"])
    elif dist > 12:
        return rng.choice(["Tempo run", "Sortie tempo", "Run soutenu"])
    else:
        return rng.choice(["Run matinal", "Footing", "Sortie standard", "Run du midi"])

names = [pick_name(dt, d) for dt, d in zip(run_dates, distances)]

# ── Dénivelé ──────────────────────────────────
elevations = [int(max(0, rng.normal(d * 8, d * 3))) for d in distances]

# ── Fréquence cardiaque ───────────────────────
# 80 % des runs ont des données HR
has_hr = rng.random(n) < 0.80
avg_hrs = []
for i, (has, pace) in enumerate(zip(has_hr, paces_min_km)):
    if has:
        # Plus l'allure est rapide, plus la FC est haute
        base_hr = 165 - (pace - 5) * 12
        avg_hrs.append(int(rng.normal(base_hr, 5)))
    else:
        avg_hrs.append(None)

# ── Calories ──────────────────────────────────
calories = [int(d * 70 + rng.normal(0, 30)) for d in distances]

# ── Assembler le DataFrame ────────────────────
df = pd.DataFrame({
    "date":          [d.strftime("%Y-%m-%d") for d in run_dates],
    "name":          names,
    "type":          "Run",
    "distance_km":   [round(d, 2) for d in distances],
    "moving_time_s": moving_times_s,
    "elapsed_time_s":[int(t * rng.uniform(1.02, 1.08)) for t in moving_times_s],
    "elevation_m":   elevations,
    "avg_hr":        avg_hrs,
    "max_hr":        [int(h * 1.1) if h else None for h in avg_hrs],
    "avg_speed_kmh": [round(60 / p, 2) for p in paces_min_km],
    "calories":      calories,
})

out = Path("data/sample_activities.csv")
out.parent.mkdir(exist_ok=True)
df.to_csv(out, index=False)
print(f"✅ {n} activités générées → {out}")
print(df.head())
