from fastapi import Request
from fastapi.responses import JSONResponse

class AppException(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message

class NotFoundError(AppException):
    def __init__(self, entity: str, entity_id: str):
        super().__init__(404, "NOT_FOUND", f"{entity} not found: {entity_id}")

class DuplicateError(AppException):
    def __init__(self, field: str, value: str):
        super().__init__(409, "DUPLICATE", f"Duplicate {field}: {value}")

class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(401, "AUTH_REQUIRED", message)

class AuthorizationError(AppException):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(403, "FORBIDDEN", message)

class ValidationError(AppException):
    def __init__(self, message: str):
        super().__init__(422, "VALIDATION_ERROR", message)

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "code": exc.code,
        },
    )
