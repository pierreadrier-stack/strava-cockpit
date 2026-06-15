# ─────────────────────────────────────────────
#  pages/analyse.py  –  Analyse approfondie
# ─────────────────────────────────────────────

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from src.data.processor import get_weekly_volume, get_monthly_volume
from src.config import COLORS, PLOTLY_TEMPLATE
from src.ui import css_bar_chart, css_line_chart, apply_glass


def render(df: pd.DataFrame):
    st.markdown("## 📉 Analyse")
    st.markdown("Volume, fréquence, répartition et tendances détaillées.")
    st.markdown("---")

    weekly  = get_weekly_volume(df)
    monthly = get_monthly_volume(df)

    # ── Onglets ───────────────────────────────
    tab1, tab2, tab3 = st.tabs(["📅 Volume", "🔄 Fréquence", "🏷️ Répartition"])

    with tab1:
        _tab_volume(weekly, monthly)

    with tab2:
        _tab_frequence(df, weekly)

    with tab3:
        _tab_repartition(df)


# ── Onglet Volume ─────────────────────────────

def _tab_volume(weekly, monthly):
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### Volume hebdomadaire")
        if not weekly.empty:
            recent = weekly.tail(12)
            css_bar_chart(
                labels=[d.strftime("%d %b") for d in recent["week"]],
                values=recent["km"].tolist(),
                decimals=1,
                caption="Kilomètres par semaine",
            )

    with col2:
        st.markdown("#### Volume mensuel")
        if not monthly.empty:
            css_bar_chart(
                labels=monthly["month_label"].tolist(),
                values=monthly["km"].tolist(),
                accent="blue",
                decimals=1,
                caption="Kilomètres par mois",
            )

    # Évolution de l'allure moyenne par mois
    st.markdown("#### Allure moyenne mensuelle")
    if not monthly.empty:
        _pace_monthly_chart(monthly)


def _pace_monthly_chart(monthly):
    m = monthly.copy()
    m["avg_pace_min"] = m["avg_pace_s"] / 60
    css_line_chart(
        labels=m["month_label"].tolist(),
        values=m["avg_pace_min"].tolist(),
        accent="orange",
        unit="min/km",
        hint="↓ plus rapide",
        value_fmt=lambda v: f"{round(v * 60) // 60}:{round(v * 60) % 60:02d}",
    )


# ── Onglet Fréquence ──────────────────────────

def _tab_frequence(df, weekly):
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### Runs par semaine")
        if not weekly.empty:
            recent = weekly.tail(12)
            css_bar_chart(
                labels=[d.strftime("%d %b") for d in recent["week"]],
                values=recent["runs"].tolist(),
                decimals=0,
                caption="Nombre de sorties par semaine",
            )

    with col2:
        st.markdown("#### Jour de la semaine préféré")
        dow_counts = df["date"].dt.day_name()
        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        fr_names = {"Monday": "Lun", "Tuesday": "Mar", "Wednesday": "Mer",
                    "Thursday": "Jeu", "Friday": "Ven", "Saturday": "Sam", "Sunday": "Dim"}
        dow_df = dow_counts.value_counts().reindex(order, fill_value=0).reset_index()
        dow_df.columns = ["day_en", "count"]
        dow_df["day_fr"] = dow_df["day_en"].map(fr_names)
        css_bar_chart(
            labels=dow_df["day_fr"].tolist(),
            values=dow_df["count"].tolist(),
            accent="blue",
            decimals=0,
            caption="Nombre de sorties par jour de la semaine",
        )

    # Heatmap calendrier
    st.markdown("#### Calendrier des sorties")
    _calendar_heatmap(df)


def _calendar_heatmap(df):
    dfc = df.copy()
    dfc["dow"]  = dfc["date"].dt.weekday        # 0=Lundi … 6=Dimanche
    dfc["week"] = dfc["date"].dt.to_period("W").apply(lambda p: p.start_time)

    pivot = dfc.pivot_table(
        index="dow", columns="week", values="distance_km", aggfunc="sum"
    ).fillna(0)

    dow_labels = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    week_labels = [d.strftime("%d %b") for d in pivot.columns]

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=week_labels,
        y=dow_labels,
        colorscale=[[0, "#1E2130"], [0.01, "#2E4060"], [1, COLORS["primary"]]],
        showscale=True,
        hovertemplate="<b>%{y} – S%{x}</b><br>%{z:.1f} km<extra></extra>",
        colorbar=dict(title="km"),
    ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=230,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(tickangle=-45, tickfont_size=10),
    )
    st.plotly_chart(apply_glass(fig), use_container_width=True)


# ── Onglet Répartition ────────────────────────

def _tab_repartition(df):
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### Runs faciles vs soutenus")
        type_counts = df["run_type"].value_counts().reset_index()
        type_counts.columns = ["Type", "Nombre"]
        fig = px.pie(
            type_counts, names="Type", values="Nombre",
            color="Type",
            color_discrete_map={
                "Facile":  COLORS["easy_run"],
                "Soutenu": COLORS["hard_run"],
            },
            hole=0.45,
        )
        fig.update_traces(textinfo="percent+label")
        fig.update_layout(
            template=PLOTLY_TEMPLATE,
            height=320,
            margin=dict(l=0, r=0, t=10, b=0),
            showlegend=False,
        )
        st.plotly_chart(apply_glass(fig), use_container_width=True)

    with col2:
        st.markdown("#### Distance vs allure")
        has_hr = "avg_hr" in df.columns and df["avg_hr"].notna().any()
        fig = px.scatter(
            df,
            x="distance_km",
            y="pace_min_km",
            color="run_type",
            size="distance_km",
            size_max=14,
            color_discrete_map={
                "Facile":  COLORS["easy_run"],
                "Soutenu": COLORS["hard_run"],
            },
            labels={
                "distance_km": "Distance (km)",
                "pace_min_km": "Allure (min/km)",
                "run_type": "Type",
            },
            hover_data={"pace_label": True, "duration_label": True},
        )
        fig.update_layout(
            template=PLOTLY_TEMPLATE,
            height=320,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        fig = apply_glass(fig)
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

    # Stats par type de run
    st.markdown("#### Statistiques par type de run")
    stats_by_type = df.groupby("run_type").agg(
        Runs=("distance_km", "count"),
        Km_total=("distance_km", "sum"),
        Km_moyen=("distance_km", "mean"),
        Allure_moy_s=("pace_s_per_km", "mean"),
    ).reset_index()
    stats_by_type["Km_total"] = stats_by_type["Km_total"].apply(lambda x: f"{x:.1f} km")
    stats_by_type["Km_moyen"] = stats_by_type["Km_moyen"].apply(lambda x: f"{x:.2f} km")
    from src.data.processor import _fmt_pace
    stats_by_type["Allure moy."] = stats_by_type["Allure_moy_s"].apply(_fmt_pace)
    stats_by_type = stats_by_type.drop(columns=["Allure_moy_s"])
    stats_by_type.columns = ["Type", "Runs", "Km total", "Km moyen", "Allure moy."]
    st.dataframe(stats_by_type, use_container_width=True, hide_index=True)
