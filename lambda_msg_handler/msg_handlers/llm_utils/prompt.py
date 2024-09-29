import logging
from typing import Optional, Union, Any, List, Dict, Callable


logger = logging.getLogger()
logger.setLevel(logging.INFO)


class Prompt(object):
    '''
    Prompt formulates sentences into instructions and messages format that can be taken by chat completion api.
    '''

    def __init__(self, sentences: List[str]):
        self._sentences = [s.strip() for s in sentences]

    @property
    def instructions(self) -> str:
        return " ".join(self._sentences).strip()

    @property
    def messages(self) -> List[object]:
        return [
            {"role": "system", "content": s} for s in self._sentences if s
        ]
