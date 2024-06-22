import json
import re
import os
import logging

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

slack_oauth_token = os.environ["slack_oauth_token"]
slack = WebClient(token=slack_oauth_token)


def extract_event_details(slack_event):
    '''
    ref: slack event format follow doc below
    https://api.slack.com/events/message.channels
    https://api.slack.com/events/message.groups
    '''

    text, channel_id, thread_ts = "", "", ""
    try:
        msg = slack_event['event']
        text = msg['text']
        channel_id = msg['channel']
        thread_ts = msg['event_ts']
        logger.info(json.dumps(msg, indent=2))
    except KeyError as e:
        logger.warning("Malformed slack event format")

    return dict(text=text, channel_id=channel_id, thread_ts=thread_ts)


def get_user_id(email):
    # Slack SDK Doc: https://slack.dev/python-slack-sdk/api-docs/slack_sdk/
    # https://api.slack.com/methods/users.lookupByEmail
    try:
        resp = slack.users_lookupByEmail(email=email)
    except SlackApiError as e:
        logger.warning(f"User not found: {e}")
        return None
    return resp['user']['id']


def compose_at_user_msg(user_ids):
    '''
    slack message formatting to mention/tag/@ user
    '''
    mentions = " ".join([f"<@{u}>" for u in user_ids])
    text = f'To alert: {mentions}'
    return text


def send_reply(text, channel_id, thread_ts):
    # Slack SDK Doc: https://slack.dev/python-slack-sdk/api-docs/slack_sdk/
    # https://api.slack.com/methods/chat.postMessage
    try:
        result = slack.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=text
        )
        logger.info(result)
    except SlackApiError as e:
        logger.error(f"Error: {e}")

    return


def tag_relevant_user(slack_event):
    # Get relevant info
    msg_details = extract_event_details(slack_event)

    # Extract relevant user email
    emails = re.findall(
        r"(?P<emails>[\w\.-]+@[\w\.-]+\.[\w]+)", msg_details['text'])
    logger.info(f"Found: {emails}")

    # Find user id
    user_ids = [user_id for e in set(emails) if (
        user_id := get_user_id(e)) != None]

    # @user
    if user_ids:
        reply = compose_at_user_msg(user_ids)
        send_reply(reply, msg_details['channel_id'], msg_details['thread_ts'])

    return


def handler(slack_event):
    '''
    Overall slack message processing function
    '''

    tag_relevant_user(slack_event)

    return
