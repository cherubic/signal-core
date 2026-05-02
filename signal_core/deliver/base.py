from abc import ABC, abstractmethod


class BaseDeliverer(ABC):
    @abstractmethod
    def send(self, digest: dict) -> None:
        ...
