# ─────────────────────────────────────────────
#  pages/dashboard.py  –  Vue principale
# ─────────────────────────────────────────────
from __future__ import annotations

import streamlit as st
import pandas as pd
from src.data.processor import get_stats, get_weekly_volume, process_data
from src.config import COLORS
from src.ui import css_bar_chart, css_scatter


def render(df: pd.DataFrame):
    st.markdown("## 📊 Dashboard")
    st.markdown("Vue d'ensemble de ton activité running.")
    st.markdown("---")

    stats = get_stats(df)
    weekly = get_weekly_volume(df)

    # ── Métriques clés (grille responsive 2×2 / 4) ──
    metrics = [
        ("Runs totaux",      f"{stats['total_runs']}",          "🏃"),
        ("Km totaux",        f"{stats['total_km']:.1f} km",     "📏"),
        ("7 derniers jours", f"{stats['km_7d']:.1f} km",        "📅"),
        ("30 derniers jours",f"{stats['km_30d']:.1f} km",       "🗓️"),
        ("Allure moyenne",   stats["avg_pace_label"],           "⚡"),
        ("Distance moyenne", f"{stats['avg_dist']:.2f} km",     "📐"),
        ("Temps total",      stats["total_time_label"],         "⏱️"),
        ("Dénivelé total",   f"{stats['total_elev']:,} m",      "⛰️"),
    ]
    _metric_grid(metrics)

    st.markdown("---")

    # ── Graphique : volume hebdomadaire ──────
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("#### Volume hebdomadaire (km)")
        if not weekly.empty:
            from src.config import GOALS
            recent = weekly.tail(12)
            css_bar_chart(
                labels=[d.strftime("%d %b") for d in recent["week"]],
                values=recent["km"].tolist(),
                goal=GOALS["weekly_km_target"],
                caption="Kilomètres courus par semaine",
            )
        else:
            st.info("Pas assez de données pour afficher le graphique.")

    with col_right:
        st.markdown("#### Dernières sorties")
        recent = df.head(7)[["date", "distance_km", "pace_label", "duration_label"]].copy()
        recent["date"] = recent["date"].dt.strftime("%d/%m/%y")
        recent.columns = ["Date", "Km", "Allure", "Durée"]
        recent["Km"] = recent["Km"].apply(lambda x: f"{x:.2f}")
        st.dataframe(recent, use_container_width=True, hide_index=True)

    # ── Graphique : activité sur la période ──
    st.markdown("---")
    st.markdown("#### Activité sur la période")
    _activity_scatter(df)


# ── Helpers UI ────────────────────────────────

def _metric_grid(items: list[tuple[str, str, str]]):
    """items = [(label, value, icon), …] → grille responsive 2×2 (mobile) / 4 (desktop)."""
    cards = "".join(
        f'<div class="metric-card">'
        f'<div class="metric-icon">{icon}</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-label">{label}</div>'
        f'</div>'
        for label, value, icon in items
    )
    st.markdown(f'<div class="metric-grid">{cards}</div>', unsafe_allow_html=True)


def _activity_scatter(df: pd.DataFrame):
    d = df.dropna(subset=["date", "distance_km"])
    if d.empty:
        st.info("Pas de données pour la période.")
        return
    dmin, dmax = d["date"].min(), d["date"].max()
    span = (dmax - dmin).total_seconds() or 1.0
    xs = [(x - dmin).total_seconds() / span for x in d["date"]]
    css_scatter(
        xs=xs,
        values=d["distance_km"].tolist(),
        types=d["run_type"].tolist(),
        color_map={
            "Facile":  COLORS["easy_run"],
            "Soutenu": COLORS["hard_run"],
        },
        unit="km",
        x_start=dmin.strftime("%d/%m/%y"),
        x_end=dmax.strftime("%d/%m/%y"),
        caption="Chaque point = une sortie · hauteur = distance · taille ∝ distance",
    )
