# ─────────────────────────────────────────────
#  app.py  –  Point d'entrée Running Cockpit
# ─────────────────────────────────────────────

import streamlit as st
from pathlib import Path

from src.config import APP_TITLE, APP_ICON
from src.data.loader import load_data
from src.data.processor import process_data
import src.pages.dashboard   as page_dashboard
import src.pages.runs        as page_runs
import src.pages.performance as page_performance
import src.pages.objectifs   as page_objectifs
import src.pages.analyse     as page_analyse
import src.pages.coach       as page_coach

# ── Configuration page ────────────────────────
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS personnalisé ──────────────────────────
css_path = Path(__file__).parent / "assets" / "style.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────
with st.sidebar:
    st.markdown(f"# {APP_ICON} {APP_TITLE}")
    st.markdown("*Ton cockpit running personnel*")
    st.markdown("---")

    page = st.radio(
        "Navigation",
        options=[
            "📊  Dashboard",
            "🗂️  Runs",
            "🏆  Performance",
            "🎯  Objectifs",
            "📉  Analyse",
            "🤖  Coach IA",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("### 📁 Importer mes données")
    st.caption("CSV export Strava ou format normalisé")
    uploaded = st.file_uploader("", type=["csv"], label_visibility="collapsed")

    from src.data.loader import STRAVA_PATH
    if uploaded:
        st.success(f"✅ Fichier chargé : {uploaded.name}")
    elif STRAVA_PATH.exists():
        st.success("✅ Données Strava chargées")
    else:
        st.info("📂 Données de démo actives")

    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.72rem;color:#4A5568;text-align:center'>"
        "V1 · Données locales uniquement<br>"
        "Prochainement : sommeil & récupération"
        "</div>",
        unsafe_allow_html=True,
    )

# ── Chargement des données ────────────────────
with st.spinner("Chargement des données…"):
    df_raw = load_data(uploaded)

if df_raw is None or df_raw.empty:
    st.error(
        "⚠️ Aucune donnée disponible.\n\n"
        "Importe ton fichier CSV via le panneau latéral, "
        "ou assure-toi que `data/sample_activities.csv` existe."
    )
    st.stop()

df = process_data(df_raw)

# ── Routing des pages ─────────────────────────
if   "Dashboard"   in page: page_dashboard.render(df)
elif "Runs"        in page: page_runs.render(df)
elif "Performance" in page: page_performance.render(df)
elif "Objectifs"   in page: page_objectifs.render(df)
elif "Analyse"     in page: page_analyse.render(df)
elif "Coach"       in page: page_coach.render(df)
