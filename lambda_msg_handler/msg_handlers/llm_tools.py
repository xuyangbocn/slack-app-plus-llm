import logging
import os
import json
from datetime import datetime, timezone

import boto3

from msg_handlers.llm_utils.tool_access_logger import ToolAccessLogger
from msg_handlers.llm_utils.tool_access_checker import BaseToolAccessChecker, ToolAccessSampleChecker

logger = logging.getLogger()
logger.setLevel(logging.INFO)

llm_tools_vars = json.loads(
    os.environ.get('llm_tools_vars', '{}')
)

cwl = ToolAccessLogger(
    log_client=boto3.client('logs'),
    log_group=os.environ['cwlg_tool_call_audit'],
    log_stream=os.environ['cwls_func_call_audit']
)

# acl = ToolAccessSampleChecker()


@cwl.log_func_call()
# @acl.require_caller_in_groups(groups=["HR", ])
# @acl.require_caller_has_perms(permissions=["get_bday", ])
def find_birthday(**args) -> str:
    name = args['name']
    bd = "unknown"
    if "yangbo" in name.lower():
        bd = "1991.Aug"
    return bd


@cwl.log_func_call()
def current_datetime(**args) -> str:
    return datetime.now(timezone.utc).isoformat()


tools = {
    "definitions": [
        {
            "type": "function",
            "function": {
                "name": "find_birthday",
                "description": "Get the birth date of a person.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the person.",
                        },
                    },
                    "required": ["name"],
                },
            },
        }, {
            "type": "function",
            "function": {
                "name": "current_datetime",
                "description": "Find current date time in UTC.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
    ],

    "tool_functions": {
        "find_birthday": find_birthday,
        "current_datetime": current_datetime,
    },
}
