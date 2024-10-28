import logging
import json

from slack_sdk.errors import SlackApiError
from slackstyler import SlackStyler


logger = logging.getLogger()

# Slack SDK Doc: https://slack.dev/python-slack-sdk/api-docs/slack_sdk/
# Create a styler instance
styler = SlackStyler()


def extract_event_details(slack_event):
    '''
    ref: slack event format follow doc below
    https://api.slack.com/events/message.channels
    https://api.slack.com/events/message.groups
    '''

    text, channel_id, event_ts, thread_ts, user = "", "", "", "", ""
    try:
        msg = slack_event['event']
        text = msg['text']
        channel_id = msg['channel']
        event_ts = msg['event_ts']
        thread_ts = msg.get('thread_ts', event_ts)
        user = msg.get('user', 'unknown')
        logger.info(json.dumps(msg, indent=2))
    except KeyError as e:
        logger.warning("Malformed slack event format")

    return dict(text=text, channel_id=channel_id, event_ts=event_ts, thread_ts=thread_ts, user=user)


def get_user_id(email, slack_client):
    # https://api.slack.com/methods/users.lookupByEmail
    try:
        resp = slack_client.users_lookupByEmail(email=email)
    except SlackApiError as e:
        logger.warning(f"User not found: {e}")
        return None
    return resp['user']['id']


def get_user_email(user_id, slack_client):
    # https://api.slack.com/methods/users.info
    try:
        resp = slack_client.users_info(user=user_id)
    except SlackApiError as e:
        logger.error(f"User id not found {user_id}: {e}")
        return None
    return resp['user']['profile']['email']


def reply(text, channel_id, thread_ts, slack_client, styled=True):
    # https://api.slack.com/methods/chat.postMessage
    try:
        text = styler.convert(text) if styled else text
    except:
        text = text

    try:
        resp = slack_client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=text
        )
        logger.info(resp)
    except SlackApiError as e:
        logger.error(f"Error: {e}")
        resp = None

    return resp
