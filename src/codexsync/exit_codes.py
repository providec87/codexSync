from enum import IntEnum


class ExitCode(IntEnum):
    OK = 0
    INTERNAL_ERROR = 1
    CONFLICT_DETECTED = 2
    CODEX_RUNNING = 3
    BAD_INPUT = 4
    FAIL_SAFE = 5
