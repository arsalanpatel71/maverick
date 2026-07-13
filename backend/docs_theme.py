"""Dark OpenAPI docs styling (Swagger UI + ReDoc): Poppins, light grey text, no bright chrome."""

from __future__ import annotations

import html
import json
from typing import Any, Dict

# Readable light greys only (no near-white).
TEXT_PRIMARY = "#b4c0ce"
TEXT_EMPHASIS = "#c8d4e2"
TEXT_SECONDARY = "#9aa8b8"
TEXT_MUTED = "#8a96a8"

POPPINS_FONT_TAGS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
"""

SWAGGER_DARK_CSS = f"""
/* Poppins for UI; keep monospace for paths / code */
body {{
  background: radial-gradient(1200px 800px at 20% -10%, #1a2332 0%, #0d1117 45%, #0a0e14 100%) fixed !important;
  color: {TEXT_PRIMARY} !important;
  font-family: 'Poppins', system-ui, sans-serif !important;
}}
.swagger-ui {{
  color: {TEXT_PRIMARY};
  font-family: 'Poppins', system-ui, sans-serif !important;
}}

.swagger-ui .wrapper {{ background: transparent; max-width: 1460px; padding: 0 1.25rem 2rem; }}

.swagger-ui .topbar {{
  background: linear-gradient(180deg, #161b22 0%, #12171f 100%) !important;
  border-bottom: 1px solid #30363d;
  box-shadow: 0 1px 0 rgba(0,0,0,0.35);
}}
.swagger-ui .topbar .download-url-wrapper .select-label {{ color: {TEXT_MUTED} !important; }}
.swagger-ui .topbar input {{
  background: #0d1117 !important; color: {TEXT_PRIMARY} !important; border: 1px solid #30363d !important; border-radius: 6px !important;
}}

.swagger-ui .information-container {{
  background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 1.25rem 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 4px 24px rgba(0,0,0,0.25);
}}
.swagger-ui .info .title {{ color: {TEXT_EMPHASIS} !important; font-weight: 650 !important; letter-spacing: -0.02em; }}
.swagger-ui .info .base-url {{ color: #79c0ff !important; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important; }}
.swagger-ui .info p, .swagger-ui .info li, .swagger-ui .info table {{ color: {TEXT_SECONDARY} !important; }}
.swagger-ui .info h1, .swagger-ui .info h2, .swagger-ui .info h3, .swagger-ui .info h4, .swagger-ui .info h5 {{ color: {TEXT_EMPHASIS} !important; }}
.swagger-ui .info a {{ color: #58a6ff !important; }}
.swagger-ui .scheme-container {{
  background: #21262d !important; color: {TEXT_PRIMARY} !important; border: 1px solid #30363d !important; border-radius: 8px; box-shadow: inset 0 1px 0 rgba(0,0,0,0.35);
}}
.swagger-ui .filter .operation-filter-input {{
  background: #0d1117 !important; color: {TEXT_PRIMARY} !important; border: 1px solid #30363d !important; border-radius: 6px !important;
}}

.swagger-ui .opblock-tag {{ color: {TEXT_EMPHASIS} !important; border-bottom: 1px solid #30363d !important; font-weight: 600; letter-spacing: 0.02em; }}
.swagger-ui .opblock-tag small {{ color: {TEXT_MUTED} !important; }}

.swagger-ui .opblock {{
  border: 1px solid #30363d !important;
  border-radius: 10px !important;
  margin: 0 0 0.85rem !important;
  box-shadow: 0 2px 12px rgba(0,0,0,0.2);
  background: #161b22 !important;
  overflow: hidden;
}}
.swagger-ui .opblock .opblock-summary {{ border: none !important; align-items: center; gap: 0.35rem; }}
/* HTTP method: no solid fill — colored text + faint outline (dark mode) */
.swagger-ui .opblock .opblock-summary-method,
.swagger-ui .opblock button.opblock-summary-method,
.swagger-ui .opblock .btn.opblock-summary-method {{
  background: transparent !important;
  background-color: transparent !important;
  background-image: none !important;
  box-shadow: none !important;
  text-shadow: none !important;
  font-weight: 700 !important;
  border-radius: 6px !important;
  min-width: 4.5rem;
  padding: 0.35rem 0.5rem !important;
  font-family: 'Poppins', system-ui, sans-serif !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  color: {TEXT_SECONDARY} !important;
}}
.swagger-ui .opblock.opblock-get .opblock-summary-method,
.swagger-ui .opblock.opblock-get button.opblock-summary-method {{
  color: #9fd4ff !important;
  border-color: rgba(159, 212, 255, 0.4) !important;
}}
.swagger-ui .opblock.opblock-post .opblock-summary-method,
.swagger-ui .opblock.opblock-post button.opblock-summary-method {{
  color: #8ee4a0 !important;
  border-color: rgba(142, 228, 160, 0.4) !important;
}}
.swagger-ui .opblock.opblock-put .opblock-summary-method,
.swagger-ui .opblock.opblock-put button.opblock-summary-method {{
  color: #f0d27a !important;
  border-color: rgba(240, 210, 122, 0.45) !important;
}}
.swagger-ui .opblock.opblock-delete .opblock-summary-method,
.swagger-ui .opblock.opblock-delete button.opblock-summary-method {{
  color: #ffaaa3 !important;
  border-color: rgba(255, 170, 163, 0.45) !important;
}}
.swagger-ui .opblock.opblock-patch .opblock-summary-method,
.swagger-ui .opblock.opblock-patch button.opblock-summary-method {{
  color: #d4b8ff !important;
  border-color: rgba(212, 184, 255, 0.45) !important;
}}
.swagger-ui .opblock.opblock-options .opblock-summary-method,
.swagger-ui .opblock.opblock-options button.opblock-summary-method {{
  color: #9fd4ff !important;
  border-color: rgba(159, 212, 255, 0.35) !important;
}}
.swagger-ui .opblock.opblock-head .opblock-summary-method,
.swagger-ui .opblock.opblock-head button.opblock-summary-method {{
  color: #b8c0ff !important;
  border-color: rgba(184, 192, 255, 0.4) !important;
}}
.swagger-ui .opblock .opblock-summary-path,
.swagger-ui .opblock .opblock-summary-path__deprecated,
.swagger-ui .opblock .opblock-summary-path a,
.swagger-ui .opblock .opblock-summary-path__descriptor {{
  color: {TEXT_EMPHASIS} !important;
  font-weight: 600 !important;
  font-family: ui-monospace, "SF Mono", SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
  font-size: 0.95rem !important;
  letter-spacing: 0.01em;
  text-shadow: 0 1px 2px rgba(0,0,0,0.45);
}}
.swagger-ui .opblock .opblock-summary-description,
.swagger-ui .opblock-summary .opblock-summary-description {{
  color: {TEXT_SECONDARY} !important;
  font-weight: 500 !important;
  font-size: 0.9rem !important;
  opacity: 1 !important;
  font-family: 'Poppins', system-ui, sans-serif !important;
}}

/* Operation row: flat dark (color identity only on method text) */
.swagger-ui .opblock.opblock-get,
.swagger-ui .opblock.opblock-post,
.swagger-ui .opblock.opblock-put,
.swagger-ui .opblock.opblock-delete,
.swagger-ui .opblock.opblock-patch,
.swagger-ui .opblock.opblock-options,
.swagger-ui .opblock.opblock-head {{
  background: #161b22 !important;
  border-color: #30363d !important;
}}
.swagger-ui .opblock.is-open .opblock-summary {{ border-bottom: 1px solid #30363d !important; }}

.swagger-ui .opblock-body {{ background: #0d1117 !important; }}
.swagger-ui .opblock-description-wrapper, .swagger-ui .opblock-description-wrapper p, .swagger-ui .opblock-description-wrapper li {{ color: {TEXT_SECONDARY} !important; }}

.swagger-ui .opblock-section-header {{
  background: #21262d !important;
  background-color: #21262d !important;
  border-bottom: 1px solid #30363d !important;
  box-shadow: none !important;
}}
.swagger-ui .opblock-section-header > label,
.swagger-ui .opblock-section-header h4 {{ color: {TEXT_EMPHASIS} !important; }}
.swagger-ui .opblock-section-header .tab {{ border-bottom-color: #30363d !important; }}
.swagger-ui .opblock-section-header .tab li {{ border-color: #30363d !important; }}
.swagger-ui .opblock-section-header .tab li button.tablinks {{ color: {TEXT_MUTED} !important; background: transparent !important; font-family: 'Poppins', system-ui, sans-serif !important; }}
.swagger-ui .opblock-section-header .tab li button.tablinks.active {{
  color: #58a6ff !important; font-weight: 600; border-bottom: 2px solid #58a6ff !important; background: transparent !important;
}}

.swagger-ui button.try-out__btn,
.swagger-ui .try-out__btn,
.swagger-ui .btn.try-out__btn {{
  background: #30363d !important; color: {TEXT_PRIMARY} !important; border: 1px solid #484f58 !important; box-shadow: none !important;
  font-family: 'Poppins', system-ui, sans-serif !important;
}}
.swagger-ui button.try-out__btn:hover,
.swagger-ui .btn.try-out__btn:hover {{ background: #3d444d !important; color: {TEXT_PRIMARY} !important; }}

.swagger-ui .tab li button.tablinks {{ color: {TEXT_MUTED} !important; background: transparent !important; font-family: 'Poppins', system-ui, sans-serif !important; }}
.swagger-ui .tab li button.tablinks.active {{ color: #58a6ff !important; font-weight: 600; border-bottom: 2px solid #58a6ff !important; }}

.swagger-ui .copy-to-clipboard button {{
  background: #30363d !important; color: {TEXT_PRIMARY} !important; border: 1px solid #484f58 !important;
}}

.swagger-ui .parameter__name, .swagger-ui .model-title {{ color: {TEXT_EMPHASIS} !important; }}
.swagger-ui .parameter__type, .swagger-ui .prop-type {{ color: #79c0ff !important; }}
.swagger-ui .parameter__extension, .swagger-ui .parameter__in {{ color: {TEXT_MUTED} !important; }}

.swagger-ui table thead tr th, .swagger-ui table thead tr td {{
  color: {TEXT_EMPHASIS} !important; border-color: #30363d !important; background: #21262d !important;
}}
.swagger-ui table tbody tr td {{ color: {TEXT_PRIMARY} !important; border-color: #30363d !important; }}
.swagger-ui .response-col_status {{ color: #79c0ff !important; font-weight: 600; }}

.swagger-ui input, .swagger-ui textarea, .swagger-ui select, .swagger-ui .btn.cancel {{
  background: #0d1117 !important; color: {TEXT_PRIMARY} !important; border: 1px solid #30363d !important; border-radius: 6px !important;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
}}
.swagger-ui .btn.execute {{
  background: linear-gradient(180deg, #238636 0%, #1a7f37 100%) !important; color: {TEXT_PRIMARY} !important; border-color: #2ea043 !important;
  font-family: 'Poppins', system-ui, sans-serif !important;
}}
.swagger-ui .btn.btn-done {{
  background: #21262d !important; color: {TEXT_PRIMARY} !important; border-color: #30363d !important; font-family: 'Poppins', system-ui, sans-serif !important;
}}

.swagger-ui .responses-inner h4, .swagger-ui .responses-inner h5 {{ color: {TEXT_EMPHASIS} !important; }}
.swagger-ui .response-col_description__inner div.markdown, .swagger-ui .markdown code {{ color: {TEXT_SECONDARY} !important; }}
.swagger-ui .highlight-code {{
  background: #161b22 !important; border: 1px solid #30363d !important; border-radius: 8px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
}}

.swagger-ui .dialog-ux .modal-ux {{
  background: #161b22 !important; border: 1px solid #30363d !important; border-radius: 12px; box-shadow: 0 16px 48px rgba(0,0,0,0.5);
}}
.swagger-ui .dialog-ux .modal-ux-header h3, .swagger-ui .dialog-ux .modal-ux-content p,
.swagger-ui .dialog-ux .modal-ux-content h4, .swagger-ui .dialog-ux .modal-ux-content h5 {{ color: {TEXT_PRIMARY} !important; }}

.swagger-ui .model-box {{ background: #21262d !important; border-radius: 8px; border: 1px solid #30363d !important; }}
.swagger-ui .model-box-control {{ color: {TEXT_MUTED} !important; }}
.swagger-ui section.models {{ border: 1px solid #30363d !important; border-radius: 10px; background: #161b22; overflow: hidden; }}
.swagger-ui section.models h4 {{ color: {TEXT_EMPHASIS} !important; border-color: #30363d !important; background: #21262d !important; }}

.swagger-ui .errors-wrapper {{ background: #21262d !important; border: 1px solid #f8514966 !important; color: #ffa198 !important; border-radius: 8px; }}

.swagger-ui .opblock-body .no-margin,
.swagger-ui .parameters-container,
.swagger-ui .responses-wrapper,
.swagger-ui .parameters-col_description,
.swagger-ui .response-col_description {{ background: transparent !important; }}
"""

REDOC_DARK_THEME: Dict[str, Any] = {
    "colors": {
        "primary": {"main": "#58a6ff"},
        "text": {"primary": TEXT_PRIMARY, "secondary": TEXT_SECONDARY},
        "responses": {
            "success": {"color": "#3fb950"},
            "error": {"color": "#f85149"},
            "redirect": {"color": "#d29922"},
            "info": {"color": "#58a6ff"},
        },
        "http": {
            "get": "#58a6ff",
            "post": "#3fb950",
            "put": "#d29922",
            "delete": "#f85149",
            "basic": "#8b949e",
            "link": "#a371f7",
        },
        "border": {"dark": "#30363d", "light": "#21262d"},
        "success": {"main": "#3fb950"},
        "warning": {"main": "#d29922"},
        "error": {"main": "#f85149"},
    },
    "schema": {
        "nestedBackground": "#21262d",
        "typeNameColor": "#79c0ff",
        "linesColor": "#30363d",
    },
    "typography": {
        "fontFamily": "'Poppins', system-ui, sans-serif",
        "fontSize": "14px",
        "lineHeight": "1.55em",
        "code": {
            "fontFamily": "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
            "color": TEXT_SECONDARY,
        },
        "headings": {
            "fontFamily": "'Poppins', system-ui, sans-serif",
            "fontWeight": "600",
        },
        "links": {
            "color": "#58a6ff",
            "visited": "#a371f7",
            "hover": "#79c0ff",
        },
    },
    "sidebar": {
        "backgroundColor": "#0d1117",
        "textColor": TEXT_PRIMARY,
        "arrow": {"color": TEXT_MUTED},
    },
    "rightPanel": {"backgroundColor": "#161b22"},
}


def redoc_theme_html_attr() -> str:
    return html.escape(
        json.dumps(REDOC_DARK_THEME, separators=(",", ":")),
        quote=True,
    )


def swagger_dark_head_inject() -> str:
    """Poppins + overrides; inject before </head> on Swagger UI page."""
    return f"{POPPINS_FONT_TAGS}<style>{SWAGGER_DARK_CSS}</style>"


def redoc_head_inject() -> str:
    """Poppins only; theme handles colors. Inject before </head> on ReDoc page."""
    return POPPINS_FONT_TAGS


def redoc_body_opening_replacement() -> str:
    """Prefix for first `body {{` in FastAPI ReDoc template (keeps margin/padding)."""
    return (
        "body { font-family: 'Poppins', system-ui, sans-serif; "
        f"background: #0d1117; color: {TEXT_PRIMARY};"
    )
