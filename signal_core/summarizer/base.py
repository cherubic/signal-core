from abc import ABC, abstractmethod
from ..models import FeedItem, SummarizedItem


class BaseSummarizer(ABC):
    @abstractmethod
    def summarize(self, items: list[FeedItem]) -> list[SummarizedItem]:
        ...

    @abstractmethod
    def pick_top5(self, items: list[SummarizedItem]) -> list[SummarizedItem]:
        ...
