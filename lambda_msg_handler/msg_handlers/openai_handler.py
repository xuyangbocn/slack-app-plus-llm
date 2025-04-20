import os
import logging

from openai import OpenAI, AssistantEventHandler
from minagent import Agent

from msg_handlers.llm_tools import tools
from msg_handlers.slack_related.SlackLLMHandler import SlackLLMHandler

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Slack client
slack_oauth_token = os.environ["slack_oauth_token"]

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

# Initialize an LLM Agent
agent = Agent(
    openai_client,
    name='OpenaiOnSlack',
    description="OpenAI on Slack",
    model=openai_gpt_model,
    instructions=[openai_asst_instructions],
    tools=tool_defs,
    tool_functions=tool_functions,
    # web_search_options={
    #     'search_context_size': 'medium',
    # }
)

# aws boto3
ddb_asst_thread_table = os.environ['ddb_asst_thread']
ddb_chat_completion_table = os.environ['ddb_chat_completion']
s3_input_file_bucket = os.environ['s3_input_file_bucket']


def handler_via_assistant(slack_event):
    '''
    Overall slack message processing function
    Simple pass-on to Chatgpt
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
