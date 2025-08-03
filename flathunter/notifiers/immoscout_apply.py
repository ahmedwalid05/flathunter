import time
import uuid
import requests
from typing import Any, Dict, Optional, Tuple

import json
import os
from flathunter.config import YamlConfig
from flathunter.logging import logger


_ALLOWED = {"MANDATORY", "OPTIONAL", True}

# Maps payload keys to formFieldConfig keys
FIELD_MAP = {
    "firstname": "firstnameField",
    "lastname": "lastnameField",
    "salutation": "salutationField",
    "emailAddress": "emailAddressField",
    "phoneNumber": "phoneNumberField",
    "address": "addressField",
    "employmentRelationship": "employmentRelationshipField",
    "income": "incomeField",
    "numberOfPersons": "numberOfPersonsField",
    "applicationPackageCompleted": "applicationPackageCompletedField",
    "petsInHousehold": "petsInHouseholdField",
    "hasPets": "petsInHouseholdField",
    "message": "messageField",
}

def _allowed(field_cfg_val: Any) -> bool:
    if isinstance(field_cfg_val, str):
        return field_cfg_val.upper() in _ALLOWED
    return bool(field_cfg_val) in _ALLOWED

def _build_contact_form(required_fields: Dict[str, Any], config: YamlConfig) -> Dict[str, Any]:
    """Builds the contact form, filtered based on what's allowed by formFieldConfig."""
    
    # Read contact form configuration from config
    if config is None:
        raise ValueError("Contact form configuration is required")
    
    logger.debug("Required fields: %s", required_fields)
    # Read from config
    contact_config = config.contact_form_config()
    
    # Build the full contact form data from config
    full = {
        "firstname": contact_config.get("firstname", ""),
        "lastname": contact_config.get("lastname", ""),
        "salutation": contact_config.get("salutation", ""),
        "emailAddress": contact_config.get("emailAddress", ""),
        "phoneNumber": contact_config.get("phoneNumber", ""),
        "address": contact_config.get("address", {}),
        "employmentRelationship": contact_config.get("employmentRelationship", ""),
        "income": contact_config.get("income", ""),
        "numberOfPersons": contact_config.get("numberOfPersons", ""),
        "applicationPackageCompleted": contact_config.get("applicationPackageCompleted", False),
        "hasPets": contact_config.get("hasPets", False),
        "petsInHousehold": contact_config.get("petsInHousehold", ""),
        "message": contact_config.get("message", ""),
        "sendProfile": contact_config.get("sendProfile", False),
        "profileImageUrl": contact_config.get("profileImageUrl", "")
    }

    contact = {}
    for key, cfg_key in FIELD_MAP.items():
        if key == "address":
            if _allowed(required_fields.get("addressField")):
                contact[key] = full.get(key)
        elif _allowed(required_fields.get(cfg_key)):
            contact[key] = full.get(key)

    # Always send if present
    for passthrough in ("sendProfile", "profileImageUrl"):
        if passthrough in full:
            contact[passthrough] = full[passthrough]

    logger.debug("Contact form: %s", contact)
    return contact


def send_is24_contact_request(
    expose_id: str,
    required_fields: Dict[str, Any],
    *,
    timeout: int = 30,
    emb_id: Optional[str] = None,
    emb_st: Optional[int] = None,
    config: YamlConfig
) -> Any:
    """
    Sends a POST contact request to the ImmoScout24 mobile API using a filtered payload.
    """

    if emb_id is None:
        emb_id = str(uuid.uuid4()).upper()
    if emb_st is None:
        emb_st = int(time.time() * 1000)

    url = f"https://api.mobile.immobilienscout24.de/expose/{expose_id}/contact"

    # Get API configuration from config
    api_config = config.immoscout_api_config()

    headers = {
        "Accept": "application/json",
        "X_IS24_CLIENT_ID": api_config.get("client_id", "8181AE4B705C440E80F86EDBE3854DE0"),
        "x-is24-device": "iphone",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-en",
        "x-emb-st": str(emb_st),
        "Content-Type": "application/json",
        "User-Agent": api_config.get("user_agent", "ImmoScout_26.27_26.0_._"),
        "x-emb-id": emb_id,
    }

    contact_form = _build_contact_form(required_fields, config)

    payload = {
        "realEstateType": "apartmentrent",
        "expose.contactForm": contact_form,
        "ssoId": api_config.get("sso_id", "124863683"),
        "supportedScreens": ["profile", "registration", "relocation", "plus", "financing"],
        "entitlements": [],
        "requestCount": 179
    }
    resp = request_with_token_file(
    "POST",
    url,
    headers=headers,
    json_body=payload,
    config=config,
    )

    # request_with_auto_refresh("post", url, )
    # resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    try:
        return resp.json()
    except ValueError:
        return resp.text


