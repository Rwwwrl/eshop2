class DuplicateTaskMessageError(Exception):
    """Raised when a task message with the same logical_id has already been processed."""
