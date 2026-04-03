# ─────────────────────────────────────────────
#  pages/coach.py  –  Coach IA propulsé par Claude
# ─────────────────────────────────────────────

import streamlit as st
import anthropic
import pandas as pd
import plotly.graph_objects as go
import json
import re
from datetime import datetime, timedelta
from src.data.processor import get_stats, get_prs, get_weekly_volume, get_goal_progress
from src.config import GOALS, COLORS, PLOTLY_TEMPLATE


def render(df: pd.DataFrame):
    st.markdown("## 🤖 Coach IA")
    st.markdown("Ton coach running personnel, propulsé par Claude.")
    st.markdown("---")

    api_key = st.secrets.get("ANTHROPIC_API_KEY", None)
    if not api_key:
        st.error("⚠️ Clé API Anthropic manquante dans les Secrets Streamlit.")
        return

    stats    = get_stats(df)
    prs      = get_prs(df)
    weekly   = get_weekly_volume(df)
    progress = get_goal_progress(df, prs)
    context  = _build_context(df, stats, prs, weekly, progress)

    # ── Onglets principaux ────────────────────
    tab_bilan, tab_plan, tab_projection, tab_chat = st.tabs([
        "📋 Bilan semaine",
        "📅 Plan semaine",
        "📈 Projections",
        "💬 Chat coach",
    ])

    with tab_bilan:
        _tab_bilan(api_key, context, stats, weekly)

    with tab_plan:
        _tab_plan(api_key, context)

    with tab_projection:
        _tab_projection(api_key, context, prs, progress, weekly)

    with tab_chat:
        _tab_chat(api_key, context)


# ══════════════════════════════════════════════
#  ONGLET 1 – Bilan de la semaine
# ══════════════════════════════════════════════

def _tab_bilan(api_key, context, stats, weekly):
    st.markdown("#### 📋 Bilan de ta semaine d'entraînement")

    col_btn, col_date = st.columns([2, 1])
    with col_btn:
        generate = st.button("🔄 Générer le bilan", use_container_width=True, key="btn_bilan")
    with col_date:
        st.caption(f"Semaine du {(datetime.now() - timedelta(days=7)).strftime('%d/%m')} au {datetime.now().strftime('%d/%m/%Y')}")

    if generate or "bilan_data" in st.session_state:
        if generate:
            with st.spinner("Claude analyse ta semaine..."):
                result = _call_claude_json(api_key, context, _prompt_bilan())
                if result:
                    st.session_state["bilan_data"] = result

        data = st.session_state.get("bilan_data")
        if data:
            _render_bilan(data, stats, weekly)


