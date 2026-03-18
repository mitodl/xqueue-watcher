"""
12-factor / Kubernetes-compatible settings for xqueue-watcher.

All manager configuration values can be supplied via environment variables
using the ``XQWATCHER_`` prefix.  This module mirrors the keys defined in
:data:`xqueue_watcher.settings.MANAGER_CONFIG_DEFAULTS` so it can be used
as a drop-in source of configuration alongside or instead of the JSON file
read by :func:`xqueue_watcher.settings.get_manager_config_values`.

It also provides :func:`configure_logging`, which initialises a structured
stdout logging configuration without requiring a ``logging.json`` file —
suitable for Kubernetes and any 12-factor environment where logs are consumed
from stdout by the container runtime.

Environment variables
---------------------
XQWATCHER_LOG_LEVEL
    Root log level (default: ``INFO``).  Accepts any standard Python level
    name: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``.
XQWATCHER_HTTP_BASIC_AUTH
    HTTP Basic Auth credentials as ``username:password``.  Unset or empty
    means no authentication (equivalent to ``None``).
XQWATCHER_POLL_TIME
    Seconds between liveness checks of client threads (integer, default 10).
XQWATCHER_REQUESTS_TIMEOUT
    Timeout in seconds for outbound HTTP requests (integer, default 1).
XQWATCHER_POLL_INTERVAL
    Seconds between queue-polling attempts (integer, default 1).
XQWATCHER_LOGIN_POLL_INTERVAL
    Seconds between login-retry attempts (integer, default 5).
XQWATCHER_FOLLOW_CLIENT_REDIRECTS
    Follow HTTP redirects when ``true`` or ``1``, ignore otherwise
    (boolean, default false).
"""

import logging
import logging.config
import os

from .settings import MANAGER_CONFIG_DEFAULTS

_PREFIX = "XQWATCHER_"

_LOG_FORMAT = "%(asctime)s %(levelname)s %(process)d [%(name)s] %(filename)s:%(lineno)d - %(message)s"


def configure_logging() -> None:
    """
    Initialise logging to stdout using a level read from the environment.

    This is the 12-factor / Kubernetes alternative to supplying a
    ``logging.json`` file.  All log records are written to ``stdout`` so they
    are captured by the container runtime and forwarded to whatever log
    aggregation system is in use (e.g. Fluentd, Loki, CloudWatch).

    The root log level defaults to ``INFO`` and can be overridden via the
    ``XQWATCHER_LOG_LEVEL`` environment variable.  The ``requests`` and
    ``urllib3`` libraries are pinned to ``WARNING`` to suppress noisy
    HTTP-level debug output.
    """
    level = os.environ.get(f"{_PREFIX}LOG_LEVEL", "INFO").strip().upper()

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": _LOG_FORMAT,
            },
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "standard",
                "level": level,
            },
        },
        "root": {
            "handlers": ["stdout"],
            "level": level,
        },
        "loggers": {
            "requests": {"level": "WARNING"},
            "urllib3": {"level": "WARNING"},
        },
    })


def _get_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if raw in ("1", "true", "yes"):
        return True
    if raw in ("0", "false", "no"):
        return False
    return default


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if raw:
        return int(raw)
    return default


def _get_auth(name: str, default):
    raw = os.environ.get(name, "").strip()
    if raw:
        return raw
    return default


def get_manager_config_from_env() -> dict:
    """
    Return manager configuration populated from environment variables.

    Values not present in the environment fall back to
    :data:`~xqueue_watcher.settings.MANAGER_CONFIG_DEFAULTS`.
    """
    return {
        "HTTP_BASIC_AUTH": _get_auth(
            f"{_PREFIX}HTTP_BASIC_AUTH",
            MANAGER_CONFIG_DEFAULTS["HTTP_BASIC_AUTH"],
        ),
        "POLL_TIME": _get_int(
            f"{_PREFIX}POLL_TIME",
            MANAGER_CONFIG_DEFAULTS["POLL_TIME"],
        ),
        "REQUESTS_TIMEOUT": _get_int(
            f"{_PREFIX}REQUESTS_TIMEOUT",
            MANAGER_CONFIG_DEFAULTS["REQUESTS_TIMEOUT"],
        ),
        "POLL_INTERVAL": _get_int(
            f"{_PREFIX}POLL_INTERVAL",
            MANAGER_CONFIG_DEFAULTS["POLL_INTERVAL"],
        ),
        "LOGIN_POLL_INTERVAL": _get_int(
            f"{_PREFIX}LOGIN_POLL_INTERVAL",
            MANAGER_CONFIG_DEFAULTS["LOGIN_POLL_INTERVAL"],
        ),
        "FOLLOW_CLIENT_REDIRECTS": _get_bool(
            f"{_PREFIX}FOLLOW_CLIENT_REDIRECTS",
            MANAGER_CONFIG_DEFAULTS["FOLLOW_CLIENT_REDIRECTS"],
        ),
    }



def _get_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if raw in ("1", "true", "yes"):
        return True
    if raw in ("0", "false", "no"):
        return False
    return default


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if raw:
        return int(raw)
    return default


def _get_auth(name: str, default):
    raw = os.environ.get(name, "").strip()
    if raw:
        return raw
    return default


def get_manager_config_from_env() -> dict:
    """
    Return manager configuration populated from environment variables.

    Values not present in the environment fall back to
    :data:`~xqueue_watcher.settings.MANAGER_CONFIG_DEFAULTS`.
    """
    return {
        "HTTP_BASIC_AUTH": _get_auth(
            f"{_PREFIX}HTTP_BASIC_AUTH",
            MANAGER_CONFIG_DEFAULTS["HTTP_BASIC_AUTH"],
        ),
        "POLL_TIME": _get_int(
            f"{_PREFIX}POLL_TIME",
            MANAGER_CONFIG_DEFAULTS["POLL_TIME"],
        ),
        "REQUESTS_TIMEOUT": _get_int(
            f"{_PREFIX}REQUESTS_TIMEOUT",
            MANAGER_CONFIG_DEFAULTS["REQUESTS_TIMEOUT"],
        ),
        "POLL_INTERVAL": _get_int(
            f"{_PREFIX}POLL_INTERVAL",
            MANAGER_CONFIG_DEFAULTS["POLL_INTERVAL"],
        ),
        "LOGIN_POLL_INTERVAL": _get_int(
            f"{_PREFIX}LOGIN_POLL_INTERVAL",
            MANAGER_CONFIG_DEFAULTS["LOGIN_POLL_INTERVAL"],
        ),
        "FOLLOW_CLIENT_REDIRECTS": _get_bool(
            f"{_PREFIX}FOLLOW_CLIENT_REDIRECTS",
            MANAGER_CONFIG_DEFAULTS["FOLLOW_CLIENT_REDIRECTS"],
        ),
    }
