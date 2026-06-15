# ─────────────────────────────────────────────
#  app.py  –  Point d'entrée Running Cockpit (mobile-first)
# ─────────────────────────────────────────────

import hmac

import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

from src.config import APP_TITLE, APP_ICON
from src.data.loader import load_data, STRAVA_PATH
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
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CSS personnalisé ──────────────────────────
css_path = Path(__file__).parent / "assets" / "style.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


# ── Accès protégé par mot de passe ────────────
#  Le mot de passe se définit dans les Secrets Streamlit (clé `app_password`).
#  S'il n'est pas configuré (ex. dev local), l'accès reste libre.
def _check_password() -> bool:
    try:
        expected = st.secrets.get("app_password", "")
    except Exception:
        expected = ""
    if not expected:
        return True  # aucun mot de passe configuré → accès libre (local)

    if st.session_state.get("auth_ok"):
        return True

    def _verify():
        if hmac.compare_digest(st.session_state.get("pwd_input", ""), str(expected)):
            st.session_state["auth_ok"] = True
            st.session_state.pop("pwd_input", None)
        else:
            st.session_state["auth_ok"] = False

    st.markdown("## 🔒 Running Cockpit")
    st.text_input("Mot de passe", type="password", key="pwd_input", on_change=_verify)
    if st.session_state.get("auth_ok") is False:
        st.error("Mot de passe incorrect.")
    return False


if not _check_password():
    st.stop()


# ── PWA : "Ajouter à l'écran d'accueil" (plein écran iOS/Android) ──
components.html(
    """
    <script>
    const head = window.parent.document.head;
    const metas = {
        'theme-color': '#0E1117',
        'apple-mobile-web-app-capable': 'yes',
        'mobile-web-app-capable': 'yes',
        'apple-mobile-web-app-status-bar-style': 'black-translucent',
        'apple-mobile-web-app-title': 'Running Cockpit'
    };
    for (const [name, content] of Object.entries(metas)) {
        if (!head.querySelector(`meta[name="${name}"]`)) {
            const m = document.createElement('meta');
            m.name = name; m.content = content;
            head.appendChild(m);
        }
    }
    </script>
    """,
    height=0,
)

# ── Navigation (état) ─────────────────────────
PAGES = [
    ("dashboard",   "📊", "Dashboard"),
    ("runs",        "🗂️", "Runs"),
    ("performance", "🏆", "Performance"),
    ("objectifs",   "🎯", "Objectifs"),
    ("analyse",     "📉", "Analyse"),
    ("coach",       "🤖", "Coach IA"),
]

# État de nav : l'URL (?page=…) sert seulement au deep-link initial ;
# ensuite la navigation passe par des reruns (pas de rechargement).
VALID_PAGES = {key for key, _, _ in PAGES}
if "page" not in st.session_state:
    _qp_page = st.query_params.get("page")
    st.session_state.page = _qp_page if _qp_page in VALID_PAGES else "dashboard"

# ── Import de données (expander discret en haut) ──
with st.expander("📁  Importer mes données Strava", expanded=False):
    st.caption("CSV export Strava ou format normalisé")
    uploaded = st.file_uploader("Fichier CSV", type=["csv"], label_visibility="collapsed")
    if uploaded:
        st.success(f"✅ Fichier chargé : {uploaded.name}")
    elif STRAVA_PATH.exists():
        st.success("✅ Données Strava chargées")
    else:
        st.info("📂 Données de démo actives")

# ── Chargement des données ────────────────────
with st.spinner("Chargement des données…"):
    df_raw = load_data(uploaded)

if df_raw is None or df_raw.empty:
    st.error(
        "⚠️ Aucune donnée disponible.\n\n"
        "Importe ton fichier CSV via le panneau ci-dessus, "
        "ou assure-toi que `data/sample_activities.csv` existe."
    )
    st.stop()

df = process_data(df_raw)

# ── Boutons de nav cachés : cliqués par le JS de la barre HTML ──
#  Un clic déclenche un rerun Streamlit (websocket, pas de rechargement) →
#  changement de page instantané, fluide comme une app native.
with st.container(key="navbtns"):
    for _key, _, _label in PAGES:
        if st.button(_label, key=f"navbtn_{_key}"):
            st.session_state.page = _key

