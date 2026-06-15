# ─────────────────────────────────────────────
#  strava_api.py  –  Connexion directe à l'API Strava
# ─────────────────────────────────────────────
"""
Récupère les activités EN DIRECT via l'API Strava (plus besoin de CSV).

Mécanique :
  1. On garde en Secrets : STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET,
     STRAVA_REFRESH_TOKEN (obtenu une seule fois via scripts/get_strava_token.py).
  2. À chaque chargement, on échange le refresh_token contre un access_token
     valide (les access tokens expirent toutes les 6 h ; le refresh, lui, dure).
  3. On télécharge les activités (paginé) et on les mappe vers le schéma
     normalisé du reste de l'app.

Robustesse : si rien n'est configuré OU si l'API échoue, on renvoie None →
loader.py bascule automatiquement sur le CSV. L'app ne plante jamais.
"""

from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

TOKEN_URL      = "https://www.strava.com/oauth/token"
ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"

_SECRET_KEYS = ("STRAVA_CLIENT_ID", "STRAVA_CLIENT_SECRET", "STRAVA_REFRESH_TOKEN")


# ── Lecture défensive des secrets ─────────────
def _get_secret(key: str):
    """Renvoie un secret ou None (sans planter si aucun secrets.toml)."""
    try:
        return st.secrets.get(key)
    except Exception:
        return None


def is_configured() -> bool:
    """True si les 3 secrets Strava sont présents."""
    return all(_get_secret(k) for k in _SECRET_KEYS)


# ── OAuth : refresh → access token ────────────
def _refresh_access_token() -> str | None:
    cid     = _get_secret("STRAVA_CLIENT_ID")
    secret  = _get_secret("STRAVA_CLIENT_SECRET")
    refresh = _get_secret("STRAVA_REFRESH_TOKEN")
    if not (cid and secret and refresh):
        return None

    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id":     cid,
            "client_secret": secret,
            "grant_type":    "refresh_token",
            "refresh_token": refresh,
        },
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json().get("access_token")


# ── Récupération paginée des activités ────────
def _fetch_all_activities(access_token: str, max_activities: int = 2000) -> list:
    headers  = {"Authorization": f"Bearer {access_token}"}
    per_page = 200
    page     = 1
    out: list = []

    while len(out) < max_activities:
        resp = requests.get(
            ACTIVITIES_URL,
            headers=headers,
            params={"per_page": per_page, "page": page},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        out.extend(batch)
        if len(batch) < per_page:   # dernière page
            break
        page += 1

    return out


# ── Mapping JSON Strava → schéma normalisé ────
def activities_to_df(activities: list) -> pd.DataFrame:
    """Convertit la liste d'activités de l'API en DataFrame normalisé."""
    rows = []
    for a in activities:
        speed = a.get("average_speed")  # m/s
        rows.append({
            # start_date_local est l'heure locale mais suffixée "Z" (trompeur) :
            # on retire le Z pour obtenir un datetime naïf, comme l'export CSV.
            "date":           (a.get("start_date_local") or a.get("start_date") or "").replace("Z", ""),
            "name":           a.get("name", ""),
            "type":           a.get("sport_type") or a.get("type") or "",
            "distance_km":    (a.get("distance") or 0) / 1000.0,
            "moving_time_s":  a.get("moving_time"),
            "elapsed_time_s": a.get("elapsed_time"),
            "elevation_m":    a.get("total_elevation_gain"),
            "avg_hr":         a.get("average_heartrate"),
            "max_hr":         a.get("max_heartrate"),
            "avg_speed_kmh":  (speed * 3.6) if speed is not None else None,
        })
    return pd.DataFrame(rows)


# ── Point d'entrée caché (cache 15 min) ───────
@st.cache_data(ttl=900, show_spinner=False)
def load_strava_df() -> pd.DataFrame | None:
    """
    Renvoie un DataFrame normalisé des activités Strava, ou None si non
    configuré / en cas d'erreur réseau (→ fallback CSV dans loader.py).
    """
    if not is_configured():
        return None
    try:
        token = _refresh_access_token()
        if not token:
            return None
        activities = _fetch_all_activities(token)
        if not activities:
            return None
        return activities_to_df(activities)
    except Exception:
        # On ne casse pas l'app : loader.py basculera sur le CSV.
        return None
