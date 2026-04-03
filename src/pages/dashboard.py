# ─────────────────────────────────────────────
#  pages/dashboard.py  –  Vue principale
# ─────────────────────────────────────────────

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from src.data.processor import get_stats, get_weekly_volume, process_data
from src.config import COLORS, PLOTLY_TEMPLATE


def render(df: pd.DataFrame):
    st.markdown("## 📊 Dashboard")
    st.markdown("Vue d'ensemble de ton activité running.")
    st.markdown("---")

    stats = get_stats(df)
    weekly = get_weekly_volume(df)

    # ── Ligne 1 : métriques clés ────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _metric("Runs totaux", f"{stats['total_runs']}", "🏃")
    with c2:
        _metric("Km totaux", f"{stats['total_km']:.1f} km", "📏")
    with c3:
        _metric("7 derniers jours", f"{stats['km_7d']:.1f} km", "📅")
    with c4:
        _metric("30 derniers jours", f"{stats['km_30d']:.1f} km", "🗓️")

    st.markdown("")

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        _metric("Allure moyenne", stats["avg_pace_label"], "⚡")
    with c6:
        _metric("Distance moyenne", f"{stats['avg_dist']:.2f} km", "📐")
    with c7:
        _metric("Temps total", stats["total_time_label"], "⏱️")
    with c8:
        _metric("Dénivelé total", f"{stats['total_elev']:,} m", "⛰️")

    st.markdown("---")

    # ── Graphique : volume hebdomadaire ──────
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("#### Volume hebdomadaire (km)")
        if not weekly.empty:
            fig = _bar_weekly(weekly)
            st.plotly_chart(fig, use_container_width=True)
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
    fig2 = _scatter_activity(df)
    st.plotly_chart(fig2, use_container_width=True)


# ── Helpers UI ────────────────────────────────

def _metric(label: str, value: str, icon: str = ""):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-icon">{icon}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def _bar_weekly(weekly: pd.DataFrame):
    # Cible hebdomadaire
    from src.config import GOALS
    target = GOALS["weekly_km_target"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=weekly["week"].dt.strftime("%d %b"),
        y=weekly["km"],
        marker_color=COLORS["primary"],
        name="Volume (km)",
        hovertemplate="<b>%{x}</b><br>%{y:.1f} km<extra></extra>",
    ))
    fig.add_hline(
        y=target,
        line_dash="dot",
        line_color=COLORS["warning"],
        annotation_text=f"Objectif {target} km",
        annotation_position="top right",
    )
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=300,
        margin=dict(l=0, r=0, t=20, b=0),
        showlegend=False,
        yaxis_title="km",
        xaxis_title="",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _scatter_activity(df: pd.DataFrame):
    dfc = df.copy()
    dfc["date_str"] = dfc["date"].dt.strftime("%d/%m/%Y")

    fig = px.scatter(
        dfc,
        x="date",
        y="distance_km",
        color="run_type",
        size="distance_km",
        size_max=18,
        color_discrete_map={
            "Facile":  COLORS["easy_run"],
            "Soutenu": COLORS["hard_run"],
        },
        hover_data={
            "date": False,
            "date_str": True,
            "distance_km": ":.2f",
            "pace_label": True,
            "run_type": True,
        },
        labels={
            "distance_km": "Distance (km)",
            "date_str": "Date",
            "pace_label": "Allure",
            "run_type": "Type",
        },
    )
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=280,
        margin=dict(l=0, r=0, t=10, b=0),
        legend_title="Type de run",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig
