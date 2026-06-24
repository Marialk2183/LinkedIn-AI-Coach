"""Artifact storage behind a tiny interface, with a local-filesystem fallback.

Generated PDF reports (and any future binary artifact) are written through an
:class:`ArtifactStore`. Locally this is the filesystem; in production it can be
**Azure Blob Storage** — selected by ``ARTIFACT_STORE`` / the presence of
``AZURE_BLOB_CONNECTION_STRING``. The interface is deliberately minimal
(``save`` / ``load``) so callers don't care which backend is live, matching the
abstraction-first, local-fallback direction of the Azure upgrade.

Analyses are immutable once created, so a report for a given id is cached under
``reports/{id}.pdf`` and re-served on later requests.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Protocol

from config import Settings

logger = logging.getLogger(__name__)


class ArtifactStore(Protocol):
    name: str

    def save(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Persist ``data`` under ``key``; return a locator (path or blob URL)."""
        ...

    def load(self, key: str) -> bytes | None:
        """Return the stored bytes for ``key``, or ``None`` if absent."""
        ...


class LocalArtifactStore:
    """Store artifacts on the local filesystem under a base directory."""

    name = "local"

    def __init__(self, base_dir: Path) -> None:
        self._base = Path(base_dir)

    def _path(self, key: str) -> Path:
        # Keys are app-controlled (e.g. "reports/12.pdf"); still guard traversal.
        safe = Path(key.replace("\\", "/"))
        if safe.is_absolute() or ".." in safe.parts:
            raise ValueError(f"Unsafe artifact key: {key!r}")
        return self._base / safe

    def save(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a sibling temp file then atomically rename, so a crash never
        # leaves a truncated artifact that would later be served as-is.
        tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)
        return str(path)

    def load(self, key: str) -> bytes | None:
        path = self._path(key)
        return path.read_bytes() if path.is_file() else None


class AzureBlobArtifactStore:
    """Store artifacts in an Azure Blob container (azure-storage-blob)."""

    name = "azure_blob"

    def __init__(self, connection_string: str, container: str) -> None:
        # Imported lazily so the package is only required when Blob is actually used.
        from azure.storage.blob import BlobServiceClient

        self._service = BlobServiceClient.from_connection_string(connection_string)
        self._container = container
        try:
            self._service.create_container(container)
        except Exception:  # noqa: BLE001 - already exists / insufficient perms
            logger.debug("Blob container %s already present or not creatable.", container)

    def save(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        from azure.storage.blob import ContentSettings

        blob = self._service.get_blob_client(self._container, key)
        blob.upload_blob(
            data, overwrite=True, content_settings=ContentSettings(content_type=content_type)
        )
        return blob.url

    def load(self, key: str) -> bytes | None:
        from azure.core.exceptions import ResourceNotFoundError

        blob = self._service.get_blob_client(self._container, key)
        try:
            return blob.download_blob().readall()
        except ResourceNotFoundError:
            return None


def build_store(settings: Settings) -> ArtifactStore:
    """Select the artifact store from config (Azure Blob if configured, else local)."""
    choice = (settings.artifact_store or "auto").lower()
    want_blob = choice == "azure_blob" or (choice == "auto" and settings.azure_blob_enabled)
    if want_blob:
        if settings.azure_blob_enabled:
            try:
                return AzureBlobArtifactStore(
                    settings.azure_blob_connection_string or "",
                    settings.azure_blob_container,
                )
            except Exception:  # noqa: BLE001 - missing package / bad creds → fall back
                logger.exception("Azure Blob init failed; falling back to local store.")
        elif choice == "azure_blob":
            logger.warning("ARTIFACT_STORE=azure_blob but no connection string set.")
    return LocalArtifactStore(settings.artifacts_abs_dir)
