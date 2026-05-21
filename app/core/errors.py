class AppError(Exception):
    """Base application error for domain and service failures."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)
