import os
import logging
import json

from openai import OpenAI, AssistantEventHandler

import boto3
import botocore
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from msg_handlers.llm_tools import tools
from msg_handlers.llm_utils.agent import Agent
from msg_handlers.slack_related.utils import extract_event_details, reply

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Slack client
slack_oauth_token = os.environ["slack_oauth_token"]
slack = WebClient(token=slack_oauth_token)

# gpt model
openai_gpt_model = os.environ.get("openai_gpt_model", "gpt-4o")
openai_api_key = os.environ.get("openai_api_key", "")
# openai_asst_instructions = os.environ.get("openai_asst_instructions", "")
openai_client = OpenAI(
    api_key=openai_api_key
)

# tools available for assistant to use
tool_defs = tools['definitions']

# tool function declaration
tool_functions = tools['tool_functions']

# Initialize an LLM Agent
agent = Agent(
    openai_client,
    name='chatgpt_on_slack',
    description="Chatgpt on slack",
    model=openai_gpt_model,
    # sentences=[openai_asst_instructions],
    sentences=[
        "AWS Reinvent is a large conference event which will be hosted in Las vegas in Pacific Standard Time from 2nd to 6th of December 2024.",
        "During the conference, thousands of varied types of sessions and activities are organized at various timing and various hotel venues in Las Vegas",
        "These sessions cover different topics, touch different level of technicality and target varied audiences.",
        "You need to assist user to find suitable sessions based on their interest. Please always include session code for easy reference.",
        "You also need to help user to plan sessions based on the session starting and end timing.",
        "You can use function calls to search for sessions from AWS",
        "Travel between different hotels will take up to 30 minute, so leave buffer time between sessions when you do planning.",
    ],
    tools=tool_defs,
    tool_functions=tool_functions
)

# aws boto3
ddb_client = boto3.client('dynamodb')
ddb_asst_thread_table = os.environ['ddb_asst_thread']
ddb_chat_completion_table = os.environ['ddb_chat_completion']


def get_asst_thread_id(slack_channel_id, slack_thread_ts, slack_user_id=''):
    '''
    DDB ddb_asst_thread keeps the mapping from slack channel id + thread ts ==> asst_thread_id
    This function will find the assistant thread id for existing slack thread
    If not found (i.e. a new slack thread), it will create a assistant thread and insert to DDB
    '''
    ddb_search_key = {
        "slack_channel_id": {"S": slack_channel_id},
        "slack_thread_ts": {"S": slack_thread_ts},
    }
    asst_thread_id = None

    # search thread in DDB
    try:
        resp = ddb_client.get_item(
            TableName=ddb_asst_thread_table,
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
                TableName=ddb_asst_thread_table,
                Key=ddb_search_key,
                UpdateExpression="SET asst_thread_id=:asst_thread_id, slack_user_id=:slack_user_id",
                ExpressionAttributeValues={
                    ":asst_thread_id": {"S": asst_thread_id},
                    ":slack_user_id": {"S": slack_user_id},
                }
            )
            logger.info(f'DDB record created for thread: {asst_thread_id}')
        except botocore.exceptions.ClientError as ex:
            logger.warning(ex)
            pass

    return asst_thread_id


def fetch_slack_thread(slack_channel_id, slack_thread_ts):
    '''
    Fetch all messages in the thread stored in DDB
    '''
    try:
        resp = ddb_client.query(
            TableName=ddb_chat_completion_table,
            Limit=25,
            ScanIndexForward=False,  # descending order
            KeyConditionExpression='slack_channel_id_thread_ts = :slack_channel_id_thread_ts',
            ExpressionAttributeValues={
                ':slack_channel_id_thread_ts': {
                    'S': f'{slack_channel_id};{slack_thread_ts}',
                }
            }
        )
        logger.info(
            f'DDB records {resp.get("count", "not")} found: {slack_channel_id};{slack_thread_ts}')

        # reverse descending order to chronological ascending order
        messages = [
            {'role': i['role']['S'], 'content': i['content']['S']}
            for i in resp.get('Items')[::-1]
        ]
    except (botocore.exceptions.ClientError, KeyError) as exNotFound:
        logger.info(f'No existing threads: {exNotFound}')
        messages = []
        pass

    return messages


def save_slack_event(slack_channel_id, slack_thread_ts, slack_event_ts, role, content, slack_user_id=''):
    ddb_search_key = {
        'slack_channel_id_thread_ts': {'S': f'{slack_channel_id};{slack_thread_ts}'},
        'slack_event_ts': {'S': slack_event_ts},
    }
    try:
        ddb_client.update_item(
            TableName=ddb_chat_completion_table,
            Key=ddb_search_key,
            UpdateExpression='SET #r=:role, content=:content, slack_user_id=:slack_user_id',
            ExpressionAttributeValues={
                ':role': {'S': role},
                ':content': {'S': content},
                ':slack_user_id': {'S': slack_user_id},
            },
            ExpressionAttributeNames={
                "#r": "role"
            }
        )
        logger.info(
            f'DDB record created for {role}[{slack_user_id}]: {slack_channel_id};{slack_thread_ts}')
    except botocore.exceptions.ClientError as ex:
        logger.error(f'DDB record fail to create: {ex}')
        pass
    return


def handler_via_assistant(slack_event):
    '''
    Overall slack message processing function
    Simple pass-on to Chatgpt
    '''
    # Get relevant info from Slack event
    msg_details = extract_event_details(slack_event)

    # Get exsiting / Create new thread
    asst_thread_id = get_asst_thread_id(
        msg_details['channel_id'], msg_details['thread_ts'], msg_details['user'])

    # Call OpenAI Assistant
    response = agent.ask_assistant(
        user=msg_details['user'],
        asst_thread_id=asst_thread_id,
        message=msg_details['text'],
    )

    # respond on slack thread
    logger.info(f"Send response to slack thread")
    reply(response, msg_details['channel_id'],
          msg_details['event_ts'], slack)

    return


def handler_via_chat_completion(slack_event):
    '''
    Overall slack message processing function
    Re-collect thread history and call Az OpenAI chat completion
    '''
    # Get relevant info from Slack event
    msg_details = extract_event_details(slack_event)

    # Re-collect past message in the thread
    thread_messages = fetch_slack_thread(
        msg_details['channel_id'], msg_details['thread_ts']
    ) + [
        {'role': 'user', 'content': msg_details['text']}
    ]

    # save latest thread msg
    save_slack_event(msg_details['channel_id'], msg_details['thread_ts'],
                     msg_details['event_ts'], 'user', msg_details['text'],
                     msg_details['user'])

    # pass whole message history to chat completion
    logger.info(f'Call chat completion api')
    logger.info(f'{"\n".join([str(t)[:70] for t in thread_messages])}')
    response = agent.chat_completion(
        user=msg_details['user'],
        messages=thread_messages,
    )

    # respond on slack thread
    logger.info(f'Send response to slack thread')
    resp = reply(response, msg_details['channel_id'],
                 msg_details['thread_ts'], slack)

    # save latest response
    save_slack_event(msg_details['channel_id'], msg_details['thread_ts'],
                     resp['ts'], 'assistant', response,
                     msg_details['user'])
    return
