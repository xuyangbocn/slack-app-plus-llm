import json
import re
import os
import logging

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from msg_handlers.slack_related.utils import extract_event_details, reply

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Slack client
slack_oauth_token = os.environ["slack_oauth_token"]
slack = WebClient(token=slack_oauth_token)


def handler(slack_event):
    '''
    Overall slack message processing function
    Simply echo of what is received
    '''
    # Get relevant info from Slack event
    msg_details = extract_event_details(slack_event)

    # echo received message
    response = f"I heard you saying: `{msg_details['text'][:100]}`"
    reply(response, msg_details['channel_id'],
          msg_details['event_ts'], slack)

    return
