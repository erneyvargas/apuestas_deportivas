import io
import logging

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import requests
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.patches import FancyBboxPatch

logger = logging.getLogger(__name__)

# ── Paleta premium: Deep Navy + Gold ─────────────────────────────────────────
BG        = "#060B18"   # fondo profundo navy
CARD      = "#0C1529"   # superficie principal
CARD_ALT  = "#0F1E38"   # superficie alternada (secciones pares)
BORDER    = "#1C2E50"   # borde sutil azul
BORDER_AC = "#2A5298"   # borde de acento
TXT_PRI   = "#EDF2FF"   # blanco frío
TXT_SEC   = "#6B88B5"   # azul-gris secundario
EMPTY     = "#0A1628"   # relleno vacío de barras
GOLD      = "#F0A500"   # oro premium
GOLD_LT   = "#FFD166"   # oro claro
BLUE_EL   = "#4080FF"   # azul eléctrico
TEAL      = "#00C9A7"   # verde azulado (empate)
RED_SOFT  = "#FF6B6B"   # rojo suave (visitante)

# ── Colormaps ─────────────────────────────────────────────────────────────────
# Modelo → naranja
MODEL_CMAP = LinearSegmentedColormap.from_list(
    "model", ["#5C1E00", "#C04000", "#FF6B00", "#FF9E3D"],
)
# Value bet → naranja más brillante
VALUE_CMAP = LinearSegmentedColormap.from_list(
    "value", ["#7B2D00", "#E05000", "#FF8C00", GOLD_LT],
)
# Betplay → azul
MARKET_CMAP = LinearSegmentedColormap.from_list(
    "market", ["#07163A", "#1040A0", "#3D7FFF"],
)

