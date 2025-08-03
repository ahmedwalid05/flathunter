"""Utilities for ImmobilienScout24: convert web search URLs to the public mobile API URLs."""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, MutableMapping
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse, quote

import re

STATIC_URL_PATTERN = re.compile(r"https://www\.immobilienscout24\.de")


# --- Constants ----------------------------------------------------------------

PARAM_NAME_MAP: Mapping[str, str] = {
    "heatingtypes": "heatingtypes",
    "haspromotion": "haspromotion",
    "numberofrooms": "numberofrooms",
    "livingspace": "livingspace",
    "energyefficiencyclasses": "energyefficiencyclasses",
    "exclusioncriteria": "exclusioncriteria",
    "equipment": "equipment",
    "petsallowedtypes": "petsallowedtypes",
    "price": "price",
    "constructionyear": "constructionyear",
    "apartmenttypes": "apartmenttypes",
    "pricetype": "pricetype",
    "floor": "floor",
    "geocodes": "geocodes",
    "geocoordinates": "geocoordinates",
    "shape": "shape",
    "sorting": "sorting",
    "newbuilding": "newbuilding",
}

EQUIPMENT_MAP: Mapping[str, str] = {
    "parking": "parking",
    "cellar": "cellar",
    "builtinkitchen": "builtInKitchen",
    "lift": "lift",
    "garden": "garden",
    "guesttoilet": "guestToilet",
    "balcony": "balcony",
    "handicappedaccessible": "handicappedAccessible",
}

REAL_ESTATE_TYPE: Mapping[str, str] = {
    "haus-mieten": "houserent",
    "wohnung-mieten": "apartmentrent",
    "wohnung-kaufen": "apartmentbuy",
    "haus-kaufen": "housebuy",
}

WEB_PATH_TO_APARTMENT_EQUIPMENT_MAP: Mapping[str, Mapping[str, Iterable[str] | bool]] = {
    # Category "Balkon/Terrasse"
    "wohnung-mit-balkon-mieten": {"equipment": ["balcony"]},
    "wohnung-mit-garten-mieten": {"equipment": ["garden"]},
    # Category "Wohnungstyp"
    "souterrainwohnung-mieten": {"apartmenttypes": ["halfbasement"]},
    "erdgeschosswohnung-mieten": {"apartmenttypes": ["groundfloor"]},
    "hochparterrewohnung-mieten": {"apartmenttypes": ["raisedgroundfloor"]},
    "etagenwohnung-mieten": {"apartmenttypes": ["apartment"]},
    "loft-mieten": {"apartmenttypes": ["loft"]},
    "maisonette-mieten": {"apartmenttypes": ["maisonette"]},
    "terrassenwohnung-mieten": {"apartmenttypes": ["terracedflat"]},
    "penthouse-mieten": {"apartmenttypes": ["penthouse"]},
    "dachgeschosswohnung-mieten": {"apartmenttypes": ["roofstorey"]},
    # Category "Ausstattung"
    "wohnung-mit-garage-mieten": {"equipment": ["parking"]},
    "wohnung-mit-einbaukueche-mieten": {"equipment": ["builtinkitchen"]},
    "wohnung-mit-keller-mieten": {"equipment": ["cellar"]},
    # Category "Merkmale"
    "neubauwohnung-mieten": {"newbuilding": True},
    "barrierefreie-wohnung-mieten": {"equipment": ["handicappedaccessible"]},
}


# --- Public API ---------------------------------------------------------------

def convert_web_to_mobile(web_url: str) -> str:
    """
    Convert an ImmoScout web *search* URL to the equivalent public mobile API URL.

    Parameters
    ----------
    web_url : str
        A URL that starts with https://www.immobilienscout24.de/Suche/...

    Returns
    -------
    str
        The mobile API URL (search/list) with translated query parameters.

    Raises
    ------
    ValueError
        If the URL is invalid, does not look like a search URL, or uses an unsupported mode (shape).
    """
    try:
        parsed = urlparse(web_url)
    except Exception as exc:  # pragma: no cover
        raise ValueError(f"Invalid URL: {web_url}") from exc

    if not STATIC_URL_PATTERN.match(f"{parsed.scheme}://{parsed.netloc}"):
        raise ValueError("URL must point to www.immobilienscout24.de")

    segments = [seg for seg in parsed.path.split("/") if seg]
    # Expect something like /Suche/de/nordrhein-westfalen/duesseldorf/wohnung-mieten
    if len(segments) < 2 or segments[0] != "Suche":
        raise ValueError(f"Unexpected path format: {parsed.path}. Expected '/Suche' in the path.")

    if "shape" in segments:
        # The original JS throws. We mirror that.
        raise ValueError("Shape is currently not supported using Immoscout")

    real_type_key = segments[-1]
    real_type = REAL_ESTATE_TYPE.get(real_type_key)
    additional_params_from_path: Dict[str, Iterable[str] | bool] | None = None

    if real_type is None:
        # Maybe it's one of the SEO apartment sub-paths that implies equipment / type.
        if real_type_key in WEB_PATH_TO_APARTMENT_EQUIPMENT_MAP:
            additional_params_from_path = dict(WEB_PATH_TO_APARTMENT_EQUIPMENT_MAP[real_type_key])
            real_type = REAL_ESTATE_TYPE["wohnung-mieten"]
        else:
            raise ValueError(f"Real estate type not found: {real_type_key}")

    # Parse and clean query params
    raw_params = parse_qs(parsed.query, keep_blank_values=False)
    web_params: Dict[str, List[str]] = {
        k: v for k, v in raw_params.items()
        if k != "enteredFrom" and k in PARAM_NAME_MAP
    }

    # Detect "radius" mode
    is_radius = "radius" in segments

    # Build mobile params
    mobile_params: MutableMapping[str, object] = {
        "searchType": "radius" if is_radius else "region",
        "realestatetype": real_type,
    }
    if not is_radius:
        # Build /de/.../... geocode from the first 3 segments following /Suche
        # e.g. /Suche/de/nordrhein-westfalen/duesseldorf/wohnung-mieten
        if len(segments) >= 4:  # Suche, de, nordrhein-westfalen, duesseldorf, ...
            geocodes = "/" + "/".join(segments[1:4])
            mobile_params["geocodes"] = geocodes
    if additional_params_from_path:
        mobile_params.update(additional_params_from_path)

    # Copy / translate params
    for key, values in web_params.items():
        if key == "equipment":
            # merge, map and de-duplicate
            mapped_vals = []
            for v in values:
                for item in str(v).split(","):
                    mapped = EQUIPMENT_MAP.get(item.lower())
                    if mapped:
                        mapped_vals.append(mapped)
            existing = mobile_params.get("equipment", [])
            if not isinstance(existing, list):
                existing = [existing] if existing else []
            mobile_params["equipment"] = list(dict.fromkeys([*existing, *mapped_vals]))
        else:
            # Keep original values but collapse lists into comma-separated strings
            if len(values) == 1:
                mobile_params[PARAM_NAME_MAP[key]] = values[0]
            else:
                mobile_params[PARAM_NAME_MAP[key]] = ",".join(values)

    # The JS version always targets /search/list
    base = "https://api.mobile.immobilienscout24.de/search/list"

    # Ensure arrays are joined with commas (as the JS library's arrayFormat=comma did)
    def normalize(v: object) -> str:
        if isinstance(v, list):
            return ",".join(map(str, v))
        return str(v)

    qs = urlencode({k: normalize(v) for k, v in mobile_params.items()}, doseq=False, safe=",")

    return f"{base}?{qs}"