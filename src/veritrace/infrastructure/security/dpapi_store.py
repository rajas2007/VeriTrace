"""Windows Data Protection API (DPAPI) symmetric key management.

Protects Data Encryption Keys (DEK) using native Windows DPAPI (CryptProtectData /
CryptUnprotectData) bound to the active user's Windows logon credentials.
"""

from __future__ import annotations

import ctypes
import logging
import os
import secrets
from ctypes import wintypes
from pathlib import Path

logger = logging.getLogger("veritrace.infrastructure.security.dpapi_store")


# Native Windows API structures
class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


class DpapiDataEncryptionKey:
    """Manages creation, DPAPI sealing, unsealing, and storage of Data Encryption Keys (DEK)."""

    def __init__(self, key_store_dir: Path | str | None = None) -> None:
        if key_store_dir:
            self._store_dir = Path(key_store_dir)
        else:
            appdata = os.environ.get("LOCALAPPDATA", "")
            base = Path(appdata) / "VeriTrace" if appdata else Path.home() / ".veritrace"
            self._store_dir = base / "security"

        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._key_file = self._store_dir / "veritrace_dek.bin"

    def is_dpapi_available(self) -> bool:
        """Return True if running on Windows with access to crypt32.dll."""
        try:
            return hasattr(ctypes.windll, "crypt32") and hasattr(
                ctypes.windll.crypt32, "CryptProtectData"
            )
        except Exception:
            return False

    def protect_key_bytes(self, key_bytes: bytes, description: str = "VeriTrace DEK") -> bytes:
        """Encrypt key bytes using Windows DPAPI CryptProtectData."""
        if not self.is_dpapi_available():
            raise OSError("Windows DPAPI (crypt32.dll) is not available on this platform.")

        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        in_blob = DATA_BLOB(
            len(key_bytes),
            ctypes.cast(ctypes.create_string_buffer(key_bytes), ctypes.POINTER(ctypes.c_char)),
        )
        out_blob = DATA_BLOB()

        success = crypt32.CryptProtectData(
            ctypes.byref(in_blob),
            description,
            None,  # Optional entropy
            None,  # Reserved
            None,  # Prompt struct
            0,  # Flags
            ctypes.byref(out_blob),
        )

        if not success:
            err = ctypes.GetLastError()
            raise OSError(f"CryptProtectData failed with Windows error code: {err}")

        try:
            encrypted_data = ctypes.string_at(out_blob.pbData, out_blob.cbData)
            return encrypted_data
        finally:
            kernel32.LocalFree(out_blob.pbData)

    def unprotect_key_bytes(self, encrypted_bytes: bytes) -> bytes:
        """Decrypt DPAPI-sealed key bytes using CryptUnprotectData."""
        if not self.is_dpapi_available():
            raise OSError("Windows DPAPI (crypt32.dll) is not available on this platform.")

        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        in_blob = DATA_BLOB(
            len(encrypted_bytes),
            ctypes.cast(
                ctypes.create_string_buffer(encrypted_bytes), ctypes.POINTER(ctypes.c_char)
            ),
        )
        out_blob = DATA_BLOB()

        success = crypt32.CryptUnprotectData(
            ctypes.byref(in_blob),
            None,  # Description output
            None,  # Optional entropy
            None,  # Reserved
            None,  # Prompt struct
            0,  # Flags
            ctypes.byref(out_blob),
        )

        if not success:
            err = ctypes.GetLastError()
            raise OSError(f"CryptUnprotectData failed with Windows error code: {err}")

        try:
            plaintext = ctypes.string_at(out_blob.pbData, out_blob.cbData)
            return plaintext
        finally:
            kernel32.LocalFree(out_blob.pbData)

    def get_or_create_key(self) -> bytes:
        """Retrieve existing DPAPI-sealed key or generate and seal a new 256-bit AES key.

        Returns:
            Plaintext 256-bit key in memory only (never logged or persisted unencrypted).
        """
        if self._key_file.is_file():
            try:
                sealed_blob = self._key_file.read_bytes()
                key = self.unprotect_key_bytes(sealed_blob)
                if len(key) == 32:
                    return key
            except Exception as exc:
                logger.warning("Failed to unprotect existing DEK at '%s': %s", self._key_file, exc)

        # Generate a new cryptographically secure 256-bit symmetric key
        new_key = secrets.token_bytes(32)
        sealed = self.protect_key_bytes(new_key)
        self._key_file.write_bytes(sealed)
        logger.info(
            "Generated and DPAPI-sealed new 256-bit Data Encryption Key at: %s", self._key_file
        )
        return new_key

    def save_secret_string(self, secret_name: str, secret_value: str) -> Path:
        """Protect and persist an arbitrary secret string (e.g. API key) using DPAPI."""
        sealed_bytes = self.protect_key_bytes(
            secret_value.encode("utf-8"), description=f"VeriTrace Secret: {secret_name}"
        )
        target_file = self._store_dir / f"{secret_name}.enc"
        target_file.write_bytes(sealed_bytes)
        return target_file

    def load_secret_string(self, secret_name: str) -> str | None:
        """Unprotect and load a DPAPI-sealed secret string."""
        target_file = self._store_dir / f"{secret_name}.enc"
        if not target_file.is_file():
            return None
        try:
            sealed_bytes = target_file.read_bytes()
            plaintext_bytes = self.unprotect_key_bytes(sealed_bytes)
            return plaintext_bytes.decode("utf-8")
        except Exception as exc:
            logger.warning("Failed to unprotect secret '%s': %s", secret_name, exc)
            return None

    def delete_secret_string(self, secret_name: str) -> bool:
        """Delete a DPAPI-sealed secret file."""
        target_file = self._store_dir / f"{secret_name}.enc"
        if target_file.is_file():
            target_file.unlink()
            return True
        return False
