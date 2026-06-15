# ─────────────────────────────────────────────
#  pages/performance.py  –  Records & tendances
# ─────────────────────────────────────────────

import streamlit as st
import pandas as pd
import numpy as np
from src.data.processor import get_prs, get_pace_trend
from src.ui import css_bar_chart, css_line_chart


def render(df: pd.DataFrame):
    st.markdown("## 🏆 Performance")
    st.markdown("Tes records personnels et l'évolution de ta forme.")
    st.markdown("---")

    prs   = get_prs(df)
    trend = get_pace_trend(df, n_weeks=16)

    # ── Records personnels (grille responsive) ──
    st.markdown("#### 🥇 Records personnels")
    pr_labels = {
        "1km":      ("1 km",       "🔵"),
        "5km":      ("5 km",       "🟠"),
        "10km":     ("10 km",      "🔴"),
        "semi":     ("Semi-mara.", "🟣"),
        "marathon": ("Marathon",   "⭐"),
    }
    cards = ""
    for key, (label, icon) in pr_labels.items():
        pr = prs.get(key)
        if pr:
            cards += (
                f'<div class="pr-card">'
                f'<div class="pr-icon">{icon}</div>'
                f'<div class="pr-distance">{label}</div>'
                f'<div class="pr-time">{pr["label"]}</div>'
                f'<div class="pr-pace">{pr["pace"]}</div>'
                f'<div class="pr-date">{pr["date"]}</div>'
                f'</div>'
            )
        else:
            cards += (
                f'<div class="pr-card pr-empty">'
                f'<div class="pr-icon">{icon}</div>'
                f'<div class="pr-distance">{label}</div>'
                f'<div class="pr-time">—</div>'
                f'<div class="pr-date">Pas encore</div>'
                f'</div>'
            )
    st.markdown(f'<div class="pr-grid">{cards}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Tendance d'allure ─────────────────────
    col_trend, col_dist = st.columns([3, 2])

    with col_trend:
        st.markdown("#### 📈 Évolution de l'allure (16 semaines)")
        if not trend.empty:
            _pace_trend_chart(trend)
        else:
            st.info("Pas assez de données.")

    with col_dist:
        st.markdown("#### 📊 Distribution des distances")
        _dist_histogram(df)

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
    weeks = trend["week"]
    vals = trend["avg_pace_min"].tolist()
    labels = [w.strftime("%d %b") for w in weeks]

    trend_line = None
    if len(trend) >= 3:
        x_num = (weeks - weeks.min()).dt.days.to_numpy()
        p = np.poly1d(np.polyfit(x_num, vals, 1))
        trend_line = [float(p(x)) for x in x_num]

    css_line_chart(
        labels=labels,
        values=vals,
        trend=trend_line,
        accent="orange",
        unit="min/km",
        hint="↓ plus rapide",
        value_fmt=_fmt_pace_min,
    )


def _fmt_pace_min(v: float) -> str:
    total = round(v * 60)
    return f"{total // 60}:{total % 60:02d}"


def _dist_histogram(df: pd.DataFrame):
    dist = df["distance_km"].dropna()
    if dist.empty:
        st.info("Pas de données.")
        return
    counts, edges = np.histogram(dist, bins=8)
    labels = [f"{edges[i]:.0f}–{edges[i + 1]:.0f}" for i in range(len(counts))]
    css_bar_chart(
        labels=labels,
        values=counts.tolist(),
        accent="blue",
        decimals=0,
        caption="Nombre de sorties par tranche de distance (km)",
    )
