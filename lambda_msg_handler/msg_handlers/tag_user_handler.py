import json
import re
import os
import logging

from slack_sdk.errors import SlackApiError

from msg_handlers.slack_related.utils import extract_event_details, get_user_id, reply

logger = logging.getLogger()


def handler(slack_event, slack_client):
    '''
    Overall slack message processing function
    Tag at relevant users
    '''
    # Get relevant info from Slack event
    msg_details = extract_event_details(slack_event)

    # Extract relevant user email
    emails = re.findall(
        r"(?P<emails>[\w\.-]+@[\w\.-]+\.[\w]+)", msg_details['text'])
    logger.info(f"Found: {emails}")

    # Find user id
    user_ids = [user_id for e in set(emails) if (
        user_id := get_user_id(e, slack_client)) != None]

    # @user
    if user_ids:
        reply_msg = 'Hi {mentions}, please check out this alert.'.format(
            metions=" ".join([f"<@{u}>" for u in user_ids])
        )
        reply(reply_msg, msg_details['channel_id'],
              msg_details['event_ts'], slack_client)

    return
