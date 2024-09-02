import os
import json
import time
import logging
from typing import Optional, Union, Any, Dict, List, Callable
from typing_extensions import override

import boto3
import botocore

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logs = boto3.client('logs')
cwlg_tool_call_audit = os.environ['cwlg_tool_call_audit']
cwls_func_call_audit = os.environ['cwls_func_call_audit']


def log_func_call(f):
    def with_log(**args):

        r = f(**args)
        log = {
            'caller': args.get('caller', 'anonymous'),
            'tool_name': f.__name__,
            'tool_args': args,
            'tool_response': r,
        }
        logger.info(f'tool_call_audit: {log}')
        response = logs.put_log_events(
            logGroupName=cwlg_tool_call_audit,
            logStreamName=cwls_func_call_audit,
            logEvents=[
                {
                    'timestamp': time.time_ns()//1000000,
                    'message': json.dumps(log)
                },
            ]
        )
        logger.info(f'tool_call_audit: {response}')

        return r

    return with_log
