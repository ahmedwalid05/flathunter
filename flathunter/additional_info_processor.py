import traceback
import requests
from typing import Dict

from flathunter.logging import logger
from flathunter.abstract_processor import Processor
from flathunter.config import Config
from flathunter.captcha.captcha_solver import CaptchaUnsolvableError
from flathunter.exceptions import ConfigException

class AdditionalInfoProcessor(Processor):
    def __init__(self, config: Config):
        self.config = config
        
    def process_expose(self, expose: Dict) -> Dict:
        url= expose['url']
        new_expose = expose
        for searcher in self.config.searchers():
            try:
                new_expose = searcher.crawl_singular(url, new_expose)
            except CaptchaUnsolvableError:
                logger.info("Error while scraping url %s: the captcha was unsolvable", url)
            except requests.exceptions.RequestException:
                logger.info("Error while scraping url %s:\n%s", url, traceback.format_exc())
            except Exception as e:
                logger.info("Error while scraping url %s:\n%s", url, traceback.format_exc())
        return new_expose