def _render_bilan(data: dict, stats, weekly):
    # ── Score global ──────────────────────────
    score = data.get("score", 3)
    score_emoji = ["😴", "😐", "🙂", "💪", "🔥"][min(score - 1, 4)]
    note_label = ["Semaine difficile", "Semaine correcte", "Bonne semaine", "Très bonne semaine", "Semaine exceptionnelle"][min(score - 1, 4)]

    st.markdown(f"""
    <div style="background:#1A1F2E;border:1px solid #2D3748;border-radius:12px;padding:20px;text-align:center;margin-bottom:16px;">
        <div style="font-size:3rem;">{score_emoji}</div>
        <div style="font-size:1.5rem;font-weight:700;color:#F7FAFC;">{note_label}</div>
        <div style="color:#8892A4;font-size:0.9rem;margin-top:4px;">Score : {score}/5</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Résumé coach ──────────────────────────
    st.markdown(f"**💬 Analyse du coach :** {data.get('resume', '')}")
    st.markdown("")

    # ── Points forts / axes d'amélioration ───
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**✅ Points forts**")
        for point in data.get("points_forts", []):
            st.markdown(f"- {point}")

    with col2:
        st.markdown("**🎯 À améliorer**")
        for point in data.get("axes_amelioration", []):
            st.markdown(f"- {point}")

    st.markdown("")

    # ── Métriques semaine ─────────────────────
    st.markdown("**📊 Ta semaine en chiffres**")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Volume", f"{stats['km_7d']} km")
    c2.metric("Runs", f"{len([r for r in [stats['km_7d']] if r > 0])} sorties")
    c3.metric("Allure moy.", stats['avg_pace_label'])

    if not weekly.empty:
        last_week = weekly.tail(1)["km"].values[0]
        prev_week = weekly.tail(2).head(1)["km"].values[0] if len(weekly) >= 2 else 0
        delta = round(last_week - prev_week, 1)
        c4.metric("vs semaine préc.", f"{last_week:.1f} km", f"{delta:+.1f} km")

    st.markdown("")
    st.markdown(f"**💡 Recommandation clé :** {data.get('recommandation', '')}")


# ══════════════════════════════════════════════
#  ONGLET 2 – Plan de la semaine prochaine
# ══════════════════════════════════════════════

def _tab_plan(api_key, context):
    st.markdown("#### 📅 Plan d'entraînement – Semaine prochaine")

    generate = st.button("🔄 Générer mon plan", use_container_width=True, key="btn_plan")

    if generate or "plan_data" in st.session_state:
        if generate:
            with st.spinner("Claude prépare ton plan personnalisé..."):
                result = _call_claude_json(api_key, context, _prompt_plan())
                if result:
                    st.session_state["plan_data"] = result

        data = st.session_state.get("plan_data")
        if data:
            _render_plan(data)


def _render_plan(data: dict):
    st.markdown(f"**🎯 Objectif de la semaine :** {data.get('objectif_semaine', '')}")
    st.markdown(f"**📏 Volume cible :** {data.get('volume_total', '')} km")
    st.markdown("")

    jours = data.get("jours", [])
    type_colors = {
        "Repos":     "#2D3748",
        "Récup":     "#2E4A3E",
        "Facile":    "#2E4A3E",
        "Tempo":     "#4A3B1E",
        "Fractionné": "#4A1E1E",
        "Long":      "#1E3A4A",
        "Course":    "#4A1E4A",
    }

    for jour in jours:
        type_run  = jour.get("type", "Repos")
        color_bg  = type_colors.get(type_run, "#2D3748")
        distance  = jour.get("distance", "")
        desc      = jour.get("description", "")
        allure    = jour.get("allure_cible", "")
        jour_nom  = jour.get("jour", "")

        dist_str  = f"{distance} km" if distance else "—"
        allure_str = f" · {allure}" if allure else ""

        st.markdown(f"""
        <div style="background:{color_bg};border-radius:10px;padding:14px 18px;margin-bottom:8px;display:flex;align-items:center;gap:16px;">
            <div style="min-width:80px;font-weight:700;color:#F7FAFC;">{jour_nom}</div>
            <div style="min-width:90px;">
                <span style="background:#FC4C02;color:white;border-radius:6px;padding:3px 8px;font-size:0.75rem;font-weight:600;">{type_run}</span>
            </div>
            <div style="min-width:60px;color:#FC4C02;font-weight:600;">{dist_str}{allure_str}</div>
            <div style="color:#CBD5E0;font-size:0.88rem;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")
    seance_cle = data.get("seance_cle", "")
    if seance_cle:
        st.info(f"⭐ **Séance clé de la semaine :** {seance_cle}")

    conseil = data.get("conseil_global", "")
    if conseil:
        st.markdown(f"**💡 Conseil du coach :** {conseil}")


# ══════════════════════════════════════════════
#  ONGLET 3 – Projections & objectifs
# ══════════════════════════════════════════════

def _tab_projection(api_key, context, prs, progress, weekly):
    st.markdown("#### 📈 Projections vers tes objectifs")

    generate = st.button("🔄 Générer mes projections", use_container_width=True, key="btn_proj")

    if generate or "proj_data" in st.session_state:
        if generate:
            with st.spinner("Claude calcule tes projections..."):
                result = _call_claude_json(api_key, context, _prompt_projection())
                if result:
                    st.session_state["proj_data"] = result

        data = st.session_state.get("proj_data")
        if data:
            _render_projection(data, prs, progress, weekly)


