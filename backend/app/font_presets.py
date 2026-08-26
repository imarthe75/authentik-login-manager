"""
Lista curada de fuentes seleccionables por tenant (heading/body).

Dos categorías:
- Google Fonts: se cargan por @import, sin fricción, sin licencia que
  gestionar (google_query alimenta directo la URL de fonts.googleapis.com).
- requires_upload=True: tipografías comerciales del manual de identidad de
  un tenant (ej. Gotham, BW Modelica, Corporative Sans Alt — EdoMex) que NO
  están en el CDN gratuito de Google Fonts. No se fabrica ni se hotlinkea un
  origen para estas — el propio tenant debe subir su archivo .woff2
  licenciado (mismo patrón base64 que logo_top_base64 en TenantTheme).
"""
from typing import TypedDict


class FontPreset(TypedDict):
    key: str
    label: str
    css_family: str
    google_query: str | None
    requires_upload: bool


FONT_PRESETS: dict[str, FontPreset] = {
    "inter": {
        "key": "inter", "label": "Inter",
        "css_family": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
        "google_query": "Inter:wght@300;400;500;600;700;800;900", "requires_upload": False,
    },
    "jost": {
        "key": "jost", "label": "Jost (CaSmarts/Civika)",
        "css_family": "'Jost', -apple-system, BlinkMacSystemFont, sans-serif",
        "google_query": "Jost:wght@300;400;500;600;700;800", "requires_upload": False,
    },
    "outfit": {
        "key": "outfit", "label": "Outfit (CaSmarts/Civika)",
        "css_family": "'Outfit', -apple-system, BlinkMacSystemFont, sans-serif",
        "google_query": "Outfit:wght@300;400;500;600;700;800", "requires_upload": False,
    },
    "montserrat": {
        "key": "montserrat", "label": "Montserrat",
        "css_family": "'Montserrat', sans-serif",
        "google_query": "Montserrat:wght@300;400;500;600;700;800", "requires_upload": False,
    },
    "open_sans": {
        "key": "open_sans", "label": "Open Sans",
        "css_family": "'Open Sans', sans-serif",
        "google_query": "Open+Sans:wght@300;400;500;600;700;800", "requires_upload": False,
    },
    "roboto": {
        "key": "roboto", "label": "Roboto",
        "css_family": "'Roboto', sans-serif",
        "google_query": "Roboto:wght@300;400;500;700;900", "requires_upload": False,
    },
    "lato": {
        "key": "lato", "label": "Lato",
        "css_family": "'Lato', sans-serif",
        "google_query": "Lato:wght@300;400;700;900", "requires_upload": False,
    },
    "poppins": {
        "key": "poppins", "label": "Poppins",
        "css_family": "'Poppins', sans-serif",
        "google_query": "Poppins:wght@300;400;500;600;700;800", "requires_upload": False,
    },
    "nunito": {
        "key": "nunito", "label": "Nunito",
        "css_family": "'Nunito', sans-serif",
        "google_query": "Nunito:wght@300;400;500;600;700;800", "requires_upload": False,
    },
    "raleway": {
        "key": "raleway", "label": "Raleway",
        "css_family": "'Raleway', sans-serif",
        "google_query": "Raleway:wght@300;400;500;600;700;800", "requires_upload": False,
    },
    "work_sans": {
        "key": "work_sans", "label": "Work Sans",
        "css_family": "'Work Sans', sans-serif",
        "google_query": "Work+Sans:wght@300;400;500;600;700;800", "requires_upload": False,
    },
    "source_sans_3": {
        "key": "source_sans_3", "label": "Source Sans 3",
        "css_family": "'Source Sans 3', sans-serif",
        "google_query": "Source+Sans+3:wght@300;400;500;600;700;800", "requires_upload": False,
    },
    "rubik": {
        "key": "rubik", "label": "Rubik",
        "css_family": "'Rubik', sans-serif",
        "google_query": "Rubik:wght@300;400;500;600;700;800", "requires_upload": False,
    },
    "karla": {
        "key": "karla", "label": "Karla",
        "css_family": "'Karla', sans-serif",
        "google_query": "Karla:wght@300;400;500;600;700;800", "requires_upload": False,
    },
    "dm_sans": {
        "key": "dm_sans", "label": "DM Sans",
        "css_family": "'DM Sans', sans-serif",
        "google_query": "DM+Sans:wght@300;400;500;600;700;800", "requires_upload": False,
    },
    "pt_sans": {
        "key": "pt_sans", "label": "PT Sans",
        "css_family": "'PT Sans', sans-serif",
        "google_query": "PT+Sans:wght@400;700", "requires_upload": False,
    },
    "ubuntu": {
        "key": "ubuntu", "label": "Ubuntu",
        "css_family": "'Ubuntu', sans-serif",
        "google_query": "Ubuntu:wght@300;400;500;700", "requires_upload": False,
    },
    "barlow": {
        "key": "barlow", "label": "Barlow",
        "css_family": "'Barlow', sans-serif",
        "google_query": "Barlow:wght@300;400;500;600;700;800", "requires_upload": False,
    },
    "mulish": {
        "key": "mulish", "label": "Mulish",
        "css_family": "'Mulish', sans-serif",
        "google_query": "Mulish:wght@300;400;500;600;700;800", "requires_upload": False,
    },
    # Manual de identidad EdoMex (Gobierno del Estado de México) — tipografías
    # comerciales, requieren archivo propio subido por el tenant.
    "gotham": {
        "key": "gotham", "label": "Gotham (EdoMex — requiere archivo propio)",
        "css_family": "'Gotham', sans-serif",
        "google_query": None, "requires_upload": True,
    },
    "bw_modelica": {
        "key": "bw_modelica", "label": "BW Modelica (EdoMex — requiere archivo propio)",
        "css_family": "'BW Modelica', sans-serif",
        "google_query": None, "requires_upload": True,
    },
    "corporative_sans_alt": {
        "key": "corporative_sans_alt", "label": "Corporative Sans Alt (EdoMex — requiere archivo propio)",
        "css_family": "'Corporative Sans Alt', sans-serif",
        "google_query": None, "requires_upload": True,
    },
}

