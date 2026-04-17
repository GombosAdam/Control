class NAVApiError(Exception):
    """General NAV API error."""
    def __init__(self, func_code: str, error_code: str, message: str):
        self.func_code = func_code
        self.error_code = error_code
        self.message = message
        super().__init__(f"NAV API error [{func_code}] {error_code}: {message}")


class NAVAuthError(NAVApiError):
    """Authentication / token exchange failure."""
    def __init__(self, message: str = "NAV authentication failed"):
        super().__init__("AUTH", "AUTH_ERROR", message)


class NAVValidationError(NAVApiError):
    """Schema or business validation error from NAV."""
    def __init__(self, error_code: str, message: str):
        super().__init__("VALIDATION", error_code, message)


class NAVConnectionError(Exception):
    """Network-level failure communicating with NAV."""
    def __init__(self, message: str = "Cannot reach NAV Online Számla API"):
        self.message = message
        super().__init__(message)
