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
            fig = _bar_chart(
                x=weekly["week"].dt.strftime("%d %b"),
                y=weekly["km"],
                color=COLORS["primary"],
                ylabel="km",
                hover_label="km",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### Volume mensuel")
        if not monthly.empty:
            fig = _bar_chart(
                x=monthly["month_label"],
                y=monthly["km"],
                color=COLORS["secondary"],
                ylabel="km",
                hover_label="km",
            )
            st.plotly_chart(fig, use_container_width=True)

    # Évolution de l'allure moyenne par mois
    st.markdown("#### Allure moyenne mensuelle")
    if not monthly.empty:
        fig = _pace_monthly_chart(monthly)
        st.plotly_chart(fig, use_container_width=True)


def _pace_monthly_chart(monthly):
    monthly = monthly.copy()
    monthly["avg_pace_min"] = monthly["avg_pace_s"] / 60

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly["month_label"],
        y=monthly["avg_pace_min"],
        mode="lines+markers",
        line=dict(color=COLORS["primary"], width=2.5),
        marker=dict(size=8),
        hovertemplate="<b>%{x}</b><br>%{y:.2f} min/km<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=280,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis_title="min/km (↓ = plus rapide)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ── Onglet Fréquence ──────────────────────────

def _tab_frequence(df, weekly):
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### Runs par semaine")
        if not weekly.empty:
            fig = _bar_chart(
                x=weekly["week"].dt.strftime("%d %b"),
                y=weekly["runs"],
                color=COLORS["warning"],
                ylabel="Runs",
                hover_label="runs",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### Jour de la semaine préféré")
        dow_counts = df["date"].dt.day_name()
        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        fr_names = {"Monday": "Lundi", "Tuesday": "Mardi", "Wednesday": "Mercredi",
                    "Thursday": "Jeudi", "Friday": "Vendredi", "Saturday": "Samedi", "Sunday": "Dimanche"}
        dow_df = dow_counts.value_counts().reindex(order, fill_value=0).reset_index()
        dow_df.columns = ["day_en", "count"]
        dow_df["day_fr"] = dow_df["day_en"].map(fr_names)
        fig = px.bar(
            dow_df, x="day_fr", y="count",
            color_discrete_sequence=[COLORS["secondary"]],
            labels={"day_fr": "", "count": "Runs"},
        )
        fig.update_layout(
            template=PLOTLY_TEMPLATE,
            height=300,
            margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)

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
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


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
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)

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
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(
            template=PLOTLY_TEMPLATE,
            height=320,
            margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
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


# ── Helper générique ──────────────────────────

def _bar_chart(x, y, color, ylabel, hover_label):
    fig = go.Figure(go.Bar(
        x=x, y=y,
        marker_color=color,
        hovertemplate=f"<b>%{{x}}</b><br>%{{y:.1f}} {hover_label}<extra></extra>",
    ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=280,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis_title=ylabel,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig
