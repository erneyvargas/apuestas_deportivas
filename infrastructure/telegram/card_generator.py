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

# ── Paleta ───────────────────────────────────────────────────────────────────
BG        = "#0d1117"
CARD      = "#161b22"
BORDER    = "#30363d"
TXT_PRI   = "#e6edf3"
TXT_SEC   = "#8b949e"
EMPTY     = "#21262d"
VALUE_CLR = "#3fb950"

# ── Colormaps ────────────────────────────────────────────────────────────────
MODEL_CMAP = LinearSegmentedColormap.from_list(
    "model", ["#da3633", "#e67e22", "#f1c40f", "#3fb950", "#1f6feb"]
)
VALUE_CMAP = LinearSegmentedColormap.from_list(
    "value", ["#1a5c2a", "#3fb950"]
)
MARKET_CMAP = LinearSegmentedColormap.from_list(
    "market", ["#3d4550", "#6e7681"]
)

RESULT_KEYS = ["home_win", "draw", "away_win"]
LABELS_ICON = {"home_win": "LOCAL", "draw": "EMPATE", "away_win": "VISIT."}
ICON_COLORS = {"home_win": "#4fc3f7", "draw": "#fff176", "away_win": "#ef9a9a"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch_logo(logo_url: str):
    try:
        r = requests.get(logo_url, timeout=5)
        return plt.imread(io.BytesIO(r.content), format="png")
    except Exception as e:
        logger.warning("Logo no disponible: %s", e)
        return None


def _gradient_bar(ax, x0, y0, w, h, prob, cmap):
    """Barra horizontal con degradado suave usando imshow."""
    # Fondo vacío
    ax.add_patch(mpatches.Rectangle(
        (x0, y0), w, h, facecolor=EMPTY, edgecolor="none", zorder=2,
    ))
    filled_w = prob * w
    if filled_w > 0.001:
        gradient = np.linspace(0, 1, 512).reshape(1, -1)
        img = ax.imshow(
            gradient, aspect="auto", cmap=cmap,
            extent=[x0, x0 + filled_w, y0, y0 + h],
            zorder=3, origin="lower",
        )
        # Recortar al área del bar para evitar sangrado
        clip = mpatches.Rectangle((x0, y0), filled_w, h, transform=ax.transData)
        img.set_clip_path(clip)


def _separator(ax, y, x0=0.06, x1=0.94):
    ax.axhline(y, xmin=x0, xmax=x1, color=BORDER, linewidth=0.8)


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

    fig_h = 9.5 if is_value else 8.0
    fig, ax = plt.subplots(figsize=(9, fig_h), dpi=150)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # ── Fondo card ────────────────────────────────────────────────────────
    ax.add_patch(FancyBboxPatch(
        (0.03, 0.02), 0.94, 0.96,
        boxstyle="round,pad=0.015",
        facecolor=CARD, edgecolor=BORDER, linewidth=1.2,
    ))

    # ── Franja superior ───────────────────────────────────────────────────
    top_color = VALUE_CLR if is_value else "#1f6feb"
    ax.add_patch(FancyBboxPatch(
        (0.03, 0.915), 0.94, 0.065,
        boxstyle="round,pad=0.015",
        facecolor=top_color, edgecolor="none",
    ))

    # Logo dentro de la franja superior, usando AnnotationBbox
    logo_img = _fetch_logo(league_logo_url) if league_logo_url else None
    if logo_img is not None:
        imagebox = OffsetImage(logo_img, zoom=0.38)
        ab = AnnotationBbox(
            imagebox, (0.095, 0.948),
            frameon=False, xycoords="data", zorder=10,
        )
        ax.add_artist(ab)
        title_x = 0.56
    else:
        title_x = 0.5

    header_lbl = "VALUE BET DETECTADO" if is_value else "Analisis de Partido"
    ax.text(title_x, 0.948, header_lbl,
            color="white", fontsize=11, fontweight="bold",
            ha="center", va="center")

    # ── Subheader: liga y fecha ────────────────────────────────────────────
    ax.text(0.08, 0.895, liga,     color=TXT_SEC, fontsize=8.5, va="center")
    ax.text(0.92, 0.895, fecha_str, color=TXT_SEC, fontsize=8.5, va="center", ha="right")

    # ── Nombre del partido ────────────────────────────────────────────────
    ax.text(0.5, 0.855, partido,
            color=TXT_PRI, fontsize=13, fontweight="bold",
            ha="center", va="center")

    _separator(ax, 0.825)

    # ── Secciones de resultados ───────────────────────────────────────────
    bottom_limit = 0.13 if is_value else 0.06
    section_h    = (0.82 - bottom_limit) / 3
    BAR_X  = 0.14
    BAR_W  = 0.68
    BAR_H  = 0.040
    BAR_MH = 0.027

    for i, key in enumerate(RESULT_KEYS):
        label   = labels[key]
        model_p = pred[key]
        fair_p  = fair[key]
        odd     = odds[key]
        is_vb   = label in vb_set

        y_top = 0.82 - i * section_h

        # Etiqueta e indicador de rol
        pct_color = VALUE_CLR if is_vb else TXT_PRI
        ax.text(0.08, y_top - 0.025,
                LABELS_ICON[key],
                color=ICON_COLORS[key], fontsize=7.5, fontweight="bold", va="center")
        ax.text(0.21, y_top - 0.025,
                label,
                color=pct_color, fontsize=10, fontweight="bold", va="center")
        ax.text(0.92, y_top - 0.025,
                f"{model_p * 100:.0f}%",
                color=pct_color, fontsize=11, fontweight="bold",
                ha="right", va="center")

        # Barra modelo (degradado suave)
        y_model = y_top - 0.078
        ax.text(0.075, y_model + BAR_H / 2, "modelo",
                color=TXT_SEC, fontsize=7, va="center", ha="right")
        _gradient_bar(ax, BAR_X, y_model, BAR_W, BAR_H, model_p,
                      VALUE_CMAP if is_vb else MODEL_CMAP)

        # Barra betplay (degradado gris)
        y_market = y_model - BAR_MH - 0.018
        ax.text(0.075, y_market + BAR_MH / 2, "betplay",
                color=TXT_SEC, fontsize=7, va="center", ha="right")
        if fair_p:
            _gradient_bar(ax, BAR_X, y_market, BAR_W, BAR_MH, fair_p, MARKET_CMAP)
            odd_str = f"@ {odd:.2f}" if odd else "—"
            ax.text(BAR_X + BAR_W + 0.015, y_market + BAR_MH / 2,
                    f"{fair_p * 100:.0f}%  {odd_str}",
                    color=TXT_SEC, fontsize=7.5, va="center")

        # Badge de edge
        if is_vb and odd:
            edge    = (model_p * odd - 1) * 100
            badge_y = y_market - 0.032
            ax.add_patch(FancyBboxPatch(
                (BAR_X, badge_y - 0.012), 0.28, 0.024,
                boxstyle="round,pad=0.005",
                facecolor="#1a3a2a", edgecolor=VALUE_CLR, linewidth=0.8,
            ))
            ax.text(BAR_X + 0.14, badge_y,
                    f"Edge: +{edge:.0f}%",
                    color=VALUE_CLR, fontsize=8, fontweight="bold",
                    ha="center", va="center")

        if i < 2:
            _separator(ax, y_top - section_h + 0.01)

    # ── Footer de apuesta recomendada ─────────────────────────────────────
    if is_value:
        _separator(ax, bottom_limit + 0.055)
        ax.text(0.5, bottom_limit + 0.038,
                "APUESTA RECOMENDADA",
                color=VALUE_CLR, fontsize=9, fontweight="bold",
                ha="center", va="center")
        vb_parts = [
            f"{lbl}  @{odd:.2f}  edge +{(prob * odd - 1) * 100:.0f}%"
            for lbl, prob, odd, _ in value_bets
        ]
        ax.text(0.5, bottom_limit + 0.015,
                "   ·   ".join(vb_parts),
                color=TXT_PRI, fontsize=8.5,
                ha="center", va="center")

    # ── Render ────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=BG, dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.read()
