"""Custom exceptions for auth service."""

from fastapi import HTTPException, status


class BaseAPIException(HTTPException):
    """Base API exception with error code support."""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = None,
        headers: dict = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code or self.__class__.__name__


class UserNotFoundError(BaseAPIException):
    """User not found exception."""
    
    def __init__(self, user_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
            error_code="USER_NOT_FOUND"
        )


class UserAlreadyExistsError(BaseAPIException):
    """User already exists exception."""
    
    def __init__(self, email: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {email} already exists",
            error_code="USER_ALREADY_EXISTS"
        )


class AuthenticationError(BaseAPIException):
    """Authentication failed exception."""
    
    def __init__(self, detail: str = "Invalid credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="AUTHENTICATION_FAILED"
        )


class AuthorizationError(BaseAPIException):
    """Authorization failed exception."""
    
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="AUTHORIZATION_FAILED"
        )


class ValidationError(BaseAPIException):
    """Validation error exception."""
    
    def __init__(self, detail: str, field: str = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="VALIDATION_ERROR"
        )
        self.field = field

