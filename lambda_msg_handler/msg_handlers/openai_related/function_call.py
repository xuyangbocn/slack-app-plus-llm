import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def find_birthday(**args) -> str:
    name = args['name']
    bd = "unknown"
    if "yangbo" in name.lower():
        bd = "1991.08.13"
    return bd


functions = {
    "declaration": {
        "find_birthday": find_birthday,
    },
    "description": [
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
        },
    ]
}
