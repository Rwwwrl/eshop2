class DuplicateMessageError(Exception):
    """Raised when a message with the same logical_id has already been processed."""
