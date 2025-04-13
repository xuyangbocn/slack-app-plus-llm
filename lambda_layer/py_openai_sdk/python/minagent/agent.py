import logging
import json
from typing import Optional, Union, Any, List, Dict, Callable
from typing_extensions import Literal

import concurrent.futures as cf

from openai import OpenAI, AzureOpenAI, AssistantEventHandler, NotGiven

from .prompt import Prompt

logger = logging.getLogger()
logger.setLevel(logging.INFO)

NOT_GIVEN = NotGiven()


class Agent(object):
    '''
    Agent is a wrapper on top of OpenAI chat completion and assistant API.

    It handles `tool_call`, `file_search` within the class
    '''

    def __init__(
        self,
        llm_client: Any,
        name: str,
        description: str,
        model: str,
        instructions: List[str],

        ##################
        # Common Openai api parameters
        ##################
        metadata: Dict[str, str] | NotGiven = NOT_GIVEN,

        reasoning_effort: Optional[  # for o-series only
            Literal["low", "medium", "high"]] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        tools: List[object] | NotGiven = NOT_GIVEN,
        tool_choice: str | NotGiven = NOT_GIVEN,

        # for assistant api only
        tool_resources: Dict | None = None,

        # for chat completion only
        web_search_options: Dict | NotGiven = NOT_GIVEN,  # for limited models
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[bool] | NotGiven = NOT_GIVEN,
        top_logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        modalities: Optional[
            List[Literal["text", "audio"]]] | NotGiven = NOT_GIVEN,

        ##################
        # Tool function for execution, Extra body, External data sources
        ##################
        tool_functions: Dict[str, Callable] = {},
        extra_body: Dict | None = None,

        openai_asst_id: str = '',
    ):
        self.llm_client = llm_client
        self.name = name
        self.description = description
        self.model = model
        self.prompt = Prompt(instructions)
        self.tools = tools
        self.tool_choice = tool_choice
        self.tool_resources = tool_resources
        self.parallel_tool_calls = parallel_tool_calls
        self.reasoning_effort = reasoning_effort
        self.temperature = temperature
        self.top_p = top_p
        self.max_completion_tokens = max_completion_tokens
        self.metadata = metadata
        self.web_search_options = web_search_options
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.logit_bias = logit_bias
        self.logprobs = logprobs
        self.top_logprobs = top_logprobs
        self.modalities = modalities

        ##
        self.openai_asst = None
        self.openai_asst_id = openai_asst_id
        self.tool_functions = tool_functions
        self.extra_body = extra_body

        self._set_chat_completion_kwargs()
        self._set_asst_config()
        self._set_asst_run_kwargs()

    def _set_chat_completion_kwargs(self):
        self.chat_completion_kwargs = {
            'model': self.model,
            'tools': self.tools,
            'tool_choice': self.tool_choice,
            'parallel_tool_calls': self.parallel_tool_calls,
            'reasoning_effort': self.reasoning_effort,
            'temperature': self.temperature,
            'top_p': self.top_p,
            'max_completion_tokens': self.max_completion_tokens,
            'metadata': self.metadata,
            'web_search_options': self.web_search_options,
            'frequency_penalty': self.frequency_penalty,
            'presence_penalty': self.presence_penalty,
            'logit_bias': self.logit_bias,
            'logprobs': self.logprobs,
            'top_logprobs': self.top_logprobs,
            'modalities': self.modalities,
            'extra_body': self.extra_body,
        }
        return

    def _set_asst_config(self):
        self.asst_config = {
            'name': self.name,
            'description': self.description,
            'instructions': self.prompt.instructions,
            'model': self.model,
            'tools': self.tools,
            'tool_resources': self.tool_resources,
            'reasoning_effort': self.reasoning_effort,
            'temperature': self.temperature,
            'top_p': self.top_p,
            'metadata': self.metadata,
        }
        return

    def _set_asst_run_kwargs(self):
        self.asst_run_kwargs = {
            'parallel_tool_calls': self.parallel_tool_calls,
            'max_completion_tokens': self.max_completion_tokens,
            'tool_choice': self.tool_choice,
        }
        return

    def _get_openai_asst(self):
        '''
        Get or create an instance of OpenAI Assistant
        Returns:
            OpenAI Assistant Object
            None if llm client is not OpenAI or AzureOpenAI
        '''
        if (type(self.llm_client) is not OpenAI) and (type(self.llm_client) is not AzureOpenAI):
            raise Exception(
                'Agent assistant api requires OpenAI or AzureOpenAI client.')

        asst = None
        if self.openai_asst_id:
            asst = self.llm_client.beta.assistants.retrieve(
                self.openai_asst_id)
        else:
            assts = self.llm_client.beta.assistants.list(limit=100)
            for a in assts:
                if a.name == self.asst_config['name']:
                    asst = a
                    break
        if not asst:
            logger.info(f'Creating OpenAI asst: {self.asst_config['name']}')
            asst = self.llm_client.beta.assistants.create(**self.asst_config)
        else:
            self.llm_client.beta.assistants.update(asst.id, **self.asst_config)
        return asst

    def ask_assistant(
        self,
        user: str,
        asst_thread_id: str,
        message: str,
        additional_instructions: Optional[str] | NotGiven = NOT_GIVEN,
        additional_messages: Optional[List[object]] | NotGiven = NOT_GIVEN,
    ) -> str:
        '''
        Send message to openai assistant api for response. Handles ordinary response and tool function calling

        Return:
            reply (str): string response from openai
        '''
        def handle_require_actions(current_thread_id, current_run_id, tool_calls):
            # requires tool calls
            tool_outputs = []
            with cf.ThreadPoolExecutor() as pool:
                fs = {
                    pool.submit(
                        self.tool_functions[tool_call.function.name],
                        caller=user,
                        **json.loads(tool_call.function.arguments)
                    ): {
                        'tool_call_id': tool_call.id,
                        'function_name': tool_call.function.name,
                        'function_args': json.loads(tool_call.function.arguments)
                    }
                    for tool_call in tool_calls
                }
                for f in cf.as_completed(fs):
                    logger.info(
                        f'tool call func name: {fs[f]['function_name']}')
                    logger.info(
                        f'tool call func args: \n{fs[f]['function_args']}')
                    resp = f.result()
                    logger.info(f'tool call func resp: \n{resp[:200]}')
                    tool_outputs.append(
                        {
                            "tool_call_id": fs[f]['tool_call_id'],
                            "output": resp,
                        }
                    )

            # submit tool call output
            response = ''
            with self.llm_client.beta.threads.runs.submit_tool_outputs_stream(
                thread_id=current_thread_id,
                run_id=current_run_id,
                tool_outputs=tool_outputs,
                event_handler=AssistantEventHandler(),
            ) as tool_stream:
                for tool_event in tool_stream:
                    logger.info(f'Tool stream event: {tool_event.event}')
                    if tool_event.event == 'thread.message.delta' and tool_event.data.delta.content:
                        response += tool_event.data.delta.content[0].text.value
                    elif tool_event.event == 'thread.run.requires_action':
                        response = handle_require_actions(
                            current_thread_id,
                            current_run_id,
                            tool_event.data.required_action.submit_tool_outputs.tool_calls
                        )
                    elif tool_event.event == 'thread.run.failed':
                        reply = "Failed to get response from assistant API"
                        logger.error(reply)
                        break
            return response

        def handle_file_search_annotation(text_value, annotations):
            # replace annotation in message text with actual file id
            parsed_text = text_value
            for a in annotations:
                logger.info(f'File search annotation: {a.text}')
                if hasattr(a, 'file_citation'):
                    parsed_text = parsed_text.replace(
                        a.text, f'[{a.file_citation.file_id}]')

            return parsed_text

        if self.openai_asst is None:
            self.openai_asst = self._get_openai_asst()

        self.llm_client.beta.threads.messages.create(
            thread_id=asst_thread_id,
            role='user',
            content=message
        )

        reply = ''
        annotations = []

        main_event_handler = AssistantEventHandler()
        with self.llm_client.beta.threads.runs.stream(
            thread_id=asst_thread_id,
            assistant_id=self.openai_asst.id,
            event_handler=main_event_handler,
            additional_instructions=additional_instructions,
            additional_messages=additional_messages,
            **self.asst_run_kwargs,
        ) as stream:
            for event in stream:
                logger.info(f'Stream event: {event.event}')
                if event.data == 'error':
                    reply = "LLM server had an error while processing your request"
                    logger.error(reply)
                    break
                elif event.event == 'thread.message.delta' and event.data.delta.content:
                    # ordinary response from openai
                    reply += event.data.delta.content[0].text.value
                    # annotations from file search
                    if event.data.delta.content[0].text.annotations:
                        annotations += event.data.delta.content[0].text.annotations

                elif event.event == 'thread.run.requires_action':
                    # requires tool calls
                    reply = handle_require_actions(
                        main_event_handler.current_run.thread_id,
                        main_event_handler.current_run.id,
                        event.data.required_action.submit_tool_outputs.tool_calls
                    )
                elif event.event == 'thread.run.failed':
                    reply = "Failed to get response from assistant API"
                    logger.error(reply)
                    break

        reply = handle_file_search_annotation(reply, annotations)

        return reply

    def chat_completion(
        self,
        user: str,
        messages: List[Dict[str, str]],
    ) -> str:
        '''
        Send full thread of messages to openai chat completion api for response. Handles ordinary response and tool function calling

        Return:
            reply (str): string response from openai
        '''
        messages = self.prompt.messages + messages
        reply = ''

        try:
            response = self.llm_client.chat.completions.create(
                messages=messages,
                **self.chat_completion_kwargs
            )
            response_message = response.choices[0].message

            while response_message.tool_calls:
                messages.append({
                    'role': response_message.role,
                    'tool_calls': response_message.tool_calls,
                    'content': response_message.content})

                with cf.ThreadPoolExecutor() as pool:
                    fs = {
                        pool.submit(
                            self.tool_functions[tool_call.function.name],
                            caller=user,
                            **json.loads(tool_call.function.arguments)
                        ): {
                            'tool_call_id': tool_call.id,
                            'function_name': tool_call.function.name,
                            'function_args': json.loads(tool_call.function.arguments)
                        }
                        for tool_call in response_message.tool_calls
                    }
                    for f in cf.as_completed(fs):
                        logger.info(
                            f'tool call func name: {fs[f]['function_name']}')
                        logger.info(
                            f'tool call func args: \n{fs[f]['function_args']}')
                        resp = f.result()
                        logger.info(f'tool call func resp: \n{resp[:200]}')
                        messages.append(
                            {
                                'tool_call_id': fs[f]['tool_call_id'],
                                'role': 'tool',
                                'name': fs[f]['function_name'],
                                'content': resp,
                            }
                        )

                response = self.llm_client.chat.completions.create(
                    messages=messages,
                    **self.chat_completion_kwargs
                )
                response_message = response.choices[0].message

            if not (reply := response_message.content):
                reply = f'Empty text content from LLM response: \n{response}'
                logger.warning(reply)

        except Exception as ex:
            reply = f'Exception raised at Chat Completion: {ex}'
            logger.error(reply, stack_info=True, exc_info=True)
        return reply
