# ─────────────────────────────────────────────
#  ui.py  –  Composants visuels partagés
# ─────────────────────────────────────────────
from __future__ import annotations

import streamlit as st


# ── Graphique en barres natif (HTML/CSS) ─────────────────────────
def css_bar_chart(
    labels: list[str],
    values: list[float],
    goal: float | None = None,
    unit: str = "km",
    accent: str = "orange",
    decimals: int = 0,
    caption: str | None = None,
):
    """Barres en verre animées, accordées au design liquid glass.
    - goal : trace une ligne d'objectif ; les barres sous le seuil passent en bleu.
    - accent : couleur par défaut des barres ("orange" ou "blue") quand pas de goal.
    - caption : légende sous le graphe (ce que représentent les données + unité).
    """
    if not values:
        st.info("Pas assez de données.")
        return

    peak = max(values + ([goal] if goal else []))
    scale = peak * 1.18 if peak > 0 else 1.0

    bars = ""
    for i, (label, val) in enumerate(zip(labels, values)):
        h = max(2.0, val / scale * 100)
        delay = 0.05 + i * 0.05
        if goal and val < goal:
            cls = "cssbar under"
        elif accent == "blue":
            cls = "cssbar blue"
        else:
            cls = "cssbar"
        bars += (
            f'<div class="cssbar-col" style="animation-delay:{delay:.2f}s">'
            f'<div class="cssbar-val" style="animation-delay:{delay + 0.4:.2f}s">{val:.{decimals}f}</div>'
            f'<div class="{cls}" style="height:{h:.1f}%;animation-delay:{delay:.2f}s"></div>'
            f'</div>'
        )

    goal_html = ""
    if goal:
        gb = goal / scale * 100
        goal_html = (
            f'<div class="cssbar-goal" style="bottom:calc({gb:.1f}% - 1px)">'
            f'<span>Objectif {goal:.0f} {unit}</span></div>'
        )

    xlabels = "".join(f"<div>{l}</div>" for l in labels)
    cap_html = f'<div class="chart-cap">{caption}</div>' if caption else ""

    st.markdown(
        f'<div class="chart-card">'
        f'<div class="cssbars">{goal_html}{bars}</div>'
        f'<div class="cssbars-x">{xlabels}</div>'
        f'{cap_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Stylisation des figures Plotly (cohérence verre) ─────────────
def apply_glass(fig, height: int | None = None):
    """Accorde une figure Plotly au thème liquid glass :
    fond transparent, typo Inter, grille discrète, tooltip en verre."""
    fig.update_layout(
        font=dict(family="Inter, sans-serif", color="#9AA6BC", size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(
            bgcolor="rgba(16,20,31,0.92)",
            bordercolor="rgba(255,255,255,0.16)",
            font=dict(color="#F4F7FB", family="Inter"),
        ),
        legend=dict(font=dict(color="#9AA6BC")),
    )
    if height is not None:
        fig.update_layout(height=height)
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="rgba(255,255,255,0.10)")
    fig.update_yaxes(
        showgrid=True, gridcolor="rgba(255,255,255,0.06)",
        zeroline=False, linecolor="rgba(255,255,255,0.10)",
    )
    return fig


# ── Courbe native (SVG) ──────────────────────────────────────────
_ACCENTS = {
    "orange": ("#FF7A3D", "#FC4C02"),
    "blue":   ("#3BA7D6", "#2E86AB"),
    "green":  ("#5FD3BC", "#44BBA4"),
}


def css_line_chart(
    labels: list[str],
    values: list[float],
    trend: list[float] | None = None,
    accent: str = "orange",
    unit: str = "",
    value_fmt=None,
    hint: str | None = None,
):
    """Courbe + aire en SVG avec repères : axe Y (min/max + unité), valeurs
    de départ/arrivée annotées, dates en axe X, et sous-titre explicatif.
    - value_fmt : fonction de formatage des valeurs (défaut : 1 décimale).
    - hint : sens de lecture, ex. "↓ plus rapide".
    """
    if not values:
        st.info("Pas assez de données.")
        return

    if value_fmt is None:
        value_fmt = lambda v: f"{v:.1f}"

    W, H = 320.0, 150.0
    gl, gr, gt, gb = 34.0, 12.0, 16.0, 18.0   # gouttières (axes)
    n = len(values)
    allv = list(values) + (list(trend) if trend else [])
    vmin, vmax = min(allv), max(allv)
    span = (vmax - vmin) or 1.0
    lo, hi = vmin - span * 0.12, vmax + span * 0.12
    rng = (hi - lo) or 1.0
    c1, c2 = _ACCENTS.get(accent, _ACCENTS["orange"])

    def X(i: int) -> float:
        return (gl + W - gr) / 2 if n == 1 else gl + (W - gl - gr) * (i / (n - 1))

    def Y(v: float) -> float:
        return gt + (H - gt - gb) * (1 - (v - lo) / rng)

    pts = [(X(i), Y(v)) for i, v in enumerate(values)]
    line_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area_pts = f"{pts[0][0]:.1f},{H - gb:.1f} " + line_pts + f" {pts[-1][0]:.1f},{H - gb:.1f}"
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" class="lc-dot"/>' for x, y in pts)

    # Axe Y : lignes + étiquettes min/max
    y_hi, y_lo = Y(vmax), Y(vmin)
    grid = (
        f'<line x1="{gl}" y1="{y_hi:.1f}" x2="{W - gr}" y2="{y_hi:.1f}" class="lc-grid"/>'
        f'<line x1="{gl}" y1="{y_lo:.1f}" x2="{W - gr}" y2="{y_lo:.1f}" class="lc-grid"/>'
        f'<text x="{gl - 4}" y="{y_hi + 3:.1f}" class="lc-axis lc-axis-r">{value_fmt(vmax)}</text>'
        f'<text x="{gl - 4}" y="{y_lo + 3:.1f}" class="lc-axis lc-axis-r">{value_fmt(vmin)}</text>'
    )

    # Valeurs de départ et d'arrivée
    (x0, y0), (xl, yl) = pts[0], pts[-1]
    endpts = (
        f'<text x="{x0:.1f}" y="{y0 - 6:.1f}" class="lc-val lc-val-s">{value_fmt(values[0])}</text>'
        f'<text x="{xl:.1f}" y="{yl - 6:.1f}" class="lc-val lc-val-e">{value_fmt(values[-1])}</text>'
    )

    # Axe X : première et dernière étiquette
    xaxis = ""
    if labels:
        xaxis = (
            f'<text x="{gl:.1f}" y="{H - 5:.1f}" class="lc-axis lc-axis-l">{labels[0]}</text>'
            f'<text x="{W - gr:.1f}" y="{H - 5:.1f}" class="lc-axis lc-axis-e">{labels[-1]}</text>'
        )

    trend_svg = ""
    if trend:
        tp = [(X(i), Y(v)) for i, v in enumerate(trend)]
        tline = " ".join(f"{x:.1f},{y:.1f}" for x, y in tp)
        trend_svg = f'<polyline points="{tline}" class="lc-trend"/>'

    sub = " · ".join(p for p in (unit, hint) if p)
    sub_svg = f'<text x="{gl}" y="9" class="lc-sub">{sub}</text>' if sub else ""

    uid = f"{accent}{n}{int(vmax * 100) % 1000}"
    svg = (
        f'<svg viewBox="0 0 {W:.0f} {H:.0f}" class="lc-svg {accent}">'
        f'<defs>'
        f'<linearGradient id="ln{uid}" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0%" stop-color="{c1}"/><stop offset="100%" stop-color="{c2}"/>'
        f'</linearGradient>'
        f'<linearGradient id="ar{uid}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{c2}" stop-opacity="0.34"/>'
        f'<stop offset="100%" stop-color="{c2}" stop-opacity="0"/>'
        f'</linearGradient>'
        f'</defs>'
        f'{grid}'
        f'<polygon points="{area_pts}" fill="url(#ar{uid})"/>'
        f'{trend_svg}'
        f'<polyline points="{line_pts}" class="lc-line" style="stroke:url(#ln{uid})"/>'
        f'{dots}{endpts}{xaxis}{sub_svg}'
        f'</svg>'
    )

    st.markdown(f'<div class="chart-card">{svg}</div>', unsafe_allow_html=True)


# ── Nuage de points natif (SVG) ──────────────────────────────────
def css_scatter(
    xs: list[float],
    values: list[float],
    types: list[str],
    color_map: dict[str, str],
    unit: str = "km",
    x_start: str = "",
    x_end: str = "",
    caption: str | None = None,
):
    """Nuage de points en SVG avec repères : axe Y (0 → max, unité), dates
    aux extrémités de l'axe X, légende des types et sous-titre."""
    if not values:
        st.info("Pas assez de données.")
        return

    W, H = 320.0, 165.0
    gl, gr, gt, gb = 30.0, 10.0, 12.0, 16.0
    vmax = max(values) or 1.0
    vhi = vmax * 1.12

    def X(fx: float) -> float:
        return gl + (W - gl - gr) * fx

    def Y(v: float) -> float:
        return gt + (H - gt - gb) * (1 - v / vhi)

    def R(v: float) -> float:
        return 2.4 + 6.0 * (v / vmax)

    circles = "".join(
        f'<circle cx="{X(fx):.1f}" cy="{Y(v):.1f}" r="{R(v):.1f}" '
        f'fill="{color_map.get(t, "#8893A8")}" fill-opacity="0.7" '
        f'stroke="{color_map.get(t, "#8893A8")}" stroke-width="0.7" class="sc-dot"/>'
        for fx, v, t in zip(xs, values, types)
    )

    y_top, y_bot = Y(vmax), Y(0)
    axes = (
        f'<line x1="{gl}" y1="{y_top:.1f}" x2="{W - gr}" y2="{y_top:.1f}" class="lc-grid"/>'
        f'<line x1="{gl}" y1="{y_bot:.1f}" x2="{W - gr}" y2="{y_bot:.1f}" class="lc-grid"/>'
        f'<text x="{gl - 4}" y="{y_top + 3:.1f}" class="lc-axis lc-axis-r">{vmax:.0f}</text>'
        f'<text x="{gl - 4}" y="{y_bot:.1f}" class="lc-axis lc-axis-r">0</text>'
        f'<text x="{gl}" y="9" class="lc-sub">{unit}</text>'
        f'<text x="{gl:.1f}" y="{H - 4:.1f}" class="lc-axis lc-axis-l">{x_start}</text>'
        f'<text x="{W - gr:.1f}" y="{H - 4:.1f}" class="lc-axis lc-axis-e">{x_end}</text>'
    )

    svg = (
        f'<svg viewBox="0 0 {W:.0f} {H:.0f}" class="sc-svg">'
        f'{axes}{circles}</svg>'
    )
    legend = "".join(
        f'<span class="sc-leg"><i style="background:{c}"></i>{t}</span>'
        for t, c in color_map.items()
    )
    cap_html = f'<div class="chart-cap">{caption}</div>' if caption else ""
    st.markdown(
        f'<div class="chart-card">{svg}<div class="sc-legend">{legend}</div>{cap_html}</div>',
        unsafe_allow_html=True,
    )
