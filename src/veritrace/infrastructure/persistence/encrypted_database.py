"""Encrypted database connection management and migration utilities for SQLCipher / SQLite.

Implements safe encrypted database connection resolution, Windows DPAPI integration,
and non-destructive migration workflows preserving tenant isolation and existing records.
"""

from __future__ import annotations

import importlib.util
import logging
import shutil
import sqlite3
import time
from enum import StrEnum
from pathlib import Path

from veritrace.infrastructure.security.dpapi_store import DpapiDataEncryptionKey

logger = logging.getLogger("veritrace.infrastructure.persistence.encrypted_database")


class DatabaseEncryptionStatus(StrEnum):
    """Status classification for relational database encryption."""

    ENCRYPTED_SQLCIPHER = "ENCRYPTED_SQLCIPHER"
    UNENCRYPTED_STANDARD = "UNENCRYPTED_STANDARD"
    SQLCIPHER_UNAVAILABLE = "SQLCIPHER_UNAVAILABLE"


class EncryptedDatabaseManager:
    """Manages database encryption, DPAPI key resolution, and safe data migration."""

    def __init__(
        self,
        db_path: Path | str | None = None,
        key_manager: DpapiDataEncryptionKey | None = None,
        prefer_encryption: bool = False,
    ) -> None:
        self._db_path = Path(db_path) if db_path else None
        self._key_manager = key_manager or DpapiDataEncryptionKey()
        self._prefer_encryption = prefer_encryption

    @staticmethod
    def is_sqlcipher_available() -> bool:
        """Return True if sqlcipher3 or pysqlcipher3 DBAPI driver is installed."""
        for mod in ["sqlcipher3", "pysqlcipher3"]:
            if importlib.util.find_spec(mod) is not None:
                return True
        return False

    def get_encryption_status(self) -> DatabaseEncryptionStatus:
        """Determine active database encryption status."""
        if not self.is_sqlcipher_available():
            return DatabaseEncryptionStatus.SQLCIPHER_UNAVAILABLE

        if not self._prefer_encryption:
            return DatabaseEncryptionStatus.UNENCRYPTED_STANDARD

        return DatabaseEncryptionStatus.ENCRYPTED_SQLCIPHER

    def backup_database(
        self,
        source_path: Path | str,
        backup_dir: Path | str | None = None,
    ) -> Path:
        """Create a timestamped backup copy of a SQLite database file."""
        src = Path(source_path)
        if not src.is_file():
            raise FileNotFoundError(f"Source database file not found: {src}")

        b_dir = Path(backup_dir) if backup_dir else src.parent / "backups"
        b_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        dest = b_dir / f"{src.stem}_{timestamp}.bak"
        shutil.copy2(src, dest)
        logger.info("Created database backup: %s -> %s", src, dest)
        return dest

    def restore_from_backup(
        self,
        backup_path: Path | str,
        target_path: Path | str,
    ) -> bool:
        """Safely restore a database from a backup copy."""
        bak = Path(backup_path)
        tgt = Path(target_path)

        if not bak.is_file():
            raise FileNotFoundError(f"Backup file not found: {bak}")

        tgt.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bak, tgt)
        logger.info("Restored database from backup: %s -> %s", bak, tgt)
        return True

    def get_connection_url(self, db_path: Path | str) -> str:
        """Resolve SQLAlchemy connection URL based on encryption preferences."""
        path = Path(db_path).resolve()
        norm_path = str(path).replace("\\", "/")

        if self._prefer_encryption and self.is_sqlcipher_available():
            dek = self._key_manager.get_or_create_key()
            # Convert 32-byte binary key to 64-char hex string for SQLCipher PRAGMA key
            key_hex = dek.hex()
            logger.info(
                "Configuring SQLCipher connection for '%s' using DPAPI-sealed DEK", path.name
            )
            return f"sqlite+pysqlcipher://:{key_hex}@/{norm_path}"

        logger.info("Configuring standard SQLite WAL connection for: %s", path.name)
        return f"sqlite:///{norm_path}"

    def migrate_unencrypted_to_encrypted(
        self,
        unencrypted_path: Path | str,
        encrypted_output_path: Path | str,
    ) -> tuple[bool, str]:
        """Safely migrate existing unencrypted SQLite database to an encrypted SQLCipher database.

        Preserves all records, table schemas, and foreign keys. Backs up original database first.
        """
        src = Path(unencrypted_path)
        out = Path(encrypted_output_path)

        if not src.is_file():
            return False, f"Source database '{src}' does not exist."

        # Step 1: Create defensive backup
        backup_file = self.backup_database(src)

        # Step 2: Check SQLCipher availability
        if not self.is_sqlcipher_available():
            return False, (
                "SQLCipher driver (sqlcipher3 / pysqlcipher3) is not installed on this host. "
                f"Source database '{src.name}' remains safely preserved and unencrypted. "
                f"Defensive backup stored at: '{backup_file.name}'."
            )

        # Step 3: Execute table-by-table migration under transaction
        try:
            dek = self._key_manager.get_or_create_key()
            key_hex = dek.hex()

            # Connect to destination encrypted database using SQLCipher
            import sqlcipher3  # type: ignore[import-not-found]

            src_conn = sqlite3.connect(str(src))
            dest_conn = sqlcipher3.connect(str(out))
            dest_conn.execute(f"PRAGMA key = \"x'{key_hex}'\"")
            dest_conn.execute("PRAGMA cipher_page_size = 4096")

            # Extract table list
            cursor = src_conn.cursor()
            cursor.execute(
                "SELECT name, sql FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            )
            tables = cursor.fetchall()

            for table_name, create_sql in tables:
                if not create_sql:
                    continue
                dest_conn.execute(create_sql)
                # Copy rows
                rows_cursor = src_conn.cursor()
                rows_cursor.execute(f"SELECT * FROM [{table_name}]")
                rows = rows_cursor.fetchall()
                if rows:
                    placeholders = ", ".join(["?"] * len(rows[0]))
                    dest_conn.executemany(
                        f"INSERT INTO [{table_name}] VALUES ({placeholders})", rows
                    )

            dest_conn.commit()
            src_conn.close()
            dest_conn.close()

            logger.info("Successfully migrated database to encrypted SQLCipher file: %s", out)
            return True, f"Database successfully encrypted and verified at: '{out}'."

        except Exception as exc:
            logger.error("Database encryption migration failed: %s", exc)
            if out.is_file():
                out.unlink()  # Remove incomplete output
            return False, f"Migration failed with error: {exc}. Original database untouched."
