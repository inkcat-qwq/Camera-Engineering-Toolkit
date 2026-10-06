"""Single session theme palette and a pinned Streamlit 1.65 native-theme bridge.

The bridge sends the app's own theme through Streamlit's host message protocol.
It changes the current browser only; no process-wide config/rcParams mutation.
Native widgets (including the canvas editor) and charts use the same palette.
"""
import json

PALETTES = {
    "Light": {"base": 0, "backgroundColor": "#FFFFFF", "secondaryBackgroundColor": "#F0F3F8",
              "textColor": "#243246", "primaryColor": "#168B99", "borderColor": "#D5DCE7"},
    "Dark": {"base": 1, "backgroundColor": "#0E1623", "secondaryBackgroundColor": "#182334",
             "textColor": "#E2EAF4", "primaryColor": "#45B9C5", "borderColor": "#536075"},
}


def palette(theme):
    if theme not in PALETTES:
        raise ValueError("Theme must be Light or Dark.")
    return dict(PALETTES[theme])


def native_theme_html(theme):
    # All values come from the fixed palette; user text is never interpolated.
    payload = json.dumps({"stCommVersion": 1, "type": "SET_CUSTOM_THEME_CONFIG",
                          "themeInfo": palette(theme)})
    return f'<script>window.postMessage({payload}, window.location.origin);</script>'


def theme_css(theme):
    p = palette(theme)
    return f'''<style>
    .stApp, [data-testid="stHeader"] {{background-color:{p['backgroundColor']}; color:{p['textColor']};}}
    [data-testid="stSidebar"] {{background-color:{p['secondaryBackgroundColor']};}}
    [data-testid="stMetric"] {{border-color:{p['borderColor']} !important;}}
    .eyebrow {{color:{p['primaryColor']} !important;}}
    [data-testid="stToolbar"], .st-key-theme_bridge {{display:none;}}
    </style>'''
