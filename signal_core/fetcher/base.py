from abc import ABC, abstractmethod
from ..models import FeedItem


class BaseFetcher(ABC):
    @abstractmethod
    def fetch(self) -> list[FeedItem]:
        ...
