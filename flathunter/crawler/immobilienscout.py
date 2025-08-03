"""Expose crawler for ImmobilienScout (API-based, no Chrome)."""
import datetime
import re
import requests
from typing import List

from jsonpath_ng.ext import parse
from bs4 import BeautifulSoup

from flathunter.abstract_crawler import Crawler
from flathunter.logging import logger
from flathunter.utils.immoscout_extractor import extract_full_listing
from flathunter.utils.immoscout_web_translator import convert_web_to_mobile

STATIC_URL_PATTERN = re.compile(r'https://www\.immobilienscout24\.de')

HEADERS = {
    "User-Agent": "ImmoScout24_1410_30_._",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

FALLBACK_IMAGE_URL = (
    "https://www.static-immobilienscout24.de/statpic/placeholder_house/"
    "496c95154de31a357afa978cdb7f15f0_placeholder_medium.png"
)



class Immobilienscout(Crawler):
    """Implementation of Crawler interface for ImmobilienScout using the public mobile API."""


    def __init__(self, config):
        super().__init__(config)

    def crawl(self, url, max_pages=None):
        return self.get_results(url, max_pages)
    
    def parse_listing(self, expose: dict) -> dict:
        images = []
        title_pic = expose.get("titlePicture", {})
        if "full" in title_pic:
            images.append(self.strip_size(title_pic["full"]))
        elif "preview" in title_pic:
            images.append(self.strip_size(title_pic["preview"]))


        # attributes come as strings like '860 €', '78 m²', '3 Zi.'
        price = self._pick_attr(expose, "€")
        size = self._pick_attr(expose, "m²")
        rooms = self._pick_attr(expose, "Zi.")

        object_id = int(expose.get("id", ""))

        return {
            "id": object_id,
            "url": f"https://www.immobilienscout24.de/expose/{object_id}",
            "image": images[0] if images else FALLBACK_IMAGE_URL,
            "images": images,
            "title": self._clean(expose.get("title", "")),
            "address": self._clean((expose.get("address") or {}).get("line", "")),
            "crawler": "Immoscout",
            "price": price, 
            "size": size,
            "rooms": rooms,
            "published": self._clean(expose.get("published", "")),
            "is_private": expose.get("isPrivate", False),
            "listing_type": expose.get("listingType", ""),
            "real_estate_type": expose.get("realEstateType", ""),
        }
    def get_results(self, search_url, max_pages=None):
        """Loads exposes from the ImmoScout mobile API."""
        mobile_url=convert_web_to_mobile(search_url) +"&sorting=-firstactivation&features=adKeysAndStringValues,virtualTour,contactDetails,viareporting,nextgen,calculatedTotalRent,listingsInListFirstSummary,xxlListingType,quickfilters,grouping,projectsInAllRealestateTypes,fairPrice"
        response = requests.post(
        mobile_url,
        headers=HEADERS,
        json={"supportedResultListTypes": [], "userData": {}},
        timeout=15,
        )
        if response.status_code != 200:
            logger.error(f"Error fetching data: {response.status_code} {response.text}")
            return []

        response_body = response.json()
        listings = []
        for item in response_body.get("resultListItems", []):
            if item.get("type") != "EXPOSE_RESULT":
                continue

            expose = item.get("item", {})
    
            listing = self.parse_listing(expose)
            listings.append(listing)
    
        return listings
    
    def crawl_singular(self, url, expose):
        return self.get_expose_details(expose)

    def get_expose_details(self, expose):
        """Loads additional details for an expose from the web page."""
        expose_url=f"https://api.mobile.immobilienscout24.de/expose/{expose['id']}"
        
        response = requests.get(expose_url, headers=HEADERS, timeout=15)
        full_expose = extract_full_listing(response.json())
      
        return {**expose, **full_expose}

    def _clean(self, s: str) -> str:
        return (s or "").replace("\xa0", " ").strip()

    def _pick_attr(self, expose, needle):
        """Return the first attribute.value that contains `needle`."""
        for a in expose.get("attributes", []):
            val = a.get("value", "")
            if needle in val:
                return self._clean(val)
        return ""
    def strip_size(self, url):
        return url.split('/ORIG')[0]
