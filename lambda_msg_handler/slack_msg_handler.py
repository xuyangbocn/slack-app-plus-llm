import json
import re
import os
import logging

from slack_sdk.errors import SlackApiError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


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


def slack_get_user_id(email, slack_client):
    # Slack SDK Doc: https://slack.dev/python-slack-sdk/api-docs/slack_sdk/
    # https://api.slack.com/methods/users.lookupByEmail
    try:
        resp = slack_client.users_lookupByEmail(email=email)
    except SlackApiError as e:
        logger.warning(f"User not found: {e}")
        return None
    return resp['user']['id']


def slack_reply(text, channel_id, thread_ts, slack_client):
    # Slack SDK Doc: https://slack.dev/python-slack-sdk/api-docs/slack_sdk/
    # https://api.slack.com/methods/chat.postMessage
    try:
        resp = slack_client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=text
        )
        logger.info(resp)
    except SlackApiError as e:
        logger.error(f"Error: {e}")

    return


def handler(slack_event, slack_client):
    '''
    Overall slack message processing function
    Mention at relevant users
    '''
    # Get relevant info from Slack event
    msg_details = extract_event_details(slack_event)

    # Extract relevant user email
    emails = re.findall(
        r"(?P<emails>[\w\.-]+@[\w\.-]+\.[\w]+)", msg_details['text'])
    logger.info(f"Found: {emails}")

    # Find user id
    user_ids = [user_id for e in set(emails) if (
        user_id := slack_get_user_id(e, slack_client)) != None]

    # @user
    if user_ids:
        reply = 'Hi {mentions}, please check out this alert.'.format(
            metions=" ".join([f"<@{u}>" for u in user_ids])
        )
        slack_reply(reply, msg_details['channel_id'],
                    msg_details['thread_ts'], slack_client)

    return
