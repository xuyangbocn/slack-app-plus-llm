import logging
import os
import json
from datetime import datetime, timezone

import boto3

from msg_handlers.llm_utils.tool_access_logger import ToolAccessLogger
from msg_handlers.llm_utils.tool_access_checker import BaseToolAccessChecker, ToolAccessSampleChecker
from msg_handlers.aws_reinvent.reinvent_helper import ReinventHelper

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

reinventHelper = ReinventHelper(
    api_profile="3ol5ZxLLv8O462NxA19WthWuAzT7Ud9o",
)


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


@cwl.log_func_call()
def aws_reinvent_search_sessions(**args) -> str:
    sessions = reinventHelper.search_session(
        search_text=args['search_text'],
        sessiontypes=args.get('session_types', []),
        topic=args.get('topics', []),
        areaofinterest=args.get('areas_of_interest', []),
        level=args.get('technical_levels', []),
        role=args.get('audience_roles', []),
        day=args.get('session_date', []),
        datehour=args.get('session_starting_hour', []),
        venue=args.get('venues', []),
    )
    return json.dumps(sessions)


@cwl.log_func_call()
def aws_reinvent_list_session_types(**args) -> str:
    return str(reinventHelper.list_sessiontypes())


@cwl.log_func_call()
def aws_reinvent_list_session_topics(**args) -> str:
    return str(reinventHelper.list_topic())


@cwl.log_func_call()
def aws_reinvent_list_area_of_interest(**args) -> str:
    return str(reinventHelper.list_areaofinterest())


@cwl.log_func_call()
def aws_reinvent_list_session_technical_levels(**args) -> str:
    return str(reinventHelper.list_level())


@cwl.log_func_call()
def aws_reinvent_list_audience_roles(**args) -> str:
    return str(reinventHelper.list_role())


@cwl.log_func_call()
def aws_reinvent_list_venues(**args) -> str:
    return str(reinventHelper.list_venue())


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
        }, {
            "type": "function",
            "function": {
                "name": "aws_reinvent_list_session_types",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }, {
            "type": "function",
            "function": {
                "name": "aws_reinvent_list_session_topics",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }, {
            "type": "function",
            "function": {
                "name": "aws_reinvent_list_area_of_interest",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }, {
            "type": "function",
            "function": {
                "name": "aws_reinvent_list_session_technical_levels",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }, {
            "type": "function",
            "function": {
                "name": "aws_reinvent_list_audience_roles",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }, {
            "type": "function",
            "function": {
                "name": "aws_reinvent_list_venues",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }, {
            "type": "function",
            "function": {
                "name": "aws_reinvent_search_sessions",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_text": {
                            "type": "string",
                        },
                        "session_types": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            }
                        },
                        "topics": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            }
                        },
                        "areas_of_interest": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            }
                        },
                        "technical_levels": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            }
                        },
                        "audience_roles": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            }
                        },
                        "session_date": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "description": "In format of YYYYMMDD"
                            }
                        },
                        "session_starting_hour": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "description": "In format of YYYYMMDDtHH in Pacific Standard Time"
                            }
                        },
                        "venues": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            }
                        },

                    },
                    "required": ["search_text"],
                },
            },
        },
    ],

    "tool_functions": {
        "find_birthday": find_birthday,
        "current_datetime": current_datetime,
        "aws_reinvent_list_session_types": aws_reinvent_list_session_types,
        "aws_reinvent_list_session_topics": aws_reinvent_list_session_topics,
        "aws_reinvent_list_area_of_interest": aws_reinvent_list_area_of_interest,
        "aws_reinvent_list_session_technical_levels": aws_reinvent_list_session_technical_levels,
        "aws_reinvent_list_audience_roles": aws_reinvent_list_audience_roles,
        "aws_reinvent_list_venues": aws_reinvent_list_venues,
        "aws_reinvent_search_sessions": aws_reinvent_search_sessions,
    },
}
