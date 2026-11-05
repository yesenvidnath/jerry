"""Typed downstream failures with a safe message for API clients."""


class DownstreamServiceError(RuntimeError):
    def __init__(self, service: str, public_message: str) -> None:
        super().__init__(f"{service} operation failed")
        self.service = service
        self.public_message = public_message
