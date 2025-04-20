import os
import logging
import json

from openai import AzureOpenAI, AssistantEventHandler
from minagent import Agent

from msg_handlers.llm_tools import tools
from msg_handlers.slack_related.SlackLLMHandler import SlackLLMHandler

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Slack client
slack_oauth_token = os.environ["slack_oauth_token"]

# azure openai
az_openai_endpoint = os.environ.get('az_openai_endpoint', '')
az_openai_api_key = os.environ.get('az_openai_api_key', '')
az_openai_api_version = os.environ.get('az_openai_api_version', '')
az_openai_deployment_name = os.environ.get('az_openai_deployment_name', '')
az_openai_asst_instructions = os.environ.get('az_openai_asst_instructions', '')
az_data_source = json.loads(os.environ.get('az_data_source', '{}'))
az_openai_client = AzureOpenAI(
    api_key=az_openai_api_key,
    api_version=az_openai_api_version,
    azure_endpoint=az_openai_endpoint,
)

# tools available for assistant to use
tool_defs = tools['definitions']

# tool function declaration
tool_functions = tools['tool_functions']

# Initialize an LLM Agent
agent = Agent(
    az_openai_client,
    name='az_openai_on_slack',
    description='Azure OpenAI on slack',
    model=az_openai_deployment_name,
    instructions=[az_openai_asst_instructions],
    tools=tool_defs,
    tool_functions=tool_functions,
    extra_body={'data_sources': [az_data_source]},
)

# aws boto3
ddb_asst_thread_table = os.environ['ddb_asst_thread']
ddb_chat_completion_table = os.environ['ddb_chat_completion']
s3_input_file_bucket = os.environ['s3_input_file_bucket']


def handler_via_assistant(slack_event):
    '''
    Overall slack message processing function
    Simple pass-on to Az OpenAI Assistant
    '''
    handler = SlackLLMHandler(
        agent,
        s3_input_file_bucket=s3_input_file_bucket,
        ddb_chat_completion_table=ddb_chat_completion_table,
        ddb_asst_thread_table=ddb_asst_thread_table,
        slack_oauth_token=slack_oauth_token,
        slack_event=slack_event,
        mode="Assistant",
    )
    handler.reply()
    return


def handler_via_chat_completion(slack_event):
    '''
    Overall slack message processing function
    Re-collect thread history and call Az OpenAI chat completion
    '''
    handler = SlackLLMHandler(
        agent,
        s3_input_file_bucket=s3_input_file_bucket,
        ddb_chat_completion_table=ddb_chat_completion_table,
        ddb_asst_thread_table=ddb_asst_thread_table,
        slack_oauth_token=slack_oauth_token,
        slack_event=slack_event,
        mode="ChatCompletion",
    )
    handler.reply()

    return