def _render_projection(data: dict, prs, progress, weekly):
    objectifs = data.get("objectifs", [])

    for obj in objectifs:
        nom        = obj.get("nom", "")
        statut     = obj.get("statut", "En cours")
        pct        = obj.get("progression", 0)
        date_est   = obj.get("date_estimee", "À déterminer")
        ecart      = obj.get("ecart_actuel", "")
        action     = obj.get("action_cle", "")
        on_track   = obj.get("on_track", True)

        color = COLORS["success"] if statut == "Atteint" else (COLORS["primary"] if on_track else COLORS["warning"])
        icon  = "✅" if statut == "Atteint" else ("🟠" if on_track else "⚠️")

        st.markdown(f"""
        <div style="background:#1A1F2E;border:1px solid #2D3748;border-radius:12px;padding:18px;margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                <div style="font-size:1.1rem;font-weight:700;color:#F7FAFC;">{icon} {nom}</div>
                <div style="color:{color};font-weight:600;">{statut}</div>
            </div>
            <div style="background:#2D3748;border-radius:30px;height:22px;overflow:hidden;margin-bottom:10px;">
                <div style="width:{pct}%;height:100%;background:{color};border-radius:30px;display:flex;align-items:center;justify-content:flex-end;padding-right:8px;">
                    <span style="color:white;font-size:0.75rem;font-weight:700;">{pct}%</span>
                </div>
            </div>
            <div style="display:flex;gap:24px;font-size:0.85rem;color:#A0AEC0;">
                <span>📅 Date estimée : <b style="color:#F7FAFC;">{date_est}</b></span>
                {'<span>⏱ Écart : <b style="color:#F7FAFC;">' + ecart + '</b></span>' if ecart else ''}
            </div>
            {'<div style="margin-top:10px;font-size:0.85rem;color:#CBD5E0;">💡 ' + action + '</div>' if action else ''}
        </div>
        """, unsafe_allow_html=True)

    # Graphique projection volume
    if not weekly.empty and len(weekly) >= 3:
        st.markdown("#### Projection du volume hebdomadaire")
        _chart_projection_volume(weekly, data)

    analyse = data.get("analyse_globale", "")
    if analyse:
        st.markdown(f"**🤖 Analyse globale :** {analyse}")


def _chart_projection_volume(weekly, data):
    import numpy as np
    recent = weekly.tail(8).copy()
    x_num  = list(range(len(recent)))
    y_vals = recent["km"].tolist()

    z = np.polyfit(x_num, y_vals, 1)
    p = np.poly1d(z)

    # Projection 8 semaines
    future_x   = list(range(len(recent), len(recent) + 8))
    future_y   = [max(0, p(x)) for x in future_x]
    future_dates = [recent["week"].iloc[-1] + timedelta(weeks=i+1) for i in range(8)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=recent["week"].dt.strftime("%d %b"),
        y=recent["km"],
        name="Volume réel",
        marker_color=COLORS["primary"],
    ))
    fig.add_trace(go.Scatter(
        x=[d.strftime("%d %b") for d in future_dates],
        y=future_y,
        name="Projection",
        mode="lines+markers",
        line=dict(color=COLORS["warning"], dash="dot", width=2),
        marker=dict(size=6),
    ))
    fig.add_hline(
        y=GOALS["weekly_km_target"],
        line_dash="dot",
        line_color=COLORS["success"],
        annotation_text=f"Objectif {GOALS['weekly_km_target']} km",
    )
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=300,
        margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════
#  ONGLET 4 – Chat libre
# ══════════════════════════════════════════════

def _tab_chat(api_key, context):
    st.markdown("#### 💬 Pose une question à ton coach")

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ex: Suis-je prêt pour un semi-marathon ?"):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        messages = [{"role": m["role"], "content": m["content"]}
                    for m in st.session_state.chat_messages]

        client = anthropic.Anthropic(api_key=api_key)
        with st.chat_message("assistant"):
            placeholder   = st.empty()
            full_response = ""
            with client.messages.stream(
                model="claude-haiku-4-5",
                max_tokens=1024,
                system=_system_prompt(context),
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)

        st.session_state.chat_messages.append({
            "role": "assistant", "content": full_response
        })


# ══════════════════════════════════════════════
#  Prompts structurés (JSON)
# ══════════════════════════════════════════════

def _prompt_bilan() -> str:
    return """Analyse les données d'entraînement de cette semaine et réponds UNIQUEMENT en JSON valide avec cette structure exacte :
{
  "score": <entier 1-5>,
  "resume": "<résumé en 2 phrases>",
  "points_forts": ["<point 1>", "<point 2>", "<point 3>"],
  "axes_amelioration": ["<axe 1>", "<axe 2>"],
  "recommandation": "<une recommandation concrète et actionnable>"
}"""


