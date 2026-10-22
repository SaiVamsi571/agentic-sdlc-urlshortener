"""
Repository Abstract Base Interface for URL Shortener Service.
"""
import abc
from typing import Any, Dict, List, Optional
from src.service.models import AnalyticsSummary, ClickEventRecord, ShortURLRecord, SystemStats

class BaseURLRepository(abc.ABC):
    @abc.abstractmethod
    def save_url(self, record: ShortURLRecord) -> bool:
        pass

    @abc.abstractmethod
    def get_url(self, short_code: str) -> Optional[ShortURLRecord]:
        pass

    @abc.abstractmethod
    def get_by_original_url(self, original_url: str) -> Optional[ShortURLRecord]:
        pass

    @abc.abstractmethod
    def is_code_taken(self, code: str) -> bool:
        pass

    @abc.abstractmethod
    def record_click(self, event: ClickEventRecord) -> None:
        pass

    @abc.abstractmethod
    def get_analytics(self, short_code: str) -> Optional[AnalyticsSummary]:
        pass

    @abc.abstractmethod
    def get_system_stats(self) -> SystemStats:
        pass
