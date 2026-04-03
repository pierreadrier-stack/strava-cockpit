# ─────────────────────────────────────────────
#  loader.py  –  Chargement et normalisation CSV
# ─────────────────────────────────────────────
"""
Supporte deux formats d'entrée :
  1. Export bulk Strava (strava.com → Paramètres → Mes données)
  2. Format CSV simplifié (colonnes normalisées directement)

Le DataFrame retourné est toujours dans le format normalisé :
  date, name, type, distance_km, moving_time_s, elapsed_time_s,
  elevation_m, avg_hr, max_hr, avg_speed_kmh, calories
"""

import pandas as pd
import numpy as np
from pathlib import Path
import streamlit as st

# ── Chemins vers les données ─────────────────
SAMPLE_PATH  = Path(__file__).parent.parent.parent / "data" / "sample_activities.csv"
STRAVA_PATH  = Path(__file__).parent.parent.parent / "data" / "activities_strava.csv"


@st.cache_data(show_spinner=False)
def load_data(uploaded_file=None) -> pd.DataFrame:
    """
    Charge les données depuis :
    - un fichier uploadé via st.file_uploader  (priorité 1)
    - data/activities_strava.csv si présent     (priorité 2)
    - data/sample_activities.csv               (priorité 3 – démo)
    Retourne un DataFrame normalisé filtré sur les runs.
    """
    if uploaded_file is not None:
        raw = pd.read_csv(uploaded_file)
    elif STRAVA_PATH.exists():
        raw = pd.read_csv(STRAVA_PATH)
    elif SAMPLE_PATH.exists():
        raw = pd.read_csv(SAMPLE_PATH)
    else:
        return pd.DataFrame()

    df = _normalize(raw)
    df = _filter_runs(df)
    df = _clean(df)
    return df


# ── Détection et dispatch ────────────────────

def _normalize(raw: pd.DataFrame) -> pd.DataFrame:
    cols = set(raw.columns)

    if "Activity Date" in cols:          # Export bulk Strava
        return _from_strava_bulk(raw)

    if "date" in cols and "distance_km" in cols:   # Format normalisé
        return raw.copy()

    # Tentative générique
    raw.columns = [c.strip().lower().replace(" ", "_") for c in raw.columns]
    return raw.copy()


# ── Parseur export bulk Strava ───────────────

def _from_strava_bulk(raw: pd.DataFrame) -> pd.DataFrame:
    """
    L'export Strava a des colonnes dupliquées (Elapsed Time, Distance,
    Max Heart Rate, Relative Effort, Commute).  Pandas les renomme
    automatiquement en ajoutant .1, .2 …
    On cible les bonnes colonnes par nom exact après lecture.
    """
    df = pd.DataFrame()

    # ── Date ─────────────────────────────────
    df["date"] = pd.to_datetime(raw.get("Activity Date"), errors="coerce")

    # ── Nom & type ────────────────────────────
    df["name"] = raw.get("Activity Name", "")
    df["type"] = raw.get("Activity Type", raw.get("Sport Type", ""))

    # ── Distance ─────────────────────────────
    # Première colonne "Distance" = km (ex: 2.12)
    # Deuxième = mètres (ex: 2120.7) → on prend la première
    dist_cols = [c for c in raw.columns if c == "Distance"]
    if dist_cols:
        dist = pd.to_numeric(raw[dist_cols[0]], errors="coerce")
        # Sécurité : si valeurs > 500 → probablement en mètres
        if dist.median() > 500:
            dist = dist / 1000
        df["distance_km"] = dist
    else:
        df["distance_km"] = np.nan

    # ── Temps de déplacement ─────────────────
    # "Moving Time" = colonne unique (secondes, float)
    if "Moving Time" in raw.columns:
        df["moving_time_s"] = pd.to_numeric(raw["Moving Time"], errors="coerce")
    else:
        # Fallback : première colonne Elapsed Time
        et_cols = [c for c in raw.columns if c == "Elapsed Time"]
        df["moving_time_s"] = pd.to_numeric(raw[et_cols[0]], errors="coerce") if et_cols else np.nan

    # ── Elapsed time ─────────────────────────
    et_cols = [c for c in raw.columns if c.startswith("Elapsed Time")]
    if et_cols:
        df["elapsed_time_s"] = pd.to_numeric(raw[et_cols[0]], errors="coerce")

    # ── Dénivelé ─────────────────────────────
    if "Elevation Gain" in raw.columns:
        df["elevation_m"] = pd.to_numeric(raw["Elevation Gain"], errors="coerce")

    # ── Fréquence cardiaque ───────────────────
    # "Average Heart Rate" est unique dans l'export
    if "Average Heart Rate" in raw.columns:
        df["avg_hr"] = pd.to_numeric(raw["Average Heart Rate"], errors="coerce")

    # "Max Heart Rate" est dupliquée → on prend la 2e (colonne détaillée)
    hr_cols = [c for c in raw.columns if c == "Max Heart Rate"]
    if len(hr_cols) >= 2:
        df["max_hr"] = pd.to_numeric(raw[hr_cols[1]], errors="coerce")
    elif hr_cols:
        df["max_hr"] = pd.to_numeric(raw[hr_cols[0]], errors="coerce")

    # ── Vitesse moyenne (m/s → km/h) ─────────
    if "Average Speed" in raw.columns:
        speed = pd.to_numeric(raw["Average Speed"], errors="coerce")
        df["avg_speed_kmh"] = speed * 3.6    # Strava exporte en m/s

    # ── Calories ─────────────────────────────
    if "Calories" in raw.columns:
        df["calories"] = pd.to_numeric(raw["Calories"], errors="coerce")

    return df


# ── Filtre sur les runs ──────────────────────

def _filter_runs(df: pd.DataFrame) -> pd.DataFrame:
    if "type" not in df.columns:
        return df
    run_types = {"Run", "Running", "TrailRun", "Trail Run", "VirtualRun",
                 "run", "running"}
    mask = df["type"].isin(run_types)
    return df[mask].reset_index(drop=True)


# ── Nettoyage final ──────────────────────────

def _clean(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = [
        "distance_km", "moving_time_s", "elapsed_time_s",
        "elevation_m", "avg_hr", "max_hr", "avg_speed_kmh", "calories"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df = df.dropna(subset=["date", "distance_km"])
    df = df[df["distance_km"] > 0]
    df = df.sort_values("date", ascending=False).reset_index(drop=True)
    return df
