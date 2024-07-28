import json
import re
import os
import logging

from slack_sdk.errors import SlackApiError

from msg_handlers.slack_related.utils import extract_event_details, reply

logger = logging.getLogger()


def handler(slack_event, slack_client):
    '''
    Overall slack message processing function
    Simply echo of what is received
    '''
    # Get relevant info from Slack event
    msg_details = extract_event_details(slack_event)

    # echo received message
    response = f"I heard you saying: `{msg_details['text'][:100]}`"
    reply(response, msg_details['channel_id'],
          msg_details['event_ts'], slack_client)

    return
