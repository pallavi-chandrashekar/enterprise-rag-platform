class AppException(Exception):
    """Base class for all application exceptions."""
    def __init__(self, detail: str, status_code: int = 500):
        self.detail = detail
        self.status_code = status_code
        super().__init__(self.detail)


class NotFoundError(AppException):
    """Raised when a resource is not found."""
    def __init__(self, detail: str = "Not Found"):
        super().__init__(detail, status_code=404)


class ValidationError(AppException):
    """Raised when there is a validation error."""
    def __init__(self, detail: str = "Validation Error"):
        super().__init__(detail, status_code=422)


class UnauthorizedError(AppException):
    """Raised when the user is not authorized to perform an action."""
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(detail, status_code=401)
