# ─────────────────────────────────────────────
#  pages/performance.py  –  Records & tendances
# ─────────────────────────────────────────────

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from src.data.processor import get_prs, get_pace_trend
from src.config import COLORS, PLOTLY_TEMPLATE


def render(df: pd.DataFrame):
    st.markdown("## 🏆 Performance")
    st.markdown("Tes records personnels et l'évolution de ta forme.")
    st.markdown("---")

    prs   = get_prs(df)
    trend = get_pace_trend(df, n_weeks=16)

    # ── Records personnels ────────────────────
    st.markdown("#### 🥇 Records personnels")
    cols = st.columns(5)
    pr_labels = {
        "1km":      ("1 km",       "🔵"),
        "5km":      ("5 km",       "🟠"),
        "10km":     ("10 km",      "🔴"),
        "semi":     ("Semi-mara.", "🟣"),
        "marathon": ("Marathon",   "⭐"),
    }
    for i, (key, (label, icon)) in enumerate(pr_labels.items()):
        pr = prs.get(key)
        with cols[i]:
            if pr:
                st.markdown(f"""
                <div class="pr-card">
                    <div class="pr-icon">{icon}</div>
                    <div class="pr-distance">{label}</div>
                    <div class="pr-time">{pr['label']}</div>
                    <div class="pr-pace">{pr['pace']}</div>
                    <div class="pr-date">{pr['date']}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="pr-card pr-empty">
                    <div class="pr-icon">{icon}</div>
                    <div class="pr-distance">{label}</div>
                    <div class="pr-time">—</div>
                    <div class="pr-date">Pas encore</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Tendance d'allure ─────────────────────
    col_trend, col_dist = st.columns([3, 2])

    with col_trend:
        st.markdown("#### 📈 Évolution de l'allure (16 semaines)")
        if not trend.empty:
            fig = _pace_trend_chart(trend)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Pas assez de données.")

    with col_dist:
        st.markdown("#### 📊 Distribution des distances")
        fig2 = _dist_histogram(df)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # ── Top 10 meilleures allures ─────────────
    st.markdown("#### ⚡ Top 10 – Meilleures allures")
    top10 = (
        df.nsmallest(10, "pace_s_per_km")
        [["date", "name", "distance_km", "pace_label", "duration_label", "avg_hr"]]
        .copy()
    )
    top10["date"] = top10["date"].dt.strftime("%d/%m/%Y")
    top10["distance_km"] = top10["distance_km"].apply(lambda x: f"{x:.2f} km")
    top10["avg_hr"] = top10["avg_hr"].apply(
        lambda x: f"{int(x)} bpm" if pd.notna(x) and x > 0 else "—"
    )
    top10.columns = ["Date", "Nom", "Distance", "Allure", "Durée", "FC moy."]
    st.dataframe(top10, use_container_width=True, hide_index=True)


# ── Graphiques ─────────────────────────────

def _pace_trend_chart(trend: pd.DataFrame):
    fig = go.Figure()

    # Ligne d'allure
    fig.add_trace(go.Scatter(
        x=trend["week"],
        y=trend["avg_pace_min"],
        mode="lines+markers",
        name="Allure moy.",
        line=dict(color=COLORS["primary"], width=2.5),
        marker=dict(size=6),
        hovertemplate="<b>%{x|%d %b}</b><br>Allure : %{y:.2f} min/km<extra></extra>",
    ))

    # Tendance linéaire (régression simple)
    if len(trend) >= 3:
        x_num = (trend["week"] - trend["week"].min()).dt.days
        z = np.polyfit(x_num, trend["avg_pace_min"], 1)
        p = np.poly1d(z)
        fig.add_trace(go.Scatter(
            x=trend["week"],
            y=p(x_num),
            mode="lines",
            name="Tendance",
            line=dict(color=COLORS["warning"], width=1.5, dash="dot"),
        ))

    fig.update_yaxes(autorange="reversed")   # allure : plus bas = mieux
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis_title="min/km",
        xaxis_title="",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def _dist_histogram(df: pd.DataFrame):
    fig = px.histogram(
        df,
        x="distance_km",
        nbins=20,
        color_discrete_sequence=[COLORS["secondary"]],
        labels={"distance_km": "Distance (km)", "count": "Nombre de runs"},
    )
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis_title="Runs",
        bargap=0.05,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig
