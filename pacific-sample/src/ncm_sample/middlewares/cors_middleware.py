"""CORS middleware configuration."""

from typing import List
from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware
from ncm_sample.config.settings import get_settings

class CORSMiddleware:
    """CORS middleware wrapper for NCM Sample."""

    def __init__(
        self,
        allow_origins: List[str] = None,
        allow_credentials: bool = True,
        allow_methods: List[str] = ["*"],
        allow_headers: List[str] = ["*"],
    ):
        settings = get_settings()

        # Use settings if no explicit origins provided
        if allow_origins is None:
            allow_origins = settings.cors_origins

        self.allow_origins = allow_origins
        self.allow_credentials = allow_credentials
        self.allow_methods = allow_methods
        self.allow_headers = allow_headers

    def get_middleware(self):
        """Get the Starlette CORS middleware class."""
        return StarletteCORSMiddleware
