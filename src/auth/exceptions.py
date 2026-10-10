class UserAlreadyExists(Exception):
    """An account with this email already exists."""


class UserNotFound(Exception):
    """The requested account does not exist."""


class CredentialsException(Exception):
    """Credentials or token claims are invalid."""
