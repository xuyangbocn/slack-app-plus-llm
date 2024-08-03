import json
import logging
from typing import Optional, Union, Any, Dict, List, Callable
from typing_extensions import override

from openai import OpenAI, AzureOpenAI, AssistantEventHandler
from openai.types.beta.threads.runs import ToolCall, ToolCallDelta, RunStep

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_asst(
        openai_client,
        asst_id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        model: Optional[str] = None,
        tools=None):
    '''
    Check if there is an asistant with the specified name exist.
    If yes, retreive the object, if not create new.
    Tools to be loaded

    Return
        Assistant object
    '''
    asst_config = dict(
        description=description,
        instructions=instructions,
        model=model,
        tools=tools,
    )
    asst = None
    if asst_id:
        logger.info(f"Retrieving: {asst_id}")
        asst = openai_client.beta.assistants.retrieve(asst_id)
    else:
        logger.info(f'Searching: {name}')
        assts = openai_client.beta.assistants.list(limit=100)
        for a in assts:
            if a.name == name:
                asst = a
                logger.info(f"Found: {asst.name}")
                break

    if not asst:
        logger.info(f"Creating: {name}")
        asst = openai_client.beta.assistants.create(name=name, **asst_config)
    else:
        openai_client.beta.assistants.update(asst.id, **asst_config)
    return asst


def ask_asst(
        openai_client,
        asst_id: str,
        asst_thread_id: str,
        msg: str,
        tool_functions: Dict[str, Callable]) -> str:
    '''
    Send message to openai assistant api for response. Handles ordinary response and tool function calling

    Return:
        response (str): string response from openai
    '''
    def handle_require_actions(
            openai_client, tool_functions, current_thread_id, current_run_id, tool_calls):

        # requires tool calls
        tool_outputs = []
        for tool in tool_calls:
            resp = tool_functions[tool.function.name](
                **json.loads(tool.function.arguments)
            )
            logger.info(f'func name: {tool.function.name}')
            logger.info(f'func arg: {tool.function.arguments}')
            logger.info(f'func resp: {resp[:500]}')
            tool_outputs.append({
                "tool_call_id": tool.id, "output": resp})

        # submit tool call output
        response = ""
        with openai_client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=current_thread_id,
            run_id=current_run_id,
            tool_outputs=tool_outputs,
            event_handler=AssistantEventHandler(),
        ) as tool_stream:
            for tool_event in tool_stream:
                logger.info(f"Tool stream event: {tool_event.event}")
                if tool_event.event == "thread.message.delta" and tool_event.data.delta.content:
                    response += tool_event.data.delta.content[0].text.value
                elif tool_event.event == 'thread.run.requires_action':
                    response = handle_require_actions(
                        openai_client,
                        tool_functions,
                        current_thread_id,
                        current_run_id,
                        tool_event.data.required_action.submit_tool_outputs.tool_calls
                    )

        return response

    openai_client.beta.threads.messages.create(
        thread_id=asst_thread_id,
        role="user",
        content=msg
    )
    response = ""

    main_event_handler = AssistantEventHandler()
    with openai_client.beta.threads.runs.stream(
        thread_id=asst_thread_id,
        assistant_id=asst_id,
        event_handler=main_event_handler,
    ) as stream:
        for event in stream:
            logger.info(f"Stream event: {event.event}")
            if event.event == "thread.message.delta" and event.data.delta.content:
                # ordinary response from openai
                response += event.data.delta.content[0].text.value
            elif event.event == 'thread.run.requires_action':
                # requires tool calls
                response = handle_require_actions(
                    openai_client,
                    tool_functions,
                    main_event_handler.current_run.thread_id,
                    main_event_handler.current_run.id,
                    event.data.required_action.submit_tool_outputs.tool_calls
                )

    return response


def complete_chat(
        openai_client,
        model: str,
        messages: List[Dict[str, str]],
        tool_defs: List[dict],
        tool_functions: Dict[str, Callable],
        az_data_source: dict) -> str:

    if (type(openai_client) is not AzureOpenAI) or az_data_source == {}:
        extra_body = {}
    else:
        extra_body = {"data_sources": [az_data_source]}

    response = openai_client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tool_defs,
        extra_body=extra_body,
    )
    response_message = response.choices[0].message

    while response_message.tool_calls:
        messages.append({
            "role": response_message.role,
            "tool_calls": response_message.tool_calls,
            "content": response_message.content})

        for tool_call in response_message.tool_calls:
            logger.info("==func name: " + tool_call.function.name)
            function_name = tool_call.function.name
            function_to_call = tool_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)
            logger.info("==func args: \n" + str(function_args))
            function_response = function_to_call(**function_args)
            logger.info("==func resp: \n" + str(function_response[:200]))
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                }
            )
        response = openai_client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tool_defs,
        )
        response_message = response.choices[0].message

    if not response_message.content:
        logger.warning(f'Empty text content from OpenAI response: {response}')
        return f'Empty text content from OpenAI response: {response}'
    return response_message.content
