# ─────────────────────────────────────────────
#  processor.py  –  Logique métier & métriques
# ─────────────────────────────────────────────
"""
Toute la logique de calcul est ici, séparée de l'UI.
Les pages importent les fonctions dont elles ont besoin.
"""

import pandas as pd
import numpy as np
from src.config import GOALS, PR_DISTANCES, SEUIL_ALLURE_SOUTENU


# ── 1. Enrichissement du DataFrame ───────────

def process_data(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les colonnes calculées au DataFrame brut."""
    df = df.copy()

    # Allure (min/km)
    df["pace_s_per_km"] = df.apply(
        lambda r: r["moving_time_s"] / r["distance_km"]
        if r["distance_km"] > 0 else np.nan, axis=1
    )
    df["pace_min_km"] = df["pace_s_per_km"] / 60          # float minutes
    df["pace_label"]  = df["pace_s_per_km"].apply(_fmt_pace)

    # Durée formatée
    df["duration_label"] = df["moving_time_s"].apply(_fmt_duration)

    # Semaine / Mois (pour agrégations)
    df["week"]  = df["date"].dt.to_period("W").apply(lambda p: p.start_time)
    df["month"] = df["date"].dt.to_period("M").apply(lambda p: p.start_time)
    df["year"]  = df["date"].dt.year

    # Type de run (facile / soutenu)
    df["run_type"] = df["pace_min_km"].apply(
        lambda p: "Soutenu" if pd.notna(p) and p <= SEUIL_ALLURE_SOUTENU else "Facile"
    )

    return df


# ── 2. Statistiques globales ──────────────────

def get_stats(df: pd.DataFrame) -> dict:
    """Retourne un dict de métriques agrégées pour le dashboard."""
    now  = pd.Timestamp.now()
    d7   = now - pd.Timedelta(days=7)
    d30  = now - pd.Timedelta(days=30)

    total_runs    = len(df)
    total_km      = df["distance_km"].sum()
    km_7d         = df[df["date"] >= d7]["distance_km"].sum()
    km_30d        = df[df["date"] >= d30]["distance_km"].sum()
    avg_dist      = df["distance_km"].mean()
    total_time_s  = df["moving_time_s"].sum()
    avg_pace_s    = (df["pace_s_per_km"].mean()
                     if "pace_s_per_km" in df.columns else np.nan)
    total_elev    = df["elevation_m"].sum() if "elevation_m" in df.columns else 0

    return {
        "total_runs":    total_runs,
        "total_km":      round(total_km, 1),
        "km_7d":         round(km_7d, 1),
        "km_30d":        round(km_30d, 1),
        "avg_dist":      round(avg_dist, 2),
        "total_time_s":  total_time_s,
        "total_time_label": _fmt_duration(total_time_s),
        "avg_pace_label": _fmt_pace(avg_pace_s),
        "total_elev":    int(total_elev),
    }


# ── 3. Records personnels ─────────────────────

def get_prs(df: pd.DataFrame) -> dict:
    """
    Calcule les PRs sur les distances standard.
    Méthode : on cherche les activités dont la distance
    est dans la fourchette [target - tol, target + tol]
    et on prend le meilleur temps.
    """
    prs = {}
    for label, cfg in PR_DISTANCES.items():
        lo = cfg["target"] - cfg["tol"]
        hi = cfg["target"] + cfg["tol"]
        subset = df[(df["distance_km"] >= lo) & (df["distance_km"] <= hi)].copy()
        if subset.empty:
            prs[label] = None
        else:
            best = subset.loc[subset["moving_time_s"].idxmin()]
            prs[label] = {
                "time_s":   best["moving_time_s"],
                "label":    _fmt_duration(best["moving_time_s"]),
                "pace":     best.get("pace_label", "—"),
                "date":     best["date"].strftime("%d/%m/%Y"),
                "distance": round(best["distance_km"], 2),
            }
    return prs


# ── 4. Volume hebdo / mensuel ─────────────────

def get_weekly_volume(df: pd.DataFrame) -> pd.DataFrame:
    """Retourne un DataFrame agrégé par semaine."""
    grp = (
        df.groupby("week")
        .agg(
            km=("distance_km", "sum"),
            runs=("distance_km", "count"),
            avg_pace_s=("pace_s_per_km", "mean"),
            avg_hr=("avg_hr", "mean"),
        )
        .reset_index()
        .sort_values("week")
    )
    grp["week_label"] = grp["week"].dt.strftime("S%W\n%d %b")
    return grp


def get_monthly_volume(df: pd.DataFrame) -> pd.DataFrame:
    """Retourne un DataFrame agrégé par mois."""
    grp = (
        df.groupby("month")
        .agg(
            km=("distance_km", "sum"),
            runs=("distance_km", "count"),
            avg_pace_s=("pace_s_per_km", "mean"),
        )
        .reset_index()
        .sort_values("month")
    )
    grp["month_label"] = grp["month"].dt.strftime("%b %Y")
    return grp


# ── 5. Progression vers les objectifs ────────

def get_goal_progress(df: pd.DataFrame, prs: dict) -> dict:
    """Calcule la progression (0–1) vers chaque objectif."""
    progress = {}

    # 5 km sub 25
    pr_5k = prs.get("5km")
    if pr_5k:
        target = GOALS["5k_target_seconds"]
        best   = pr_5k["time_s"]
        # Plus le temps est proche du target, plus la progression est haute
        # On considère un temps de "départ" à 35 min pour un coureur débutant
        start  = 35 * 60
        ratio  = 1 - max(0, (best - target) / (start - target))
        progress["5km"] = min(1.0, max(0.0, ratio))
    else:
        progress["5km"] = 0.0

    # 10 km sub 50
    pr_10k = prs.get("10km")
    if pr_10k:
        target = GOALS["10k_target_seconds"]
        best   = pr_10k["time_s"]
        start  = 70 * 60
        ratio  = 1 - max(0, (best - target) / (start - target))
        progress["10km"] = min(1.0, max(0.0, ratio))
    else:
        progress["10km"] = 0.0

    # Marathon : objectif de présence – progression basée sur la distance max hebdo
    weekly = get_weekly_volume(df)
    max_weekly_km = weekly["km"].max() if not weekly.empty else 0
    progress["marathon"] = min(1.0, max_weekly_km / 60)   # 60 km/sem = prêt

    # Volume hebdo cible
    recent_weeks = weekly.tail(4)["km"].mean() if not weekly.empty else 0
    progress["volume"] = min(1.0, recent_weeks / GOALS["weekly_km_target"])

    return progress


# ── 6. Tendance de performance ────────────────

def get_pace_trend(df: pd.DataFrame, n_weeks: int = 12) -> pd.DataFrame:
    """Retourne l'allure moyenne hebdomadaire sur les n dernières semaines."""
    cutoff = pd.Timestamp.now() - pd.Timedelta(weeks=n_weeks)
    recent = df[df["date"] >= cutoff].copy()
    if recent.empty:
        return pd.DataFrame()

    trend = (
        recent.groupby("week")
        .agg(avg_pace_s=("pace_s_per_km", "mean"), km=("distance_km", "sum"))
        .reset_index()
        .sort_values("week")
    )
    trend["avg_pace_min"] = trend["avg_pace_s"] / 60
    trend["week_label"]   = trend["week"].dt.strftime("%d %b")
    return trend


# ── Helpers de formatage ──────────────────────

def _fmt_pace(seconds_per_km) -> str:
    """Convertit des secondes/km en chaîne 'mm:ss /km'."""
    if pd.isna(seconds_per_km) or seconds_per_km <= 0:
        return "—"
    mins = int(seconds_per_km // 60)
    secs = int(seconds_per_km % 60)
    return f"{mins}:{secs:02d} /km"


def _fmt_duration(seconds) -> str:
    """Convertit des secondes en 'Hh MMm' ou 'MMm SSs'."""
    if pd.isna(seconds) or seconds <= 0:
        return "—"
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m:02d}m"
    return f"{m}m {s:02d}s"
