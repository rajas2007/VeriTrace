"""Original Document Storage abstraction.

Enforces immutable storage, path traversal protection, safe filename sanitization,
directory isolation by organization/investigation/document, and isolation from
OneDrive and the Git repository.
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import stat
from pathlib import Path

from veritrace.domain.exceptions.base import StorageError


def resolve_default_storage_root(
    custom_root: Path | str | None = None,
    allow_workspace_storage: bool = False,
) -> Path:
    """Resolve and validate the primary document storage root directory.

    Priority:
    1. custom_root parameter (if provided)
    2. VERITRACE_STORAGE_ROOT environment variable
    3. %LOCALAPPDATA%/VeriTrace/storage
    """
    if custom_root is not None:
        root = Path(custom_root).expanduser().resolve()
    elif "VERITRACE_STORAGE_ROOT" in os.environ:
        root = Path(os.environ["VERITRACE_STORAGE_ROOT"]).expanduser().resolve()
    else:
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            root = (Path(local_app_data) / "VeriTrace" / "storage").resolve()
        else:
            root = (Path.home() / ".local" / "share" / "VeriTrace" / "storage").resolve()

    # Invariant: Never store runtime files inside OneDrive
    if "onedrive" in str(root).lower() and not allow_workspace_storage:
        # Fall back to safe local directory outside OneDrive
        safe_base = (
            Path("C:/VeriTrace/storage") if os.name == "nt" else Path("/var/lib/veritrace/storage")
        )
        root = safe_base.resolve()

    return root


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and strip illegal characters."""
    base = Path(filename).name
    # Remove null bytes and illegal Windows/POSIX characters: \ / : * ? " < > |
    cleaned = re.sub(r'[\x00-\x1f\\/:*?"<>|]', "_", base).strip()
    cleaned = cleaned.strip(". ")
    if not cleaned:
        cleaned = "document_unnamed.bin"
    return cleaned


class OriginalDocumentStorage:
    """Manages immutable filesystem storage for uploaded original documents and page rasters."""

    def __init__(
        self,
        storage_root: Path | str | None = None,
        allow_workspace_storage: bool = False,
    ) -> None:
        self._allow_workspace = allow_workspace_storage
        self._storage_root = resolve_default_storage_root(
            storage_root,
            allow_workspace_storage=allow_workspace_storage,
        )
        self._documents_root = self._storage_root / "documents"
        self._pages_root = self._storage_root / "pages"

        # Create base storage roots
        self._documents_root.mkdir(parents=True, exist_ok=True)
        self._pages_root.mkdir(parents=True, exist_ok=True)

    @property
    def storage_root(self) -> Path:
        """Root filesystem path for storage."""
        return self._storage_root

    def _get_document_dir(
        self,
        organization_id: str,
        investigation_id: str,
        document_id: str,
    ) -> Path:
        """Resolve isolated directory for a specific document."""
        doc_dir = (
            self._documents_root
            / sanitize_filename(organization_id)
            / sanitize_filename(investigation_id)
            / sanitize_filename(document_id)
        ).resolve()

        if not doc_dir.is_relative_to(self._storage_root):
            raise StorageError(f"Path traversal detected in document path: {doc_dir}")
        return doc_dir

    def store_original(
        self,
        organization_id: str,
        investigation_id: str,
        document_id: str,
        filename: str,
        content: bytes,
    ) -> str:
        """Store raw original document bytes immutably."""
        if not content:
            raise StorageError("Cannot store empty content for original document")

        doc_dir = self._get_document_dir(organization_id, investigation_id, document_id)
        original_dir = doc_dir / "original"
        original_dir.mkdir(parents=True, exist_ok=True)

        safe_name = sanitize_filename(filename)
        target_path = (original_dir / safe_name).resolve()

        if not target_path.is_relative_to(self._storage_root):
            raise StorageError(f"Path traversal detected: {target_path}")

        if target_path.exists():
            raise StorageError(
                f"File already exists at {target_path}. "
                "Overwriting original documents is strictly forbidden."
            )

        temp_path = original_dir / f"{safe_name}.tmp_{os.getpid()}"
        try:
            temp_path.write_bytes(content)
            temp_path.replace(target_path)
            with contextlib.suppress(OSError):
                os.chmod(target_path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
        except Exception as exc:
            if temp_path.exists():
                with contextlib.suppress(OSError):
                    temp_path.unlink()
            raise StorageError(f"Failed to persist original file: {exc}") from exc

        return str(target_path.as_posix())

    def read_original(self, storage_path: str | Path) -> bytes:
        """Read original file bytes from storage, verifying path containment."""
        path = Path(storage_path).resolve()
        if not path.is_relative_to(self._storage_root):
            raise StorageError(f"Path traversal violation reading file: {path}")
        if not path.is_file():
            raise StorageError(f"Original file not found: {path}")
        return path.read_bytes()

    def read_original_for_tenant(
        self,
        organization_id: str,
        storage_path: str | Path,
    ) -> bytes:
        """Read original file verifying that the path belongs strictly to the organization."""
        path = Path(storage_path).resolve()
        expected_org_dir = (self._documents_root / sanitize_filename(organization_id)).resolve()
        if not path.is_relative_to(expected_org_dir):
            from veritrace.domain.exceptions.base import TenantIsolationError

            raise TenantIsolationError(
                f"Cross-organization storage access violation: Path '{storage_path}' "
                f"does not belong to organization '{organization_id}'"
            )
        return self.read_original(path)

    def store_page_image(
        self,
        organization_id: str,
        investigation_id: str,
        document_id: str,
        page_number: int,
        image_bytes: bytes,
    ) -> str:
        """Store rasterized page preview PNG image."""
        pages_dir = (
            self._pages_root
            / sanitize_filename(organization_id)
            / sanitize_filename(investigation_id)
            / sanitize_filename(document_id)
        ).resolve()

        if not pages_dir.is_relative_to(self._storage_root):
            raise StorageError(f"Path traversal detected in pages path: {pages_dir}")

        pages_dir.mkdir(parents=True, exist_ok=True)
        page_path = pages_dir / f"page_{page_number}.png"
        page_path.write_bytes(image_bytes)
        return str(page_path.as_posix())

    def cleanup_document(
        self,
        organization_id: str,
        investigation_id: str,
        document_id: str,
    ) -> None:
        """Compensating cleanup: remove document directory and page directory on failed intake."""
        doc_dir = self._get_document_dir(organization_id, investigation_id, document_id)
        if doc_dir.exists():
            self._remove_tree_safely(doc_dir)

        pages_dir = (
            self._pages_root
            / sanitize_filename(organization_id)
            / sanitize_filename(investigation_id)
            / sanitize_filename(document_id)
        ).resolve()
        if pages_dir.exists():
            self._remove_tree_safely(pages_dir)

    def _remove_tree_safely(self, path: Path) -> None:
        """Safely remove a directory tree, clearing read-only flags first."""
        if not path.is_relative_to(self._storage_root):
            return

        def _clear_readonly(func, fpath, _exc):  # type: ignore[no-untyped-def]
            with contextlib.suppress(OSError):
                os.chmod(fpath, stat.S_IWRITE)
                func(fpath)

        shutil.rmtree(path, onerror=_clear_readonly)
