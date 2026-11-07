"""Unit tests for Encrypted Database Manager and backup/restore workflows."""

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from veritrace.infrastructure.persistence.encrypted_database import (
    DatabaseEncryptionStatus,
    EncryptedDatabaseManager,
)
from veritrace.infrastructure.security.dpapi_store import DpapiDataEncryptionKey


def create_sample_sqlite_db(db_path: Path) -> None:
    """Create a sample SQLite database with test schema and data."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE evidence (id TEXT PRIMARY KEY, title TEXT, score REAL)")
    cursor.execute("INSERT INTO evidence VALUES ('evd_001', 'Signature crop', 0.95)")
    cursor.execute("INSERT INTO evidence VALUES ('evd_002', 'Stamp impression', 0.88)")
    conn.commit()
    conn.close()


def test_sqlcipher_availability():
    """Verify is_sqlcipher_available runs cleanly."""
    res = EncryptedDatabaseManager.is_sqlcipher_available()
    assert isinstance(res, bool)


def test_get_encryption_status():
    """Verify status reporting based on driver availability and user preference."""
    with patch.object(EncryptedDatabaseManager, "is_sqlcipher_available", return_value=False):
        mgr = EncryptedDatabaseManager(prefer_encryption=True)
        assert mgr.get_encryption_status() == DatabaseEncryptionStatus.SQLCIPHER_UNAVAILABLE

    with patch.object(EncryptedDatabaseManager, "is_sqlcipher_available", return_value=True):
        mgr_unenc = EncryptedDatabaseManager(prefer_encryption=False)
        assert mgr_unenc.get_encryption_status() == DatabaseEncryptionStatus.UNENCRYPTED_STANDARD

        mgr_enc = EncryptedDatabaseManager(prefer_encryption=True)
        assert mgr_enc.get_encryption_status() == DatabaseEncryptionStatus.ENCRYPTED_SQLCIPHER


def test_backup_and_restore_database(tmp_path: Path):
    """Verify defensive backup creation and database restoration."""
    db_file = tmp_path / "test_forensics.db"
    create_sample_sqlite_db(db_file)

    mgr = EncryptedDatabaseManager()
    backup_file = mgr.backup_database(db_file)

    assert backup_file.is_file()
    assert backup_file.stat().st_size > 0

    # Mutate the source database
    conn = sqlite3.connect(str(db_file))
    conn.execute("DELETE FROM evidence WHERE id = 'evd_001'")
    conn.commit()
    conn.close()

    # Verify mutation took effect
    conn = sqlite3.connect(str(db_file))
    rows = conn.execute("SELECT * FROM evidence").fetchall()
    assert len(rows) == 1
    conn.close()

    # Restore from backup
    success = mgr.restore_from_backup(backup_file, db_file)
    assert success is True

    # Verify original rows are restored
    conn = sqlite3.connect(str(db_file))
    restored_rows = conn.execute("SELECT * FROM evidence").fetchall()
    assert len(restored_rows) == 2
    conn.close()


def test_get_connection_url_standard(tmp_path: Path):
    """Verify standard SQLite WAL connection URL formatting."""
    db_file = tmp_path / "veritrace_data.db"
    mgr = EncryptedDatabaseManager(prefer_encryption=False)

    url = mgr.get_connection_url(db_file)
    assert url.startswith("sqlite:///")
    assert "veritrace_data.db" in url


def test_get_connection_url_encrypted_with_mock(tmp_path: Path):
    """Verify SQLCipher connection URL generation using DPAPI key."""
    db_file = tmp_path / "veritrace_secure.db"

    mock_key_mgr = MagicMock(spec=DpapiDataEncryptionKey)
    # 32 bytes of 0xAB -> hex string of length 64
    mock_key_mgr.get_or_create_key.return_value = b"\xab" * 32

    with patch.object(EncryptedDatabaseManager, "is_sqlcipher_available", return_value=True):
        mgr = EncryptedDatabaseManager(
            key_manager=mock_key_mgr,
            prefer_encryption=True,
        )
        url = mgr.get_connection_url(db_file)

        assert url.startswith("sqlite+pysqlcipher://:")
        assert "abababab" in url
        assert "veritrace_secure.db" in url


def test_migrate_unencrypted_to_encrypted_without_driver(tmp_path: Path):
    """Verify graceful rejection and defensive backup when SQLCipher driver is missing."""
    src_db = tmp_path / "legacy.db"
    create_sample_sqlite_db(src_db)
    enc_out = tmp_path / "legacy_encrypted.db"

    with patch.object(EncryptedDatabaseManager, "is_sqlcipher_available", return_value=False):
        mgr = EncryptedDatabaseManager()
        success, message = mgr.migrate_unencrypted_to_encrypted(src_db, enc_out)

        assert success is False
        assert "SQLCipher driver" in message
        assert "remains safely preserved" in message
        assert not enc_out.exists()


def test_real_sqlcipher_encryption_and_tamper_rejection(tmp_path: Path):
    """Verify true SQLCipher encryption with sqlcipher3 on disk and reject invalid keys."""
    if not EncryptedDatabaseManager.is_sqlcipher_available():
        pytest.skip("sqlcipher3 driver not installed")

    import sqlcipher3

    db_path = tmp_path / "sqlcipher_live.db"
    key = "TestSecretLiveKey123"

    # Create encrypted db
    conn = sqlcipher3.connect(str(db_path))
    conn.execute(f'PRAGMA key = "{key}"')
    conn.execute("CREATE TABLE forensics (id INT, payload TEXT)")
    conn.execute("INSERT INTO forensics VALUES (1, 'SENSITIVE_INVESTIGATION_DATA')")
    conn.commit()
    conn.close()

    # Verify raw disk bytes
    raw_data = db_path.read_bytes()
    assert not raw_data.startswith(b"SQLite format 3")
    assert b"SENSITIVE_INVESTIGATION_DATA" not in raw_data

    # Standard SQLite must fail
    conn_std = sqlite3.connect(str(db_path))
    with pytest.raises(sqlite3.DatabaseError):
        conn_std.execute("SELECT * FROM forensics").fetchall()
    conn_std.close()

    # Wrong key must fail
    conn_wrong = sqlcipher3.connect(str(db_path))
    conn_wrong.execute('PRAGMA key = "WRONG_KEY"')
    with pytest.raises(sqlcipher3.DatabaseError):
        conn_wrong.execute("SELECT * FROM forensics").fetchall()
    conn_wrong.close()

    # Correct key succeeds
    conn_ok = sqlcipher3.connect(str(db_path))
    conn_ok.execute(f'PRAGMA key = "{key}"')
    rows = conn_ok.execute("SELECT * FROM forensics").fetchall()
    assert rows == [(1, "SENSITIVE_INVESTIGATION_DATA")]
    conn_ok.close()


def test_migrate_unencrypted_to_encrypted_live(tmp_path: Path):
    """Verify live migration from plaintext SQLite to encrypted SQLCipher database."""
    if not EncryptedDatabaseManager.is_sqlcipher_available():
        pytest.skip("sqlcipher3 driver not installed")

    import sqlcipher3

    src_db = tmp_path / "plain_source.db"
    create_sample_sqlite_db(src_db)
    enc_out = tmp_path / "migrated_encrypted.db"

    key_mgr = DpapiDataEncryptionKey(key_store_dir=tmp_path / "keys")
    mgr = EncryptedDatabaseManager(key_manager=key_mgr)
    success, msg = mgr.migrate_unencrypted_to_encrypted(src_db, enc_out)

    assert success is True
    assert enc_out.is_file()

    # Destination is encrypted
    enc_raw = enc_out.read_bytes()
    assert not enc_raw.startswith(b"SQLite format 3")
    assert b"Signature crop" not in enc_raw

    # Query with DPAPI key succeeds
    dek = mgr._key_manager.get_or_create_key()
    c_mig = sqlcipher3.connect(str(enc_out))
    c_mig.execute(f"PRAGMA key = \"x'{dek.hex()}'\"")
    rows = c_mig.execute("SELECT * FROM evidence").fetchall()
    assert len(rows) == 2
    c_mig.close()


def test_encrypted_database_restart_and_recovery(tmp_path: Path):
    """Verify application restart lifecycle, DPAPI key reload, and recovery from backup."""
    if not EncryptedDatabaseManager.is_sqlcipher_available():
        pytest.skip("sqlcipher3 driver not installed")

    from datetime import UTC, datetime

    import sqlalchemy as sa
    import sqlalchemy.exc

    from veritrace.infrastructure.persistence.database import (
        create_session_factory,
        session_scope,
    )
    from veritrace.infrastructure.persistence.models.investigation import InvestigationModel
    from veritrace.infrastructure.persistence.models.organization import OrganizationModel

    db_file = tmp_path / "app_restart_test.db"
    key_store_dir = tmp_path / "security"
    key_mgr = DpapiDataEncryptionKey(key_store_dir=key_store_dir)
    mgr = EncryptedDatabaseManager(db_path=db_file, key_manager=key_mgr, prefer_encryption=True)

    url = mgr.get_connection_url(db_file)

    # 1. Startup 1: Create schema and insert data
    engine1 = sa.create_engine(url)
    session_factory1 = create_session_factory(engine1)

    InvestigationModel.metadata.create_all(engine1)

    org_id = "org_restart_001"
    inv_id = "inv_restart_001"
    now = datetime.now(UTC)

    with session_scope(session_factory1) as session:
        session.add(
            OrganizationModel(
                id=org_id, name="Test Corp", industry_sector="MANUFACTURING", created_at=now
            )
        )
        session.add(
            InvestigationModel(
                id=inv_id,
                organization_id=org_id,
                title="Restart Audit",
                reference_code="INV-RES-01",
                status="DRAFT",
                created_at=now,
                updated_at=now,
            )
        )

    # 2. Simulate application shutdown
    engine1.dispose()

    # Verify disk file is fully encrypted
    raw_disk = db_file.read_bytes()
    assert not raw_disk.startswith(b"SQLite format 3")
    assert b"Restart Audit" not in raw_disk

    # 3. Startup 2 (Application restart): Independent store instance reloads DPAPI key
    key_mgr2 = DpapiDataEncryptionKey(key_store_dir=key_store_dir)
    mgr2 = EncryptedDatabaseManager(db_path=db_file, key_manager=key_mgr2, prefer_encryption=True)
    url2 = mgr2.get_connection_url(db_file)

    engine2 = sa.create_engine(url2)
    session_factory2 = create_session_factory(engine2)

    with session_scope(session_factory2) as session:
        inv = session.query(InvestigationModel).filter_by(id=inv_id).first()
        assert inv is not None
        assert inv.title == "Restart Audit"

    # 4. Create encrypted backup
    backup_file = mgr2.backup_database(db_file)
    assert backup_file.is_file()
    assert not backup_file.read_bytes().startswith(b"SQLite format 3")

    # 5. Simulate catastrophic database corruption
    engine2.dispose()
    db_file.write_bytes(b"CORRUPTED_GARBAGE_BYTES_OVERWRITING_DATABASE")

    # Reconnect fails on corrupt database
    engine_corrupt = sa.create_engine(url2)
    with pytest.raises(sa.exc.DatabaseError), engine_corrupt.connect() as conn:
        conn.execute(sa.text("SELECT * FROM investigations"))
    engine_corrupt.dispose()

    # 6. Disaster Recovery: Restore from backup
    success = mgr2.restore_from_backup(backup_file, db_file)
    assert success is True

    # 7. Startup 3 (Post-recovery restart): Query recovered data
    engine3 = sa.create_engine(url2)
    session_factory3 = create_session_factory(engine3)
    with session_scope(session_factory3) as session:
        recovered_inv = session.query(InvestigationModel).filter_by(id=inv_id).first()
        assert recovered_inv is not None
        assert recovered_inv.title == "Restart Audit"
    engine3.dispose()
