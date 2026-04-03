# ─────────────────────────────────────────────
#  pages/coach.py  –  Coach IA propulsé par Claude
# ─────────────────────────────────────────────

import streamlit as st
import anthropic
import pandas as pd
from src.data.processor import get_stats, get_prs, get_weekly_volume, get_goal_progress
from src.config import GOALS


def render(df: pd.DataFrame):
    st.markdown("## 🤖 Mon Coach IA")
    st.markdown("Ton coach running personnel, propulsé par Claude.")
    st.markdown("---")

    # ── Vérification clé API ──────────────────
    api_key = st.secrets.get("ANTHROPIC_API_KEY", None)
    if not api_key:
        st.error(
            "⚠️ Clé API Anthropic manquante.\n\n"
            "Va dans Streamlit Cloud → Settings → Secrets et ajoute :\n"
            "`ANTHROPIC_API_KEY = \"sk-ant-...\"`"
        )
        return

    # ── Contexte running ──────────────────────
    stats    = get_stats(df)
    prs      = get_prs(df)
    weekly   = get_weekly_volume(df)
    progress = get_goal_progress(df, prs)

    context  = _build_context(df, stats, prs, weekly, progress)

    # ── Initialisation historique chat ────────
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # ── Analyse automatique en haut ───────────
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📊 Analyse de ma semaine", use_container_width=True):
            _ask_coach(
                api_key, context,
                "Analyse ma semaine d'entraînement actuelle et donne-moi un feedback précis."
            )
    with col2:
        if st.button("🎯 Progression objectifs", use_container_width=True):
            _ask_coach(
                api_key, context,
                "Analyse ma progression vers mes objectifs 5km sub 25, 10km sub 50 et marathon. Suis-je sur la bonne trajectoire ?"
            )
    with col3:
        if st.button("📅 Plan semaine prochaine", use_container_width=True):
            _ask_coach(
                api_key, context,
                "Propose-moi un plan d'entraînement détaillé pour la semaine prochaine adapté à mon niveau et mes objectifs."
            )

    st.markdown("---")

    # ── Historique de la conversation ─────────
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Input utilisateur ─────────────────────
    if prompt := st.chat_input("Pose une question à ton coach..."):
        _ask_coach(api_key, context, prompt)


# ── Logique coach ─────────────────────────────

def _ask_coach(api_key: str, context: str, question: str):
    """Envoie une question à Claude et affiche la réponse en streaming."""

    # Ajoute le message utilisateur
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # Prépare les messages pour l'API
    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
    ]

    # Appel Claude avec streaming
    client = anthropic.Anthropic(api_key=api_key)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""

        with client.messages.stream(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=_system_prompt(context),
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                response_placeholder.markdown(full_response + "▌")

        response_placeholder.markdown(full_response)

    st.session_state.messages.append({
        "role": "assistant",
        "content": full_response
    })


def _system_prompt(context: str) -> str:
    return f"""Tu es un coach running expert, data-driven et bienveillant.
Tu analyses les données d'entraînement de ton athlète et tu lui donnes des conseils précis, personnalisés et motivants.

Ton style :
- Direct et concis, pas de blabla inutile
- Basé sur les données réelles de l'athlète
- Encourageant mais honnête
- Tu utilises des emojis avec modération
- Tu réponds toujours en français
- Tu donnes des conseils actionnables et concrets

Profil de l'athlète :
- Homme, 26 ans
- Objectifs : 5km sub 25min, 10km sub 50min, finir un marathon cette année
- Volume actuel : 15-30 km/semaine, objectif 40-50 km/semaine

Données d'entraînement actuelles :
{context}

Quand tu analyses, tu dois :
1. Te baser sur les vraies données fournies
2. Identifier les points forts et axes d'amélioration
3. Donner des recommandations concrètes et adaptées
4. Rester motivant et réaliste
"""


def _build_context(df, stats, prs, weekly, progress) -> str:
    """Construit un résumé textuel des données pour Claude."""

    # Stats générales
    ctx = f"""
=== STATISTIQUES GLOBALES ===
- Nombre total de runs : {stats['total_runs']}
- Kilomètres totaux : {stats['total_km']} km
- Km sur 7 derniers jours : {stats['km_7d']} km
- Km sur 30 derniers jours : {stats['km_30d']} km
- Allure moyenne globale : {stats['avg_pace_label']}
- Distance moyenne par run : {stats['avg_dist']} km
- Temps total de course : {stats['total_time_label']}

=== RECORDS PERSONNELS ==="""

    for label, key in [("1 km", "1km"), ("5 km", "5km"), ("10 km", "10km"),
                        ("Semi-marathon", "semi"), ("Marathon", "marathon")]:
        pr = prs.get(key)
        if pr:
            ctx += f"\n- {label} : {pr['label']} à {pr['pace']} (le {pr['date']})"
        else:
            ctx += f"\n- {label} : pas encore couru"

    # Progression objectifs
    ctx += f"""

=== PROGRESSION OBJECTIFS ===
- 5km sub 25min : {int(progress['5km'] * 100)}% atteint
- 10km sub 50min : {int(progress['10km'] * 100)}% atteint
- Marathon (préparation volume) : {int(progress['marathon'] * 100)}% prêt
- Volume hebdo cible (40km) : {int(progress['volume'] * 100)}% atteint"""

    # Volume récent (4 dernières semaines)
    if not weekly.empty:
        ctx += "\n\n=== VOLUME DES 4 DERNIÈRES SEMAINES ==="
        for _, row in weekly.tail(4).iterrows():
            ctx += f"\n- Semaine du {row['week'].strftime('%d/%m')} : {row['km']:.1f} km ({int(row['runs'])} runs)"

    # Derniers runs
    ctx += "\n\n=== 5 DERNIÈRES SORTIES ==="
    for _, row in df.head(5).iterrows():
        ctx += (
            f"\n- {row['date'].strftime('%d/%m/%Y')} : "
            f"{row['distance_km']:.2f} km en {row['duration_label']} "
            f"à {row['pace_label']} [{row['run_type']}]"
        )

    return ctx