DEFAULT_FONT_KEY = "inter"


def font_import_url(google_query: str) -> str:
    return f"https://fonts.googleapis.com/css2?family={google_query}&display=swap"


def resolve_public_font_fields(
    font_heading: str | None,
    font_body: str | None,
    custom_font_heading_name: str | None,
    has_custom_font_heading_file: bool,
    custom_font_body_name: str | None,
    has_custom_font_body_file: bool,
) -> dict:
    """
    Resuelve las keys de preset guardadas en TenantTheme a los valores ya
    listos para el frontend público (login.html.j2/ThemePublic) — el
    front no necesita conocer FONT_PRESETS, solo consume family/import_url.
    """
    def _resolve(key: str | None, custom_name: str | None, has_file: bool) -> dict:
        preset = FONT_PRESETS.get(key or DEFAULT_FONT_KEY, FONT_PRESETS[DEFAULT_FONT_KEY])
        if preset["requires_upload"]:
            if not has_file:
                # Preset comercial elegido pero sin archivo subido todavía:
                # no hay nada real que cargar — cae al default en vez de
                # anunciar un @font-face que 404ea silenciosamente.
                fallback = FONT_PRESETS[DEFAULT_FONT_KEY]
                return {
                    "family": fallback["css_family"],
                    "import_url": font_import_url(fallback["google_query"]),
                    "has_custom": False,
                }
            family = f"'{custom_name}', sans-serif" if custom_name else preset["css_family"]
            return {"family": family, "import_url": None, "has_custom": True}
        return {
            "family": preset["css_family"],
            "import_url": font_import_url(preset["google_query"]),
            "has_custom": False,
        }

    heading = _resolve(font_heading, custom_font_heading_name, has_custom_font_heading_file)
    body = _resolve(font_body, custom_font_body_name, has_custom_font_body_file)
    return {
        "font_heading_family": heading["family"],
        "font_heading_import_url": heading["import_url"],
        "has_custom_font_heading": heading["has_custom"],
        "font_body_family": body["family"],
        "font_body_import_url": body["import_url"],
        "has_custom_font_body": body["has_custom"],
    }
