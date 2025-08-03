import re
from typing import Any, Dict, List, Optional

FALLBACK_IMAGE_URL = "https://via.placeholder.com/800x600?text=No+image"


def _clean(s: Optional[str]) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def _get_section(data: Dict[str, Any], t: str) -> Optional[Dict[str, Any]]:
    for s in data.get("sections", []):
        if s.get("type") == t:
            return s
    return None


def _get_sections(data: Dict[str, Any], t: str) -> List[Dict[str, Any]]:
    return [s for s in data.get("sections", []) if s.get("type") == t]


def _extract_images(data: Dict[str, Any]) -> List[Dict[str, str]]:
    images: List[Dict[str, str]] = []
    for media_sec in _get_sections(data, "MEDIA"):
        for m in media_sec.get("media", []):
            if m.get("type") == "PICTURE":
                images.append({
                    "caption": m.get("caption", ""),
                    "url": strip_size(m.get("fullImageUrl") or m.get("previewImageUrl") or m.get("imageUrlForWeb"))
                })
    return images


def _extract_text_areas(data: Dict[str, Any]) -> Dict[str, str]:
    """Extract all TEXT_AREA blocks as {title: text}."""
    texts = {}
    for s in _get_sections(data, "TEXT_AREA"):
        title = s.get("title", "")
        texts[title] = _clean(s.get("text", ""))
    return texts


def _extract_attribute_lists(data: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """Collect all ATTRIBUTE_LIST sections as {section_title: {label: text}}."""
    out = {}
    for s in _get_sections(data, "ATTRIBUTE_LIST"):
        section_data = {}
        for a in s.get("attributes", []):
            label = _clean(a.get("label", ""))
            section_data[label] = _clean(a.get("text", ""))
        out[s.get("title", "")] = section_data
    return out


def strip_size(url):
    return url.split('/ORIG')[0] if url else url


def _extract_required_fields(data: Dict[str, Any]) -> Dict[str, str]:
    """
    Extracts required fields from formFieldConfig inside contact.contactData.
    Returns {fieldName: status} where status is MANDATORY/OPTIONAL/...
    """
    required_fields = {}
    contact_data = data.get("contact", {}).get("contactData", {})
    form_cfg = contact_data.get("formFieldConfig", {})

    for key, value in form_cfg.items():
        required_fields[key] = value

    return required_fields


def extract_full_listing(data: Dict[str, Any]) -> Dict[str, Any]:
    header = data.get("header", {})
    object_id = str(header.get("id") or data.get("adTargetingParameters", {}).get("obj_scoutId", ""))

    # Title
    title_sec = _get_section(data, "TITLE")
    title = _clean(title_sec.get("title", "")) if title_sec else ""

    # Address
    map_sec = _get_section(data, "MAP")
    address = ""
    if map_sec:
        address = _clean(" ".join(filter(None, [map_sec.get("addressLine1"), map_sec.get("addressLine2")])))

    # Images
    images_info = _extract_images(data)
    image_urls = [img["url"] for img in images_info if img.get("url")]

    # Top attributes (rooms, size, price)
    price = ""
    size = ""
    rooms = ""
    top_attr = _get_section(data, "TOP_ATTRIBUTES")
    if top_attr:
        for a in top_attr.get("attributes", []):
            label = a.get("label", "").lower()
            text = _clean(a.get("text", ""))
            if "zimmer" in label:
                rooms = text
            elif "wohnfläche" in label:
                size = text
            elif "kaltmiete" in label:
                price = text

    # Attribute lists
    attribute_lists = _extract_attribute_lists(data)

    # Text sections (description, Ausstattung, Lage, etc.)
    text_sections = _extract_text_areas(data)
    description = text_sections.get("Objektbeschreibung", "")

    # Agent details
    agent_info = {}
    agent_sec = _get_section(data, "AGENTS_INFO")
    if agent_sec:
        agent_info = {
            "company": agent_sec.get("company", ""),
            "name": agent_sec.get("name", ""),
            "logoUrl": agent_sec.get("logoUrl", "")
        }

    # Real estate type
    real_estate_type = header.get("realEstateType", "")

    # Private or not
    is_private = data.get("adTargetingParameters", {}).get("obj_privateOffer", "").lower() == "true"

    # Required contact fields
    required_fields = _extract_required_fields(data)

    return {
        "id": object_id,
        "url": f"https://www.immobilienscout24.de/expose/{object_id}" if object_id else "",
        "image": image_urls[0] if image_urls else FALLBACK_IMAGE_URL,
        "images": image_urls,
        "title": title,
        "size": size,
        "rooms": rooms,
        "contact_details": agent_info,
        "built_in_kitchen": attribute_lists.get("Hauptkriterien", {}).get("Einbauküche:", ""),
        "balcony": attribute_lists.get("Hauptkriterien", {}).get("Balkon/Terrasse:", ""),
        "is_private": is_private,
        "listing_type": "",
        "real_estate_type": real_estate_type,
        # Extra info
        "description": description,
        "text_sections": text_sections,
        "attributes": attribute_lists,
        "agent_info": agent_info,
        "required_fields": required_fields  # <-- Added required fields
    }