def _prompt_plan() -> str:
    return """Génère un plan d'entraînement pour la semaine prochaine adapté au profil et aux objectifs de l'athlète.
Réponds UNIQUEMENT en JSON valide avec cette structure exacte :
{
  "objectif_semaine": "<objectif principal>",
  "volume_total": <nombre km>,
  "jours": [
    {"jour": "Lundi", "type": "<Repos|Récup|Facile|Tempo|Fractionné|Long>", "distance": <km ou null>, "description": "<détail>", "allure_cible": "<ex: 5:30/km ou null>"},
    {"jour": "Mardi", ...},
    {"jour": "Mercredi", ...},
    {"jour": "Jeudi", ...},
    {"jour": "Vendredi", ...},
    {"jour": "Samedi", ...},
    {"jour": "Dimanche", ...}
  ],
  "seance_cle": "<description de la séance la plus importante>",
  "conseil_global": "<conseil du coach pour cette semaine>"
}"""


def _prompt_projection() -> str:
    return """Analyse la progression de l'athlète et projette ses performances futures.
Réponds UNIQUEMENT en JSON valide avec cette structure exacte :
{
  "objectifs": [
    {
      "nom": "5km sub 25min",
      "statut": "<Atteint|En bonne voie|À risque>",
      "progression": <0-100>,
      "on_track": <true|false>,
      "date_estimee": "<mois année ex: Juin 2026>",
      "ecart_actuel": "<ex: 1:23 de retard ou Objectif atteint>",
      "action_cle": "<action concrète pour progresser>"
    },
    {"nom": "10km sub 50min", ...},
    {"nom": "Marathon 2026", ...},
    {"nom": "Volume 40km/semaine", ...}
  ],
  "analyse_globale": "<analyse globale de la trajectoire en 2-3 phrases>"
}"""


# ══════════════════════════════════════════════
#  Helpers API
# ══════════════════════════════════════════════

def _call_claude_json(api_key: str, context: str, prompt: str) -> dict | None:
    """Appelle Claude et retourne un dict JSON parsé."""
    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2048,
            system=_system_prompt(context),
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        # Extraction du JSON même si Claude ajoute du texte autour
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        st.error(f"Erreur API Claude : {e}")
    return None


def _system_prompt(context: str) -> str:
    return f"""Tu es un coach running expert, data-driven et bienveillant.
Tu analyses les données réelles de ton athlète pour donner des conseils précis et personnalisés.

Profil :
- Homme, 26 ans
- Objectifs : 5km sub 25min, 10km sub 50min, finir un marathon cette année
- Volume actuel : 15-30 km/sem → objectif 40-50 km/sem

Données d'entraînement :
{context}

Règles :
- Base-toi TOUJOURS sur les vraies données fournies
- Sois direct, concis et motivant
- Donne des conseils actionnables et réalistes
- Réponds toujours en français
"""


def _build_context(df, stats, prs, weekly, progress) -> str:
    ctx = f"""
=== STATS GLOBALES ===
Runs totaux: {stats['total_runs']} | Km totaux: {stats['total_km']} km
Km 7 jours: {stats['km_7d']} km | Km 30 jours: {stats['km_30d']} km
Allure moyenne: {stats['avg_pace_label']} | Distance moyenne: {stats['avg_dist']} km

=== RECORDS PERSONNELS ==="""
    for label, key in [("1km","1km"),("5km","5km"),("10km","10km"),("Semi","semi"),("Marathon","marathon")]:
        pr = prs.get(key)
        ctx += f"\n{label}: {pr['label']} à {pr['pace']} ({pr['date']})" if pr else f"\n{label}: pas encore couru"

    ctx += f"""

=== PROGRESSION OBJECTIFS ===
5km sub 25min: {int(progress['5km']*100)}% | 10km sub 50min: {int(progress['10km']*100)}%
Marathon: {int(progress['marathon']*100)}% | Volume 40km/sem: {int(progress['volume']*100)}%

=== VOLUME 4 DERNIÈRES SEMAINES ==="""
    if not weekly.empty:
        for _, r in weekly.tail(4).iterrows():
            ctx += f"\nSemaine {r['week'].strftime('%d/%m')}: {r['km']:.1f} km ({int(r['runs'])} runs)"

    ctx += "\n\n=== 5 DERNIÈRES SORTIES ==="
    for _, r in df.head(5).iterrows():
        ctx += f"\n{r['date'].strftime('%d/%m/%Y')}: {r['distance_km']:.2f}km en {r['duration_label']} à {r['pace_label']} [{r['run_type']}]"

    return ctx
