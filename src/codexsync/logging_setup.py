import logging
import json
from pathlib import Path

from .models import LoggingConfig


def configure_logging(cfg: LoggingConfig, verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else getattr(logging, cfg.level.upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if cfg.file:
        _ensure_parent(cfg.file)
        handlers.append(logging.FileHandler(cfg.file, encoding="utf-8"))

    formatter = _build_formatter(cfg.format)
    for handler in handlers:
        handler.setFormatter(formatter)

    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True,
    )


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _build_formatter(format_name: str) -> logging.Formatter:
    value = format_name.lower().strip()
    if value == "json":
        return _JsonFormatter()
    if value == "logfmt":
        return _LogfmtFormatter()
    return logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(payload, ensure_ascii=False)


class _LogfmtFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        fields = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        return " ".join(f"{key}={_quote_logfmt(str(value))}" for key, value in fields.items())


def _quote_logfmt(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
