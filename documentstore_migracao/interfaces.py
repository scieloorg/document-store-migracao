import abc
import logging
import functools
from typing import Dict

logger = logging.getLogger(__name__)


class ObjectStorage(abc.ABC):
    """Interface basica de manipulação para salvas os ativos digitais.
    """

    @abc.abstractmethod
    def register(self, file_path: str) -> str:
        """ registra um arquivo e retorna uma url """
        ...

    @abc.abstractmethod
    def get_asset(self, uuid: str):
        ...

    @abc.abstractmethod
    def get_urls(self, uuid: str) -> Dict:
        ...

    @abc.abstractmethod
    def remove(self, id: str) -> None:
        ...
