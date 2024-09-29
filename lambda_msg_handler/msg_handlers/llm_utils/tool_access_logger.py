import os
import json
import time
import logging
import functools
from typing import Optional, Union, Any, Dict, List, Callable
from typing_extensions import override

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class ToolAccessLogger():
    '''
    A cloudwatch logger for LLM tool calls.
    Provides a decorator for LLM function calls.
    '''

    def __init__(
        self,
        log_client: Any,
        log_group: str,
        log_stream: str,
    ):
        self.log_client = log_client
        self.log_group = log_group
        self.log_stream = log_stream

    def write(self, caller: str, tool_name: str, tool_args: Dict[str, Any], tool_response: str):
        self.log_client.put_log_events(
            logGroupName=self.log_group,
            logStreamName=self.log_stream,
            logEvents=[
                {
                    'timestamp': time.time_ns()//1000000,
                    'message': json.dumps(
                        {
                            'caller': caller,
                            'tool_name': tool_name,
                            'tool_args': tool_args,
                            'tool_response': tool_response,
                        }
                    )
                },
            ]
        )
        return

    def log_func_call(self) -> Callable:
        '''
        Return a decorator to log function calls
        If need to log calls that fails access check, place this at the out most as (1st) decorator.

        E.g.
            cwl = ToolAccessLogger(...)

            @cwl.log_func_call()
            def some_llm_function_call(**args) -> str:
                ...
        '''
        def decorator(f: Callable) -> Callable:
            @functools.wraps(f)
            def wrapper(**kwargs):
                r = f(**kwargs)

                self.write(
                    caller=kwargs.get('caller', 'anonymous'),
                    tool_name=f.__name__,
                    tool_args=kwargs,
                    tool_response=r,
                )
                return r
            return wrapper

        return decorator
