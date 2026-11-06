"""Unit tests for OriginalDocumentStorage."""

from __future__ import annotations

from pathlib import Path

import pytest

from veritrace.domain.exceptions.base import StorageError
from veritrace.infrastructure.storage.document_storage import (
    OriginalDocumentStorage,
    resolve_default_storage_root,
    sanitize_filename,
)


def test_sanitize_filename() -> None:
    """Verify filename sanitization strips path traversal characters and illegal symbols."""
    assert sanitize_filename("contract.pdf") == "contract.pdf"
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32.dll") == "system32.dll"
    assert sanitize_filename("report:2026*final?.pdf") == "report_2026_final_.pdf"
    assert sanitize_filename("") == "document_unnamed.bin"
    assert sanitize_filename("...   ") == "document_unnamed.bin"


def test_resolve_default_storage_root_prefers_custom_root(tmp_path: Path) -> None:
    """Verify custom root is respected when passed."""
    custom = tmp_path / "custom_storage"
    root = resolve_default_storage_root(custom, allow_workspace_storage=True)
    assert root == custom.resolve()


def test_store_original_immutable_and_read(tmp_path: Path) -> None:
    """Verify storing original file persists content immutably and allows reading."""
    storage = OriginalDocumentStorage(storage_root=tmp_path, allow_workspace_storage=True)

    org_id = "org_test001"
    inv_id = "inv_test001"
    doc_id = "doc_test001"
    content = b"PDF original content binary bytes"

    path_str = storage.store_original(
        organization_id=org_id,
        investigation_id=inv_id,
        document_id=doc_id,
        filename="contract.pdf",
        content=content,
    )

    stored_path = Path(path_str)
    assert stored_path.is_file()
    assert stored_path.name == "contract.pdf"
    assert "original" in stored_path.parts

    read_back = storage.read_original(path_str)
    assert read_back == content


def test_store_original_empty_content_raises(tmp_path: Path) -> None:
    """Verify empty content is rejected."""
    storage = OriginalDocumentStorage(storage_root=tmp_path, allow_workspace_storage=True)
    with pytest.raises(StorageError, match="Cannot store empty content"):
        storage.store_original("org_1", "inv_1", "doc_1", "empty.pdf", b"")


def test_store_original_prevents_overwrite(tmp_path: Path) -> None:
    """Verify overwriting an existing original file is strictly prohibited."""
    storage = OriginalDocumentStorage(storage_root=tmp_path, allow_workspace_storage=True)
    storage.store_original("org_1", "inv_1", "doc_1", "doc.pdf", b"initial bytes")

    with pytest.raises(StorageError, match="Overwriting original documents is strictly forbidden"):
        storage.store_original("org_1", "inv_1", "doc_1", "doc.pdf", b"new bytes")


def test_store_page_image(tmp_path: Path) -> None:
    """Verify storing page image saves raster preview correctly."""
    storage = OriginalDocumentStorage(storage_root=tmp_path, allow_workspace_storage=True)
    img_bytes = b"\x89PNG\r\n\x1a\nfake_preview"

    saved_path = storage.store_page_image(
        organization_id="org_1",
        investigation_id="inv_1",
        document_id="doc_1",
        page_number=1,
        image_bytes=img_bytes,
    )

    path = Path(saved_path)
    assert path.is_file()
    assert path.name == "page_1.png"
    assert path.read_bytes() == img_bytes


def test_cleanup_document_compensation(tmp_path: Path) -> None:
    """Verify cleanup removes files and directories cleanly even if files are read-only."""
    storage = OriginalDocumentStorage(storage_root=tmp_path, allow_workspace_storage=True)
    path_str = storage.store_original("org_1", "inv_1", "doc_1", "doc.pdf", b"content")
    storage.store_page_image("org_1", "inv_1", "doc_1", 1, b"preview")

    assert Path(path_str).exists()

    storage.cleanup_document("org_1", "inv_1", "doc_1")
    assert not Path(path_str).exists()


def test_storage_read_original_for_tenant_isolation_guard(tmp_path: Path) -> None:
    """Verify that read_original_for_tenant rejects access from a different organization."""
    from veritrace.domain.exceptions.base import TenantIsolationError

    storage = OriginalDocumentStorage(storage_root=tmp_path, allow_workspace_storage=True)
    path_org_a = storage.store_original("org_alpha", "inv_1", "doc_1", "secret.pdf", b"secret data")

    # Access by owning org succeeds
    data = storage.read_original_for_tenant("org_alpha", path_org_a)
    assert data == b"secret data"

    # Access by adversary org raises TenantIsolationError
    with pytest.raises(TenantIsolationError, match="Cross-organization storage access violation"):
        storage.read_original_for_tenant("org_adversary", path_org_a)


def test_cleanup_never_deletes_prior_successful_ingestion(tmp_path: Path) -> None:
    """Verify that cleaning up a failed document never touches earlier successful documents."""
    storage = OriginalDocumentStorage(storage_root=tmp_path, allow_workspace_storage=True)

    # Ingest document 1 successfully
    path_1 = storage.store_original("org_1", "inv_1", "doc_001", "contract.pdf", b"contract data")
    preview_1 = storage.store_page_image("org_1", "inv_1", "doc_001", 1, b"page 1 preview")

    # Ingest document 2 which subsequently fails
    path_2 = storage.store_original("org_1", "inv_1", "doc_002", "failed.pdf", b"failed data")
    storage.store_page_image("org_1", "inv_1", "doc_002", 1, b"failed page 1")

    # Perform compensating cleanup ONLY on document 2
    storage.cleanup_document("org_1", "inv_1", "doc_002")

    # Assert document 2 is completely removed
    assert not Path(path_2).exists()

    # Assert document 1 is completely preserved and untouched
    assert Path(path_1).exists()
    assert Path(preview_1).exists()
    assert storage.read_original(path_1) == b"contract data"
