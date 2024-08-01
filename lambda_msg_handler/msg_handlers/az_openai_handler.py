import os
import logging
import json

from openai import AzureOpenAI, AssistantEventHandler

import boto3
import botocore

from slack_sdk.errors import SlackApiError
from msg_handlers.openai_related.utils import get_asst, ask_asst
from msg_handlers.openai_related.asst_tools import tools
from msg_handlers.slack_related.utils import extract_event_details, reply

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# azure openai
az_openai_endpoint = os.environ.get("az_openai_endpoint", "")
az_openai_api_key = os.environ.get("az_openai_api_key", "")
az_openai_api_version = os.environ.get("az_openai_api_version", "")
az_openai_deployment_name = os.environ.get("az_openai_deployment_name", "")
az_openai_asst_instructions = os.environ.get("az_openai_asst_instructions", "")
az_openai_client = AzureOpenAI(
    api_key=az_openai_api_key,
    api_version=az_openai_api_key,
    azure_endpoint=az_openai_endpoint,
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
        thread = az_openai_client.beta.threads.create()
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
        az_openai_client,
        name="az_openai_on_slack",
        description="Azure OpenAI on slack",
        instructions=az_openai_asst_instructions,
        model=az_openai_deployment_name,
        tools=tool_defs
    )

    # Get exsiting / Create new thread
    asst_thread_id = get_asst_thread_id(
        msg_details['channel_id'], msg_details['thread_ts'])

    # Call OpenAI Assistant
    response = ask_asst(
        az_openai_client, asst.id, asst_thread_id, msg_details['text'],
        tool_functions)

    # respond on slack thread
    logger.info(f"Send response to slack thread")
    reply(response, msg_details['channel_id'],
          msg_details['event_ts'], slack_client)

    return
