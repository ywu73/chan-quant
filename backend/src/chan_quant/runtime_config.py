"""Validated runtime configuration for local and deployed environments."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, cast

Environment = Literal["development", "test", "staging", "production"]
DataMode = Literal["synthetic", "csv", "sina", "snapshot"]

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}
_HOST_PATTERN = re.compile(
    r"^(?:localhost|(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\."
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*|(?:\d{1,3}\.){3}\d{1,3})$"
)
_RELEASE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{7,64}$")


class RuntimeConfigError(ValueError):
    """Raised when runtime configuration is incomplete or invalid."""


@dataclass(frozen=True)
class RuntimeConfig:
    environment: Environment
    data_mode: DataMode
    remote_network_enabled: bool
    force_refresh_enabled: bool
    docs_enabled: bool
    allowed_hosts: tuple[str, ...]
    release_sha: str
    csv_path: str | None
    snapshot_path: str | None
    research_preview: bool = True


def _parse_bool(environ: Mapping[str, str], name: str, default: bool) -> bool:
    raw = environ.get(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise RuntimeConfigError(
        f"{name} must be true/false, 1/0, yes/no, or on/off"
    )


def configured_data_mode(environ: Mapping[str, str] | None = None) -> DataMode:
    values = os.environ if environ is None else environ
    configured = values.get("CHAN_QUANT_DATA_SOURCE", "").strip().lower()
    if not configured:
        if values.get("CHAN_QUANT_DATA_PACKAGE_PATH"):
            return "snapshot"
        return "csv" if values.get("CHAN_QUANT_CSV_PATH") else "synthetic"
    if configured not in {"synthetic", "csv", "sina", "snapshot"}:
        raise RuntimeConfigError(
            "CHAN_QUANT_DATA_SOURCE must be synthetic, csv, sina, or snapshot"
        )
    return cast(DataMode, configured)


def remote_network_enabled(environ: Mapping[str, str] | None = None) -> bool:
    values = os.environ if environ is None else environ
    return _parse_bool(values, "CHAN_QUANT_REMOTE_NETWORK_ENABLED", True)


def _allowed_hosts(environ: Mapping[str, str]) -> tuple[str, ...]:
    raw = environ.get(
        "CHAN_QUANT_ALLOWED_HOSTS",
        "localhost,127.0.0.1,testserver",
    )
    hosts = tuple(item.strip().lower() for item in raw.split(",") if item.strip())
    if not hosts or any(not _HOST_PATTERN.fullmatch(host) for host in hosts):
        raise RuntimeConfigError(
            "CHAN_QUANT_ALLOWED_HOSTS must contain comma-separated host names or IPv4 addresses"
        )
    return tuple(dict.fromkeys(hosts))


def load_runtime_config(environ: Mapping[str, str] | None = None) -> RuntimeConfig:
    """Parse a fresh immutable configuration snapshot.

    The optional mapping keeps request-level tests and diagnostic checks reloadable;
    the application does not cache environment variables globally.
    """

    values = os.environ if environ is None else environ
    raw_environment = values.get("CHAN_QUANT_ENVIRONMENT", "development").strip().lower()
    if raw_environment not in {"development", "test", "staging", "production"}:
        raise RuntimeConfigError(
            "CHAN_QUANT_ENVIRONMENT must be development, test, staging, or production"
        )
    environment = cast(Environment, raw_environment)

    if environment == "production":
        required = (
            "CHAN_QUANT_DATA_SOURCE",
            "CHAN_QUANT_REMOTE_NETWORK_ENABLED",
            "CHAN_QUANT_ALLOW_FORCE_REFRESH",
            "CHAN_QUANT_DOCS_ENABLED",
            "CHAN_QUANT_ALLOWED_HOSTS",
            "CHAN_QUANT_RELEASE_SHA",
        )
        missing = [name for name in required if not values.get(name, "").strip()]
        if missing:
            raise RuntimeConfigError(
                "production requires explicit deployment settings: " + ", ".join(missing)
            )

    release_sha = values.get("CHAN_QUANT_RELEASE_SHA", "development").strip()
    if not _RELEASE_PATTERN.fullmatch(release_sha):
        raise RuntimeConfigError(
            "CHAN_QUANT_RELEASE_SHA must be a 1-64 character build identifier"
        )
    if environment == "production" and not _GIT_SHA_PATTERN.fullmatch(release_sha):
        raise RuntimeConfigError(
            "production CHAN_QUANT_RELEASE_SHA must be a 7-64 character hexadecimal Git SHA"
        )

    return RuntimeConfig(
        environment=environment,
        data_mode=configured_data_mode(values),
        remote_network_enabled=remote_network_enabled(values),
        force_refresh_enabled=_parse_bool(
            values,
            "CHAN_QUANT_ALLOW_FORCE_REFRESH",
            False,
        ),
        docs_enabled=_parse_bool(
            values,
            "CHAN_QUANT_DOCS_ENABLED",
            environment != "production",
        ),
        allowed_hosts=_allowed_hosts(values),
        release_sha=release_sha,
        csv_path=values.get("CHAN_QUANT_CSV_PATH") or None,
        snapshot_path=values.get("CHAN_QUANT_DATA_PACKAGE_PATH") or None,
    )


def docs_enabled_for_startup(environ: Mapping[str, str] | None = None) -> bool:
    """Choose a fail-closed docs setting even when another config field is invalid."""

    values = os.environ if environ is None else environ
    environment = values.get("CHAN_QUANT_ENVIRONMENT", "development").strip().lower()
    return _parse_bool(
        values,
        "CHAN_QUANT_DOCS_ENABLED",
        environment != "production",
    )
