import os
import json
import time
import logging
import functools
from typing import Optional, Union, Any, Dict, List, Callable
from typing_extensions import override
from abc import ABC, abstractmethod

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class BaseToolAccessChecker(ABC):
    '''
    Abstract class for access control to LLM tools. This class is used in decorator requires_caller_groups(), requires_permissions()
    Abstract Method caller_in_groups(), and caller_has_perms() to be overridden in subclass
    '''
    @abstractmethod
    def caller_in_groups(
        self, caller: str, groups: List[str]
    ) -> bool:
        '''
        Biz logic of checking if caller is in the allowed groups. Returns True/False.
        To be overridden.
        '''
        pass

    @abstractmethod
    def caller_has_perms(
        self, caller: str, permissions: List[str]
    ) -> bool:
        '''
        Biz logic of checking if caller has the required permission. Returns True/False.
        To be overridden.
        '''
        pass

    def require_caller_in_groups(self, groups: List[str]):
        '''
        Decorator to access control tool calls
        Check if caller is from the allowed groups
        '''
        def decorator(f):
            @functools.wraps(f)
            def wrapper(**kwargs):
                tool_name = f.__name__
                caller = kwargs.get('caller', 'anonymous')
                if self.caller_in_groups(caller, groups) is True:
                    r = f(**kwargs)
                else:
                    r = f'Caller {caller} has no access to {tool_name}.'
                return r
            return wrapper

        return decorator

    def require_caller_has_perms(self, permissions: List[str]):
        '''
        Decorator to access control tool calls
        Check if caller has the required permissions
        '''
        def decorator(f):
            @functools.wraps(f)
            def wrapper(**kwargs):
                tool_name = f.__name__
                caller = kwargs.get('caller', 'anonymous')
                if self.caller_has_perms(caller, permissions) is True:
                    r = f(**kwargs)
                else:
                    r = f'Caller {caller} has no access to {tool_name}.'
                return r
            return wrapper

        return decorator


class ToolAccessSampleChecker(BaseToolAccessChecker):
    '''
    Sample Access control for LLM tool calls.
    '''

    def caller_in_groups(
        self, caller: str, groups: List[str]
    ) -> bool:
        # always allow
        return True

    def caller_has_perms(
        self, caller: str, permissions: List[str]
    ) -> bool:
        # always deny
        return False
