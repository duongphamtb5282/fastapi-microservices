"""Base controller interface and implementation."""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Type
from fastapi import APIRouter
from ncm_sample.features.shared.services.base_service import BaseService

T = TypeVar('T')

class BaseController(ABC, Generic[T]):
    """Base controller interface."""

    def __init__(self, service_class: Type[T], router: APIRouter):
        self.service_class = service_class
        self.router = router
        self._setup_routes()
    
    @abstractmethod
    def _setup_routes(self):
        """Setup controller routes."""
        pass
