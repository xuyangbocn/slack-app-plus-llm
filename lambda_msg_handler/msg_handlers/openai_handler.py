import os
import logging
import json

from openai import OpenAI, AssistantEventHandler

import boto3
import botocore

from slack_sdk.errors import SlackApiError
from msg_handlers.openai_related.utils import get_asst, ask_asst
from msg_handlers.openai_related.asst_tools import tools
from msg_handlers.slack_related.utils import extract_event_details, reply

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# gpt model
openai_gpt_model = os.environ.get("openai_gpt_model", "gpt-4o")
openai_api_key = os.environ.get("openai_api_key", "")
openai_asst_instructions = os.environ.get("openai_asst_instructions", "")
openai_client = OpenAI(
    api_key=openai_api_key
)

# tools available for assistant to use
tool_defs = tools['definitions']

# tool function declaration
tool_functions = tools['tool_functions']

# aws boto3
ddb_client = boto3.client("dynamodb")
ddb_table = os.environ["ddb_asst_thread"]


def get_asst_thread_id(slack_channel_id, slack_thread_ts):
    '''
    DDB gpt_thread keeps the mapping from slack channel id + thread ts ==> asst_thread_id
    This function will find the gpt thread id for existing slack thread
    If not found (i.e. a new slack thread), it will create a gpt thread and insert to DDB
    '''
    ddb_search_key = {
        "slack_channel_id": {"S": slack_channel_id},
        "slack_thread_ts": {"S": slack_thread_ts},
    }
    asst_thread_id = None

    # search thread in DDB
    try:
        resp = ddb_client.get_item(
            TableName=ddb_table,
            Key=ddb_search_key,
        )
        asst_thread_id = resp["Item"]["asst_thread_id"]['S']
        logger.info(f'DDB record found for thread: {asst_thread_id}')
    except (botocore.exceptions.ClientError, KeyError) as exNotFound:
        # if thread not found in DDB
        thread = openai_client.beta.threads.create()
        asst_thread_id = thread.id
        try:
            ddb_client.update_item(
                TableName=ddb_table,
                Key=ddb_search_key,
                UpdateExpression="SET asst_thread_id=:asst_thread_id",
                ExpressionAttributeValues={
                    ":asst_thread_id": {"S": asst_thread_id}
                }
            )
            logger.info(f'DDB record created for thread: {asst_thread_id}')
        except botocore.exceptions.ClientError as ex:
            logger.warning(ex)
            pass

    return asst_thread_id


def handler(slack_event, slack_client):
    '''
    Overall slack message processing function
    Simple pass-on to Chatgpt
    '''
    # Get relevant info from Slack event
    msg_details = extract_event_details(slack_event)

    # Get Chatgpt assistant
    asst = get_asst(
        openai_client,
        name="chatgpt_on_slack",
        description="Chatgpt on slack",
        instructions=openai_asst_instructions,
        model=openai_gpt_model,
        tools=tool_defs
    )

    # Get exsiting / Create new thread
    asst_thread_id = get_asst_thread_id(
        msg_details['channel_id'], msg_details['thread_ts'])

    # Call OpenAI Assistant
    response = ask_asst(
        openai_client, asst.id, asst_thread_id, msg_details['text'],
        tool_functions)

    # respond on slack thread
    logger.info(f"Send response to slack thread")
    reply(response, msg_details['channel_id'],
          msg_details['event_ts'], slack_client)

    return