RESULT_KEYS  = ["home_win", "draw", "away_win"]
LABELS_ICON  = {"home_win": "LOCAL", "draw": "EMPATE", "away_win": "VISITA"}
ICON_COLORS  = {"home_win": BLUE_EL, "draw": TEAL, "away_win": RED_SOFT}
SECTION_BG   = {"home_win": "#0C1529", "draw": "#0F1E38", "away_win": "#0C1529"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch_logo(logo_url: str):
    try:
        r = requests.get(logo_url, timeout=5)
        return plt.imread(io.BytesIO(r.content), format="png")
    except Exception as e:
        logger.warning("Logo no disponible: %s", e)
        return None


def _gradient_bar(ax, x0, y0, w, h, prob, cmap, radius=0.003):
    """Barra con degradado, fondo redondeado y clip preciso."""
    # Fondo vacío
    ax.add_patch(FancyBboxPatch(
        (x0, y0), w, h,
        boxstyle=f"round,pad={radius}",
        facecolor=EMPTY, edgecolor="none", zorder=2,
    ))
    filled_w = max(prob * w, 0.001)
    gradient = np.linspace(0, 1, 512).reshape(1, -1)
    img = ax.imshow(
        gradient, aspect="auto", cmap=cmap,
        extent=[x0, x0 + filled_w, y0, y0 + h],
        zorder=3, origin="lower",
    )
    clip = mpatches.Rectangle((x0, y0), filled_w, h, transform=ax.transData)
    img.set_clip_path(clip)



def _sep(ax, y, x0=0.06, x1=0.94, alpha=0.4):
    ax.axhline(y, xmin=x0, xmax=x1, color=BORDER_AC, linewidth=0.6, alpha=alpha)


# ── Card principal ────────────────────────────────────────────────────────────

def generate_match_card(
    partido: str,
    fecha_str: str,
    liga: str,
    pred: dict,
    labels: dict,
    odds: dict,
    fair: dict,
    value_bets: list | None = None,
    league_logo_url: str | None = None,
) -> bytes:
    is_value = bool(value_bets)
    vb_set   = {lbl for lbl, *_ in (value_bets or [])}

    fig_h = 10.0 if is_value else 8.5
    fig, ax = plt.subplots(figsize=(9, fig_h), dpi=150)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # ── Sombra exterior (efecto glow) ─────────────────────────────────────
    for offset, alpha in [(0.008, 0.08), (0.004, 0.15)]:
        ax.add_patch(FancyBboxPatch(
            (0.03 - offset, 0.02 - offset),
            0.94 + 2 * offset, 0.96 + 2 * offset,
            boxstyle="round,pad=0.018",
            facecolor=BLUE_EL, edgecolor="none",
            alpha=alpha, zorder=0,
        ))

    # ── Fondo card ────────────────────────────────────────────────────────
    ax.add_patch(FancyBboxPatch(
        (0.03, 0.02), 0.94, 0.96,
        boxstyle="round,pad=0.015",
        facecolor=CARD, edgecolor=BORDER_AC,
        linewidth=0.9, zorder=1,
    ))

    # ── Zona de cabecera: franja de acento + panel blanco ─────────────────
    accent_clr = GOLD if is_value else BLUE_EL

    # Franja de color delgada en la parte superior (indicador value / análisis)
    ax.add_patch(FancyBboxPatch(
        (0.03, 0.955), 0.94, 0.023,
        boxstyle="round,pad=0.010",
        facecolor=accent_clr, edgecolor="none", zorder=2,
    ))
    badge_label = "VALUE BET" if is_value else "ANÁLISIS"
    ax.text(0.5, 0.970, badge_label,
            color="#0C1529", fontsize=8.5, fontweight="bold",
            ha="center", va="center", zorder=6)

    # Panel blanco para logo + nombre del partido
    hdr_y = 0.835
    hdr_h = 0.118
    ax.add_patch(FancyBboxPatch(
        (0.03, hdr_y), 0.94, hdr_h,
        boxstyle="round,pad=0.010",
        facecolor="#FFFFFF", edgecolor="#E0E4EE",
        linewidth=0.8, zorder=2,
    ))

    # Logo de liga sobre fondo blanco
    logo_img = _fetch_logo(league_logo_url) if league_logo_url else None
    partido_x = 0.5

    if logo_img is not None:
        imagebox = OffsetImage(logo_img, zoom=0.42)
        ab = AnnotationBbox(
            imagebox, (0.10, hdr_y + hdr_h / 2),
            frameon=False, xycoords="data", zorder=10,
        )
        ax.add_artist(ab)
        partido_x = 0.57

    # Nombre del partido: tipografía grande sobre blanco
    ax.text(partido_x, hdr_y + hdr_h * 0.62, partido,
            color="#0C1529", fontsize=17, fontweight="bold",
            ha="center", va="center", zorder=5)

    # Subheader liga / fecha sobre el panel blanco
    # Usamos posiciones fijas y alineaciones opuestas para evitar solapamientos
    liga_x = 0.24 if logo_img is not None else 0.06
    ax.text(liga_x, hdr_y + hdr_h * 0.22, liga.upper(),
            color="#6B88B5", fontsize=9, va="center", ha="left", fontweight="bold", zorder=5)
    ax.text(0.94, hdr_y + hdr_h * 0.22, fecha_str,
            color="#6B88B5", fontsize=8.5, va="center", ha="right", zorder=5)

    _sep(ax, hdr_y - 0.005)

    # ── Secciones de resultados ───────────────────────────────────────────
    results_top  = 0.815
    bottom_limit = 0.14 if is_value else 0.07
    section_h    = (results_top - bottom_limit) / 3
    BAR_X  = 0.155
    BAR_W  = 0.660
    BAR_H  = 0.038
    BAR_MH = 0.024

    for i, key in enumerate(RESULT_KEYS):
        label   = labels[key]
        model_p = pred[key]
        fair_p  = fair[key]
        odd     = odds[key]
        is_vb   = label in vb_set

        y_top    = 0.815 - i * section_h
        sec_bg   = CARD_ALT if i % 2 == 1 else CARD

        # Fondo de sección alternado
        ax.add_patch(mpatches.Rectangle(
            (0.03, y_top - section_h + 0.002), 0.94, section_h - 0.004,
            facecolor=sec_bg, zorder=1,
        ))

        icon_clr = ICON_COLORS[key]
        pct_clr  = GOLD if is_vb else TXT_PRI

        # Nombre del resultado (alineado a la izquierda)
        ax.text(0.045, y_top - 0.027, label,
                color=pct_clr, fontsize=12, fontweight="bold",
                va="center", zorder=5)

        # Porcentaje a la derecha (Principal)
        ax.text(0.955, y_top - 0.027, f"{model_p * 100:.0f}%",
                color=pct_clr, fontsize=20, fontweight="bold",
                ha="right", va="center", zorder=5)

        # ── Barra modelo ──────────────────────────────────────────────────
        y_model = y_top - 0.073
        ax.text(0.148, y_model + BAR_H / 2, "MODELO",
                color=TXT_SEC, fontsize=7, va="center", ha="right",
                fontweight="bold", zorder=5)
        _gradient_bar(ax, BAR_X, y_model, BAR_W, BAR_H, model_p,
                      VALUE_CMAP if is_vb else MODEL_CMAP)
        # Etiqueta de porcentaje encima de la barra
        ax.text(BAR_X + BAR_W + 0.01, y_model + BAR_H / 2,
                f"{model_p * 100:.0f}%",
                color=GOLD if is_vb else BLUE_EL,
                fontsize=12, fontweight="bold", va="center", zorder=5)

        # ── Barra betplay ─────────────────────────────────────────────────
        y_market = y_model - BAR_MH - 0.016
        ax.text(0.148, y_market + BAR_MH / 2, "BETPLAY",
                color=TXT_SEC, fontsize=7, va="center", ha="right",
                fontweight="bold", zorder=5)
        if fair_p:
            _gradient_bar(ax, BAR_X, y_market, BAR_W, BAR_MH, fair_p, MARKET_CMAP)
            odd_str = f"@ {odd:.2f}" if odd else "—"
            ax.text(BAR_X + BAR_W + 0.01, y_market + BAR_MH / 2,
                    f"{fair_p * 100:.0f}%  {odd_str}",
                    color=TXT_SEC, fontsize=12, va="center", zorder=5)

        # ── Badge de edge ─────────────────────────────────────────────────
        if is_vb and odd:
            edge    = (model_p * odd - 1) * 100
            bx, by  = BAR_X, y_market - 0.038
            bw, bh  = 0.30, 0.026
            # Fondo del badge con degradado dorado
            ax.add_patch(FancyBboxPatch(
                (bx, by), bw, bh,
                boxstyle="round,pad=0.006",
                facecolor="#2A1800", edgecolor=GOLD,
                linewidth=1.0, zorder=4,
            ))
            ax.text(bx + bw / 2, by + bh / 2,
                    f"EDGE  +{edge:.0f}%",
                    color=GOLD_LT, fontsize=8.5, fontweight="bold",
                    ha="center", va="center", zorder=5)

        if i < 2:
            _sep(ax, y_top - section_h + 0.01)

    # ── Footer: apuesta recomendada ───────────────────────────────────────
    if is_value:
        footer_top = bottom_limit + 0.045
        _sep(ax, footer_top, alpha=0.7)

        # Hacemos el recuadro del footer más compacto (menos alto)
        footer_y_min = 0.065
        footer_h = footer_top - footer_y_min
        ax.add_patch(FancyBboxPatch(
            (0.03, footer_y_min), 0.94, footer_h,
            boxstyle="round,pad=0.010",
            facecolor="#1A0E00", edgecolor=GOLD,
            linewidth=0.8, zorder=2,
        ))
        
        # Título del footer
        ax.text(0.5, footer_top - 0.018,
                "APUESTA RECOMENDADA",
                color=GOLD, fontsize=10.5, fontweight="bold",
                ha="center", va="center", zorder=5)

        vb_parts = [
            f"{lbl}  @{odd:.2f}  ·  edge +{(prob * odd - 1) * 100:.0f}%"
            for lbl, prob, odd, _ in (value_bets or [])
        ]
        # Posicionamos el texto de forma más compacta dentro del recuadro
        ax.text(0.5, footer_top - 0.040,
                "   ·   ".join(vb_parts),
                color=TXT_PRI, fontsize=10,
                ha="center", va="center", zorder=5)

    # ── Branding footer ───────────────────────────────────────────────────
    brand_y = 0.045
    ax.text(0.5, brand_y,
            "Sport Analytics  ·  Powered by XGBoost",
            color="#2A4878", fontsize=7,
            ha="center", va="center", zorder=5)

    # ── Render ────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight",
                facecolor=BG, dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.read()