# ── Routing des pages ─────────────────────────
RENDERERS = {
    "dashboard":   page_dashboard.render,
    "runs":        page_runs.render,
    "performance": page_performance.render,
    "objectifs":   page_objectifs.render,
    "analyse":     page_analyse.render,
    "coach":       page_coach.render,
}
RENDERERS[st.session_state.page](df)

# ── Barre de navigation fixe en bas (HTML pur, contrôle total du markup) ──
_links = "".join(
    f'<div class="navlink{" active" if st.session_state.page == key else ""}" '
    f'data-page="{key}" title="{label}">{icon}</div>'
    for key, icon, label in PAGES
)
st.markdown(f'<div class="bottomnav">{_links}</div>', unsafe_allow_html=True)

# ── Glissé haptique sur la barre de nav ───────
#  Le doigt glissé survole les menus (aperçu + vibration) ; au relâchement on
#  clique le bouton Streamlit caché correspondant → rerun instantané sans
#  rechargement. Le code tourne dans le frame parent (non sandboxé) : on y
#  injecte un <script> pour accéder aux boutons cachés et les .click().
components.html(
    """
    <script>
    (function () {
        const p = window.parent;
        if (p.__navSwipeInstalled) { return; }   // une seule installation
        p.__navSwipeInstalled = true;

        const topScript = function () {
            // iOS n'a pas navigator.vibrate. Hack Safari 17.4+ : basculer un
            // <input type="checkbox" switch> invisible réveille le Taptic Engine.
            let hsw = null;
            function ensureSwitch() {
                if (hsw) { return hsw; }
                const label = document.createElement('label');
                label.setAttribute('aria-hidden', 'true');
                label.style.cssText = 'position:fixed;left:-9999px;top:0;width:1px;height:1px;opacity:0;pointer-events:none;';
                hsw = document.createElement('input');
                hsw.type = 'checkbox';
                hsw.setAttribute('switch', '');
                label.appendChild(hsw);
                document.body.appendChild(label);
                return hsw;
            }
            function vibrate(ms) {
                try { navigator.vibrate && navigator.vibrate(ms); } catch (e) {}
                try { const s = ensureSwitch(); s.checked = !s.checked; s.click(); } catch (e) {}
            }

            // Bascule de page = clic sur le bouton Streamlit caché → rerun.
            const go = (pageKey) => {
                if (!pageKey) { return; }
                const btn = document.querySelector('.st-key-navbtn_' + pageKey + ' button');
                if (btn) { btn.click(); }
            };

            let current = null;
            const linkAt = (x, y) => {
                const el = document.elementFromPoint(x, y);
                return el ? el.closest('.bottomnav .navlink') : null;
            };
            const clear = () => document.querySelectorAll('.bottomnav .navlink.sliding')
                                         .forEach(l => l.classList.remove('sliding'));
            const preview = (link) => {
                if (link === current) { return; }
                current = link;
                clear();
                if (link) { link.classList.add('sliding'); vibrate(18); }
            };

            const onMove = (e) => {
                const t = e.touches && e.touches[0];
                if (!t) { return; }
                const link = linkAt(t.clientX, t.clientY);
                if (link) { preview(link); e.preventDefault(); }
            };
            // Délégation sur document : survit aux re-rendus de la barre.
            document.addEventListener('touchstart', onMove, { passive: false });
            document.addEventListener('touchmove',  onMove, { passive: false });
            document.addEventListener('touchend', function () {
                const target = current;
                clear();
                current = null;
                if (target) { go(target.getAttribute('data-page')); }
            });
            document.addEventListener('touchcancel', function () { clear(); current = null; });
            // Desktop (souris) : touch supprimé, on route le clic.
            document.addEventListener('click', function (e) {
                const link = e.target.closest && e.target.closest('.bottomnav .navlink');
                if (link) { go(link.getAttribute('data-page')); }
            });
        };

        const s = p.document.createElement('script');
        s.textContent = '(' + topScript.toString() + ')();';
        p.document.body.appendChild(s);
    })();
    </script>
    """,
    height=0,
)
