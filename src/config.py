# ─────────────────────────────────────────────
#  config.py  –  Constantes globales de l'app
# ─────────────────────────────────────────────

APP_TITLE = "Running Cockpit"
APP_ICON  = "🏃"

# ── Objectifs personnels ─────────────────────
GOALS = {
    "5k_target_seconds":   25 * 60,   # 25 min
    "10k_target_seconds":  50 * 60,   # 50 min
    "marathon_target_seconds": None,  # Objectif présence, pas de temps cible
    "weekly_km_target": 40,           # km / semaine objectif
}

# ── Palette de couleurs ──────────────────────
COLORS = {
    "primary":    "#FC4C02",   # Orange Strava
    "secondary":  "#2E86AB",
    "success":    "#44BBA4",
    "warning":    "#F7B731",
    "danger":     "#E84855",
    "neutral":    "#6C757D",
    "easy_run":   "#44BBA4",   # Vert  → run facile
    "hard_run":   "#FC4C02",   # Orange → run soutenu
}

PLOTLY_TEMPLATE = "plotly_dark"

# ── Seuils de classification des runs ───────
# Un run est "soutenu" si l'allure est <= ce seuil (min/km)
SEUIL_ALLURE_SOUTENU = 5.5   # min/km  →  en dessous = effort soutenu

# ── Colonnes attendues dans le CSV normalisé ─
REQUIRED_COLUMNS = [
    "date", "name", "distance_km", "moving_time_s", "elevation_m"
]

# ── Mapping Strava bulk export → colonnes normalisées ──
# Géré dans loader.py

# ── Distances pour les PR (tolérance ±5 %) ──
PR_DISTANCES = {
    "1km":       {"target": 1.0,  "tol": 0.08},
    "5km":       {"target": 5.0,  "tol": 0.3},
    "10km":      {"target": 10.0, "tol": 0.5},
    "semi":      {"target": 21.1, "tol": 1.0},
    "marathon":  {"target": 42.2, "tol": 2.0},
}
