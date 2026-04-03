# ─────────────────────────────────────────────
#  pages/objectifs.py  –  Suivi des objectifs
# ─────────────────────────────────────────────

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from src.data.processor import get_prs, get_goal_progress, get_weekly_volume
from src.config import COLORS, GOALS, PLOTLY_TEMPLATE


def render(df: pd.DataFrame):
    st.markdown("## 🎯 Objectifs")
    st.markdown("Ta progression vers tes objectifs de course.")
    st.markdown("---")

    prs      = get_prs(df)
    progress = get_goal_progress(df, prs)
    weekly   = get_weekly_volume(df)

    # ── Objectif 5 km sub 25 ─────────────────
    st.markdown("### 🔵 5 km en moins de 25 min")
    _goal_block(
        pr=prs.get("5km"),
        target_s=GOALS["5k_target_seconds"],
        target_label="25:00",
        progress=progress["5km"],
        icon="🔵",
        tip="Intègre 1 séance de fractionné par semaine (ex: 5×1km à allure cible).",
    )

    st.markdown("---")

    # ── Objectif 10 km sub 50 ────────────────
    st.markdown("### 🔴 10 km en moins de 50 min")
    _goal_block(
        pr=prs.get("10km"),
        target_s=GOALS["10k_target_seconds"],
        target_label="50:00",
        progress=progress["10km"],
        icon="🔴",
        tip="Ajoute une sortie tempo de 8–10 km à allure cible (5:00 /km) chaque semaine.",
    )

    st.markdown("---")

    # ── Objectif Marathon ────────────────────
    st.markdown("### ⭐ Finir un marathon cette année")
    _marathon_block(df, prs, progress, weekly)

    st.markdown("---")

    # ── Objectif volume hebdo ────────────────
    st.markdown("### 📈 Volume cible : 40–50 km/semaine")
    _volume_block(weekly, progress)


# ── Blocs de rendu ───────────────────────────

def _goal_block(pr, target_s, target_label, progress, icon, tip):
    col1, col2 = st.columns([3, 1])

    with col1:
        # Barre de progression
        pct = int(progress * 100)
        color = _progress_color(progress)
        st.markdown(f"""
        <div class="goal-block">
            <div class="goal-bar-bg">
                <div class="goal-bar" style="width:{pct}%; background:{color};">
                    <span class="goal-pct">{pct}%</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"*💡 {tip}*")

    with col2:
        if pr:
            delta_s = pr["time_s"] - target_s
            delta_label = _fmt_delta(delta_s)
            status = "✅ Objectif atteint !" if delta_s <= 0 else f"Écart : **{delta_label}**"
            st.markdown(f"""
            <div class="pr-mini-card">
                <div>🏆 PR actuel</div>
                <div class="pr-mini-time">{pr['label']}</div>
                <div class="pr-mini-pace">{pr['pace']}</div>
                <div>Objectif : {target_label}</div>
                <div>{status}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="pr-mini-card pr-empty">
                <div>Aucun PR enregistré</div>
                <div style="font-size:0.85rem;margin-top:8px;">
                    Lance-toi sur cette distance !
                </div>
            </div>
            """, unsafe_allow_html=True)


def _marathon_block(df, prs, progress, weekly):
    col1, col2, col3 = st.columns(3)

    # Volume max hebdo
    max_weekly = weekly["km"].max() if not weekly.empty else 0
    avg_recent = weekly.tail(4)["km"].mean() if not weekly.empty else 0

    with col1:
        st.metric("Volume max (1 semaine)", f"{max_weekly:.1f} km")
        st.caption("Objectif avant marathon : ~60 km/sem")

    with col2:
        st.metric("Moyenne 4 dernières semaines", f"{avg_recent:.1f} km")
        st.caption("Objectif : 40+ km/sem en continu")

    pr_semi = prs.get("semi")
    pr_mara = prs.get("marathon")
    with col3:
        if pr_mara:
            st.metric("PR Marathon", pr_mara["label"])
        elif pr_semi:
            st.metric("PR Semi-marathon", pr_semi["label"])
            projected = pr_semi["time_s"] * 2.1   # règle du pouce
            h = int(projected // 3600)
            m = int((projected % 3600) // 60)
            st.caption(f"Marathon projeté ≈ {h}h{m:02d}m")
        else:
            st.info("Pas encore de PR semi ou marathon.")

    # Barre de progression marathon
    pct = int(progress["marathon"] * 100)
    color = _progress_color(progress["marathon"])
    st.markdown(f"""
    <div class="goal-block" style="margin-top:12px;">
        <div class="goal-bar-bg">
            <div class="goal-bar" style="width:{pct}%; background:{color};">
                <span class="goal-pct">{pct}%</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("*💡 Pour finir un marathon, vise 60 km/sem sur 8 semaines avant la course. Plan long run : +1–2 km/semaine.*")


def _volume_block(weekly, progress):
    col1, col2 = st.columns([3, 1])

    with col1:
        if not weekly.empty:
            recent = weekly.tail(8)
            fig = go.Figure()
            colors = [
                COLORS["primary"] if k >= GOALS["weekly_km_target"] else COLORS["secondary"]
                for k in recent["km"]
            ]
            fig.add_trace(go.Bar(
                x=recent["week"].dt.strftime("%d %b"),
                y=recent["km"],
                marker_color=colors,
                hovertemplate="<b>%{x}</b><br>%{y:.1f} km<extra></extra>",
            ))
            fig.add_hline(
                y=GOALS["weekly_km_target"],
                line_dash="dot",
                line_color=COLORS["warning"],
                annotation_text=f"Cible {GOALS['weekly_km_target']} km",
            )
            fig.update_layout(
                template=PLOTLY_TEMPLATE,
                height=250,
                margin=dict(l=0, r=0, t=10, b=0),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        pct = int(progress["volume"] * 100)
        color = _progress_color(progress["volume"])
        st.markdown(f"""
        <div class="pr-mini-card">
            <div>Progression volume</div>
            <div class="pr-mini-time">{pct}%</div>
            <div>vers {GOALS['weekly_km_target']} km/sem</div>
        </div>
        """, unsafe_allow_html=True)


# ── Helpers ──────────────────────────────────

def _progress_color(p: float) -> str:
    if p >= 1.0:
        return COLORS["success"]
    elif p >= 0.7:
        return COLORS["primary"]
    elif p >= 0.4:
        return COLORS["warning"]
    return COLORS["secondary"]


def _fmt_delta(delta_s: float) -> str:
    delta_s = abs(int(delta_s))
    m = delta_s // 60
    s = delta_s % 60
    return f"{m}:{s:02d}"
