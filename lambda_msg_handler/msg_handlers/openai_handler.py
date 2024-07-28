import os
import logging

from openai import OpenAI
import boto3
import botocore

from slack_sdk.errors import SlackApiError
from msg_handlers.openai_related.utils import get_asst, EventHandler
from msg_handlers.openai_related.function_call import functions
from msg_handlers.slack_related.utils import extract_event_details, reply

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# gpt model
openai_gpt_model = os.environ.get("openai_gpt_model", "gpt-4o")
openai_api_key = os.environ.get("openai_api_key", "")
openai_client = OpenAI(
    api_key=openai_api_key
)

# function call available
available_functions = functions['declaration']
tools = functions['description']

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
        instructions=os.getenv('chatgpt_instruction', ""),
        model=openai_gpt_model,
        tools=tools  # to be enhanced
    )

    # Get exsiting / Create new thread
    asst_thread_id = get_asst_thread_id(
        msg_details['channel_id'], msg_details['thread_ts'])

    # Call OpenAi
    response = ""
    openai_client.beta.threads.messages.create(
        thread_id=asst_thread_id,
        role="user",
        content=msg_details['text']
    )
    with openai_client.beta.threads.runs.stream(
        thread_id=asst_thread_id,
        assistant_id=asst.id,
        event_handler=EventHandler(
            openai_client,
            functions=available_functions,  # to be enhanced
            extra_function_call_args={}  # to be enhanced
        ),
    ) as stream:
        for event in stream:
            logger.info(f"Stream event: {event.event}")
            if event.event == "thread.message.delta" and event.data.delta.content:
                response += event.data.delta.content[0].text.value
            # if event.event == 'thread.run.requires_action':
            #     # When tool_call=function needed, run status will turn 'requires_action'
            #     event_handler.handle_requires_action(event.data)

    # respond on slack thread
    logger.info(f"Send response to slack thread")
    reply(response, msg_details['channel_id'],
          msg_details['event_ts'], slack_client)

    return
