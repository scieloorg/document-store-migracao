"""
Este módulo deve conter classes concretas que implementam as interfaces
definidas no módulo `interfaces`, ou seja, adaptadores.
"""
from typing import Dict
from documentstore_migracao import interfaces


class BaseObjectStorage(interfaces.ObjectStorage):
    """Implementação de `interfaces.ObjectStorage` para armazenamento em ObjectStore.
    Trata-se de uma classe abstrata que deve ser estendida por outras que
    implementam/definem o atributo `DomainClass`.
    """

    def __init__(self, storage):
        self._storage = storage

    def remove(self, uuid: str) -> None:
        self._storage.remove(uuid)

    def register(self, file_path: str) -> str:
        return self._storage.register(file_path)

    def get_asset(self, uuid: str):
        return self._storage.get_asset(uuid)

    def get_urls(self, uuid: str) -> Dict:
        return self._storage.get_urls(uuid)
