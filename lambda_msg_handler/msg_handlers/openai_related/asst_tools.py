import logging
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def find_birthday(**args) -> str:
    name = args['name']
    bd = "unknown"
    if "yangbo" in name.lower():
        bd = "1991.Aug"
    return bd


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
                            "description": "Name of the person."
                        }
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