import requests

# ---- Config ----
TOKEN_FILE = "is24_tokens.json"  # Default, can be overridden by config


# ---- Tiny token file helpers ----
def load_tokens(path: str = TOKEN_FILE) -> Tuple[str, str]:
    if not os.path.exists(path):
        raise RuntimeError(f"Token file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("access_token", ""), data.get("refresh_token", "")

def save_tokens(access_token: str, refresh_token: str, path: str = TOKEN_FILE) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "updated_at": int(time.time()),
            },
            f,
            ensure_ascii=False,
        )
    os.replace(tmp, path)

def get_token_file_path(config: YamlConfig) -> str:
    """Get token file path from config or use default"""
    api_config = config.immoscout_api_config()
    return api_config.get("token_file", TOKEN_FILE)


# ---- Refresh + request ----
def _refresh_access_token(refresh_token: str, config: YamlConfig, timeout: int = 15) -> Dict[str, Any]:
    logger.info("Refreshing acccess tokens")
    
    # Get OAuth configuration from config
    api_config = config.immoscout_api_config()
    issuer = "https://login.immobilienscout24.de"
    auth_server_id = api_config.get("auth_server_id", "aus1227au6oBg6hGH417")
    token_url = f"{issuer}/oauth2/{auth_server_id}/v1/token"
    client_id = api_config.get("oauth_client_id", "is24-ios-de")
    user_agent = api_config.get("oauth_user_agent", "okta-oidc-ios/3.11.0 iOS/Version 26.0 Device/iPhone14,2/appVersion/26.27")
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "application/json",
        "User-Agent": user_agent,
        "x-emb-id": str(uuid.uuid4()).upper(),
        "x-emb-st": str(int(time.time() * 1000)),
    }
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
    }
    resp = requests.post(token_url, headers=headers, data=data, timeout=timeout)
    resp.raise_for_status()
    tokens = resp.json()
    logger.info(
    "Refreshed tokens: access=%s refresh=%s expires_in=%s",
    tokens.get("access_token", ""),
    tokens.get("refresh_token", ""),
    tokens.get("expires_in"),
    )
    return tokens


def request_with_token_file(
    method: str,
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json_body: Any = None,
    data: Any = None,
    timeout: int = 30,
    token_file: str = TOKEN_FILE,
    config: Optional[YamlConfig] = None,
) -> requests.Response:
    """
    Uses tokens from `token_file`. On 401/403, refreshes and retries once.
    Persists rotated refresh token.
    """
    # Use config token file path if available
    if config is not None:
        token_file = get_token_file_path(config)
    
    access_token, refresh_token = load_tokens(token_file)

    def do_request(tok: str) -> requests.Response:
        hdrs = dict(headers or {})
        hdrs["Authorization"] = f"Bearer {tok}"
        return requests.request(method, url, headers=hdrs, params=params, json=json_body, data=data, timeout=timeout)

    resp = do_request(access_token)
    if resp.status_code not in (401, 403):
        logger.warning("non auth error response: %s", resp.status_code)
        return resp

    # Refresh and retry once
    if config is None:
        raise ValueError("Config is required for token refresh")
    tokens = _refresh_access_token(refresh_token, config)
    logger.info("Saving rotated tokens to %s", token_file)
    new_access = tokens.get("access_token", access_token)
    new_refresh = tokens.get("refresh_token", refresh_token)  # Okta rotates this
    save_tokens(new_access, new_refresh, token_file)

    resp2 = do_request(new_access)
    return resp2
