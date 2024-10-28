import logging
import json
from typing import Optional, Union, Any, List, Dict, Callable
import concurrent.futures as cf

from openai import OpenAI, AzureOpenAI, AssistantEventHandler

from .prompt import Prompt

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class Agent(object):
    '''
    Agent is a wrapper on top of any compatible interface of OpenAI chat completion API.
    Agent is similar to beta OpenAI Assistant concept.
    Each Agent has a pre-defined
        - model
        - system prompt
        - tools
        - other configurations
    This can be used for non-OpenAI LLM, or when openai assistant api doesnt support certain features.
    '''

    def __init__(
        self,
        llm_client: Any,
        name: str,
        description: str,
        model: str,
        sentences: List[str],
        tools: Union[List[object], None] = None,
        tool_choice: Union[str, None] = 'auto',
        tool_functions: Dict[str, Callable] = {},
        az_data_source: Dict = {},
        openai_asst_id: str = '',
    ):
        self.llm_client = llm_client
        self.name = name
        self.description = description
        self.model = model
        self.prompt = Prompt(sentences)
        self.tool_functions = tool_functions

        # For chat completion API
        self.chat_completion_kwargs = {'model': self.model}
        if tools:
            self.chat_completion_kwargs.update({
                'tools': tools,
                'tool_choice': tool_choice,
            })
        if (type(llm_client) is AzureOpenAI) and az_data_source:
            self.chat_completion_kwargs.update({
                'extra_body': {'data_sources': [az_data_source]}
            })

        # For Assistance API
        self.asst_config = {
            'name': name,
            'description': description,
            'instructions': self.prompt.instructions,
            'model': model,
            'tools': tools,
        }
        self.openai_asst = None
        self.openai_asst_id = openai_asst_id

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
        # else:
        #     self.llm_client.beta.assistants.update(asst.id, **self.asst_config)
        return asst

    def ask_assistant(
        self,
        user: str,
        asst_thread_id: str,
        message: str,
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

            return response

        if self.openai_asst is None:
            self.openai_asst = self._get_openai_asst()

        self.llm_client.beta.threads.messages.create(
            thread_id=asst_thread_id,
            role='user',
            content=message
        )

        reply = ''

        main_event_handler = AssistantEventHandler()
        with self.llm_client.beta.threads.runs.stream(
            thread_id=asst_thread_id,
            assistant_id=self.openai_asst.id,
            event_handler=main_event_handler,
        ) as stream:
            for event in stream:
                logger.info(f'Stream event: {event.event}')
                if event.event == 'thread.message.delta' and event.data.delta.content:
                    # ordinary response from openai
                    reply += event.data.delta.content[0].text.value
                elif event.event == 'thread.run.requires_action':
                    # requires tool calls
                    reply = handle_require_actions(
                        main_event_handler.current_run.thread_id,
                        main_event_handler.current_run.id,
                        event.data.required_action.submit_tool_outputs.tool_calls
                    )

        return reply

    def chat_completion(
        self,
        user: str,
        messages: List[Dict[str, str]]
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
