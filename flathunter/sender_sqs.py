"""Functions and classes related to sending SQS messages"""
import json
from typing import Dict
import boto3

from flathunter.abstract_notifier import Notifier
from flathunter.abstract_processor import Processor
from flathunter.config import YamlConfig
from flathunter.logging import logger


class SenderSQS(Processor, Notifier):
    """Expose processor that sends SQS events """

    def __init__(self, config: YamlConfig) -> None:
        self.config = config
        sqs_config= self.config.sqs_details()
        self.sqs = boto3.client(
            "sqs",
            aws_access_key_id=sqs_config["access_key_id"],
            aws_secret_access_key=sqs_config["secret_access_key"],
            region_name='us-east-1'           
            )
        self.queue_url = sqs_config["sqs_queue_name"]
        logger.info("SQS started")
        

    def process_expose(self, expose: Dict) -> Dict:
        """Send a message to a sqs queue channel describing the expose"""
        message = json.dumps(expose)
        self.notify(message)
        return expose

    def notify(self, message: str) -> None:
        """Send message to a sqs queue"""
        self.__send_message(message)

    def __send_message(self, message: str) -> None:
        """Send message to a sqs queue"""
        logger.debug(('Sending sqs event to queue:', self.queue_url))
        response = self.sqs.send_message(
            QueueUrl=self.queue_url,
            MessageBody=message
        )
        logger.debug(('Sent sqs message with id: ', response["MessageId"]))
