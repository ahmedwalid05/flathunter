import json
import requests
from typing import Dict, Any

from flathunter.abstract_processor import Processor
from flathunter.config import YamlConfig
from flathunter.logging import logger

# Import the function we wrote earlier
from flathunter.notifiers.immoscout_apply import send_is24_contact_request

class SenderApplier(Processor):
    """Class that applies for a listing using the ImmoScout24 API"""

    def __init__(self, config: YamlConfig):
        self.config = config

    def process_expose(self, expose: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply for a given expose using the ImmoScout24 contact API.
        :param expose: Dictionary containing at least the expose ID and search ID
        :return: The API response
        """
        expose_id = expose.get("id")

        if not expose_id:
            logger.error("Expose missing 'id' or 'search_id': %s", expose)
            return expose

        try:
            response = send_is24_contact_request(
                expose_id=expose_id,
                required_fields=expose["required_fields"],
                config=self.config,
            )
            logger.info("Applied to expose %s: %s", expose_id, response)
            expose["application_response"] = response
        except requests.HTTPError as e:
            response = e.response.json()
            logger.error("HTTP error while applying for expose %s: %s. Response: %s", expose_id, e, response)
            expose["application_response"] = {"error": str(e)}

        return expose