# ─────────────────────────────────────────────
#  pages/runs.py  –  Tableau de toutes les sorties
# ─────────────────────────────────────────────

import streamlit as st
import pandas as pd
from src.config import COLORS


def render(df: pd.DataFrame):
    st.markdown("## 🗂️ Mes Runs")
    st.markdown("Historique complet de toutes tes sorties.")
    st.markdown("---")

    # ── Filtres ──────────────────────────────
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        if df["date"].notna().any():
            min_date = df["date"].min().date()
            max_date = df["date"].max().date()
            date_range = st.date_input(
                "Période",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
            )
        else:
            date_range = None

    with col2:
        dist_filter = st.slider(
            "Distance minimale (km)",
            min_value=0.0,
            max_value=float(df["distance_km"].max()),
            value=0.0,
            step=0.5,
        )

    with col3:
        run_type = st.selectbox("Type de run", ["Tous", "Facile", "Soutenu"])

    # ── Filtrage ─────────────────────────────
    filtered = df.copy()
    if date_range and len(date_range) == 2:
        start, end = date_range
        filtered = filtered[
            (filtered["date"].dt.date >= start) &
            (filtered["date"].dt.date <= end)
        ]
    if dist_filter > 0:
        filtered = filtered[filtered["distance_km"] >= dist_filter]
    if run_type != "Tous":
        filtered = filtered[filtered["run_type"] == run_type]

    st.markdown(f"**{len(filtered)} sorties** affichées")
    st.markdown("")

    # ── Construction du tableau ───────────────
    display = _build_display(filtered)
    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Date":     st.column_config.TextColumn("Date", width="small"),
            "Nom":      st.column_config.TextColumn("Nom", width="medium"),
            "Distance": st.column_config.TextColumn("Distance", width="small"),
            "Durée":    st.column_config.TextColumn("Durée", width="small"),
            "Allure":   st.column_config.TextColumn("Allure", width="small"),
            "Dénivelé": st.column_config.TextColumn("Dénivelé", width="small"),
            "FC moy.":  st.column_config.TextColumn("FC moy.", width="small"),
            "Type":     st.column_config.TextColumn("Type", width="small"),
        },
        height=600,
    )

    # ── Résumé bas de page ────────────────────
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("Distance totale", f"{filtered['distance_km'].sum():.1f} km")
    c2.metric("Runs", len(filtered))
    avg_dist = filtered["distance_km"].mean()
    c3.metric("Distance moyenne", f"{avg_dist:.2f} km" if not pd.isna(avg_dist) else "—")


def _build_display(df: pd.DataFrame) -> pd.DataFrame:
    """Construit le DataFrame d'affichage propre."""
    out = pd.DataFrame()
    out["Date"]     = df["date"].dt.strftime("%d/%m/%Y")
    out["Nom"]      = df["name"].fillna("—") if "name" in df.columns else "—"
    out["Distance"] = df["distance_km"].apply(lambda x: f"{x:.2f} km")
    out["Durée"]    = df["duration_label"]
    out["Allure"]   = df["pace_label"]

    if "elevation_m" in df.columns:
        out["Dénivelé"] = df["elevation_m"].apply(
            lambda x: f"{int(x)} m" if pd.notna(x) else "—"
        )
    else:
        out["Dénivelé"] = "—"

    if "avg_hr" in df.columns:
        out["FC moy."] = df["avg_hr"].apply(
            lambda x: f"{int(x)} bpm" if pd.notna(x) and x > 0 else "—"
        )
    else:
        out["FC moy."] = "—"

    out["Type"] = df["run_type"] if "run_type" in df.columns else "—"
    return out
