"""AES-256-GCM vault layer.

Vault files live in `vault/`, encrypted with a user-local key generated at
build time. Decrypted payload is held in memory only; nothing sensitive
touches disk after assembly.

Key file: `vault/.key` (chmod 600). Fingerprint is the first 16 hex chars —
display it on every decrypt so the operator can confirm a stable key.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency: cryptography. Install with `pip install cryptography`."
    ) from exc


KEY_LEN = 32  # AES-256
NONCE_LEN = 12  # GCM standard
VAULT_MAGIC = b"HMS1"  # Hermes vault v1
VAULT_DIR = Path(__file__).resolve().parent.parent / "vault"


class VaultError(RuntimeError):
    """Raised when vault decryption / integrity check fails."""


class Vault:
    """AES-256-GCM vault for Hermes persona / attack / payload storage."""

    def __init__(self, key: bytes | None = None, base_dir: Path | None = None):
        self.base_dir = Path(base_dir) if base_dir else VAULT_DIR
        self.key_file = self.base_dir / ".key"
        if key is None:
            key = self._load_or_init_key()
        if len(key) != KEY_LEN:
            raise VaultError(f"Key must be {KEY_LEN} bytes; got {len(key)}")
        self.key = key
        self.fingerprint = key.hex()[:16]

    # ── key management ───────────────────────────────────────────────

    def _load_or_init_key(self) -> bytes:
        if self.key_file.exists():
            data = self.key_file.read_bytes()
            if len(data) != KEY_LEN:
                raise VaultError(
                    f"Key file corrupt (got {len(data)} bytes; expected {KEY_LEN})"
                )
            return data
        self.base_dir.mkdir(parents=True, exist_ok=True)
        key = os.urandom(KEY_LEN)
        self.key_file.write_bytes(key)
        os.chmod(self.key_file, 0o600)
        return key

    # ── encrypt / decrypt ────────────────────────────────────────────

    def encrypt(self, plaintext: bytes) -> bytes:
        nonce = os.urandom(NONCE_LEN)
        aes = AESGCM(self.key)
        ct = aes.encrypt(nonce, plaintext, None)
        return VAULT_MAGIC + nonce + ct

    def decrypt(self, blob: bytes) -> bytes:
        if not blob.startswith(VAULT_MAGIC):
            raise VaultError(f"Bad magic; not a Hermes vault file (got {blob[:4]!r})")
        nonce = blob[len(VAULT_MAGIC) : len(VAULT_MAGIC) + NONCE_LEN]
        ciphertext = blob[len(VAULT_MAGIC) + NONCE_LEN :]
        aes = AESGCM(self.key)
        return aes.decrypt(nonce, ciphertext, None)

    # ── file IO ─────────────────────────────────────────────────────

    def encrypt_file(self, src: Path, dst_name: str) -> Path:
        """Encrypt a file's bytes to `<dst_name>` under base_dir."""
        plaintext = Path(src).read_bytes()
        encrypted = self.encrypt(plaintext)
        out = self.base_dir / dst_name
        out.write_bytes(encrypted)
        os.chmod(out, 0o600)
        return out

    def decrypt_file(self, name: str) -> bytes:
        """Decrypt a vault file to bytes."""
        path = self.base_dir / name
        if not path.exists():
            raise VaultError(f"Vault file missing: {path}")
        return self.decrypt(path.read_bytes())

    # ── JSON helpers ────────────────────────────────────────────────

    def decrypt_json(self, name: str) -> dict[str, Any]:
        return json.loads(self.decrypt_file(name).decode("utf-8"))

    def encrypt_json(self, payload: dict[str, Any], dst_name: str) -> Path:
        plaintext = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return self.encrypt_file_bytes(plaintext, dst_name)

    def encrypt_file_bytes(self, plaintext: bytes, dst_name: str) -> Path:
        out = self.base_dir / dst_name
        out.write_bytes(self.encrypt(plaintext))
        os.chmod(out, 0o600)
        return out

    # ── info ────────────────────────────────────────────────────────

    def info(self) -> dict[str, Any]:
        """Return public vault info — never the key itself."""
        return {
            "fingerprint": self.fingerprint,
            "key_len": KEY_LEN,
            "base_dir": str(self.base_dir),
            "files": sorted(p.name for p in self.base_dir.glob("*") if p.is_file()),
        }
