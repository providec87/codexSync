class CodexSyncError(Exception):
    """Base error for codexsync."""


class ConfigError(CodexSyncError):
    """Invalid or incomplete configuration."""


class SafetyPreconditionError(CodexSyncError):
    """Safety rule violation."""


class ConflictError(CodexSyncError):
    """Conflict that requires manual resolution."""


class FailSafeError(CodexSyncError):
    """Safe stop due to uncertainty."""
