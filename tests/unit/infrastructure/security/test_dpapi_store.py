"""Unit tests for Windows DPAPI Data Encryption Key management."""

import os
from pathlib import Path

import pytest

from veritrace.infrastructure.security.dpapi_store import DpapiDataEncryptionKey


def test_dpapi_availability():
    """Verify DPAPI availability check behaves properly on host platform."""
    store = DpapiDataEncryptionKey()
    if os.name == "nt":
        assert store.is_dpapi_available() is True
    else:
        assert store.is_dpapi_available() is False


@pytest.mark.skipif(os.name != "nt", reason="DPAPI requires native Windows platform")
def test_dpapi_protect_unprotect_roundtrip(tmp_path: Path):
    """Verify crypt32 DPAPI sealing and unsealing returns original bytes."""
    store = DpapiDataEncryptionKey(key_store_dir=tmp_path)
    secret_bytes = b"VERITRACE_SECRET_256_BIT_KEY_123"  # 32 bytes
    assert len(secret_bytes) == 32

    sealed = store.protect_key_bytes(secret_bytes, description="Test Roundtrip")
    assert sealed != secret_bytes
    assert len(sealed) > len(secret_bytes)

    unsealed = store.unprotect_key_bytes(sealed)
    assert unsealed == secret_bytes


@pytest.mark.skipif(os.name != "nt", reason="DPAPI requires native Windows platform")
def test_dpapi_corrupted_ciphertext_rejection(tmp_path: Path):
    """Verify unprotecting invalid or tampered ciphertext raises OSError."""
    store = DpapiDataEncryptionKey(key_store_dir=tmp_path)
    corrupted_bytes = b"\x00\x01\x02\x03CORRUPTED_CIPHERTEXT_BLOB_FOR_TESTING"

    with pytest.raises(OSError, match="CryptUnprotectData failed"):
        store.unprotect_key_bytes(corrupted_bytes)


@pytest.mark.skipif(os.name != "nt", reason="DPAPI requires native Windows platform")
def test_get_or_create_key_persistence(tmp_path: Path):
    """Verify key generation, disk persistence, and idempotent retrieval."""
    store1 = DpapiDataEncryptionKey(key_store_dir=tmp_path)

    # First call generates new key and writes sealed file
    key1 = store1.get_or_create_key()
    assert len(key1) == 32
    assert store1._key_file.is_file()

    # Second call using fresh store instance should read the sealed file and return identical key
    store2 = DpapiDataEncryptionKey(key_store_dir=tmp_path)
    key2 = store2.get_or_create_key()
    assert key2 == key1


@pytest.mark.skipif(os.name != "nt", reason="DPAPI requires native Windows platform")
def test_get_or_create_key_recovery_on_corrupt_file(tmp_path: Path):
    """Verify corrupt existing key file is recovered by generating a new valid key."""
    store = DpapiDataEncryptionKey(key_store_dir=tmp_path)
    # Write garbage to the key file
    store._key_file.write_bytes(b"garbage_not_a_valid_dpapi_blob")

    # Should log warning, generate a new valid 32-byte key, and overwrite the corrupt file
    new_key = store.get_or_create_key()
    assert len(new_key) == 32

    # Now reading it again should succeed
    reloaded_key = store.get_or_create_key()
    assert reloaded_key == new_key


@pytest.mark.skipif(os.name != "nt", reason="DPAPI requires native Windows platform")
def test_dpapi_secret_string_roundtrip_and_deletion(tmp_path: Path):
    """Verify arbitrary secret strings (e.g. Groq API keys) are sealed, restored, and deleted."""
    store = DpapiDataEncryptionKey(key_store_dir=tmp_path)
    api_key = "mock_secret_payload_value_999"

    # Save
    sealed_path = store.save_secret_string("groq_api_key", api_key)
    assert sealed_path.is_file()
    # Ensure plaintext is not exposed in file bytes
    raw_data = sealed_path.read_bytes()
    assert b"mock_secret_payload" not in raw_data

    # Load via separate store instance
    store2 = DpapiDataEncryptionKey(key_store_dir=tmp_path)
    loaded = store2.load_secret_string("groq_api_key")
    assert loaded == api_key

    # Delete
    deleted = store2.delete_secret_string("groq_api_key")
    assert deleted is True
    assert not sealed_path.exists()
    assert store2.load_secret_string("groq_api_key") is None
