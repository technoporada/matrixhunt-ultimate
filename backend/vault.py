"""At-rest encryption for the sensitive files.

What is protected: cookie jars (live session tokens), the session signing
secret, app settings. What is NOT: matrixhunt.db (public scraped listings -
encrypting it would be theater, and SQLAlchemy needs a plaintext file to open,
so "encryption" would just mean a plaintext temp copy).

Crypto: scrypt (n=2^15, r=8, p=1) derives a 32-byte key from the master
password; Fernet (AES-128-CBC + HMAC) envelopes each file with a random salt.
Wrong password -> InvalidToken, never partial plaintext.

Key provisioning: env MH_VAULT_PASSWORD, or POST /api/vault/unlock once per
process lifetime. Without a key everything works unencrypted (0600 files)
with a loud startup warning - fail-open for availability, never silent.
"""
import base64
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).parent
VERIFIER_PATH = HERE / ".vault_verifier"

_salt_len = 16


_fernet_cache = {}


def _fernet(password, salt):
    """Derive the Fernet key, cached per (password, salt).

    scrypt with n=2**15 costs ~0.6 s and 32 MiB per call, and seal/unseal
    ran on every settings read, every cookie-jar write and every proxied page
    load - read_settings() alone was called from four places per request.
    The salt changes when the password changes, so it belongs in the key."""
    key = (password, salt)
    hit = _fernet_cache.get(key)
    if hit is not None:
        return hit
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    from cryptography.fernet import Fernet
    kdf = Scrypt(salt=salt, length=32, n=2 ** 15, r=8, p=1)
    f = Fernet(base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8"))))
    # Bounded so a long-running process with a wrong password on every
    # unlock attempt cannot grow this without limit.
    if len(_fernet_cache) > 8:
        _fernet_cache.clear()
    _fernet_cache[key] = f
    return f


class Vault:
    """Process-wide key holder. Call unlock() once; lock() drops the key."""

    def __init__(self):
        self._password = None
        env = os.environ.get("MH_VAULT_PASSWORD")
        if env:
            self._password = env

    @property
    def locked(self):
        return not self._password

    def unlock(self, password):
        """Verify against the stored verifier (or create it on first use)."""
        if not password:
            return False
        if VERIFIER_PATH.exists():
            try:
                blob = json.loads(VERIFIER_PATH.read_text())
                salt = base64.b64decode(blob["salt"])
                _fernet(password, salt).decrypt(blob["token"].encode())
            except Exception:
                return False
        else:
            salt = os.urandom(_salt_len)
            token = _fernet(password, salt).encrypt(b"matrixhunt-vault")
            VERIFIER_PATH.write_text(json.dumps({
                "salt": base64.b64encode(salt).decode(),
                "token": token.decode()}))
            try:
                VERIFIER_PATH.chmod(0o600)
            except OSError:
                pass
        self._password = password
        # Seal any plaintext leftovers from before the first unlock.
        seal_plaintext_leftovers(self)
        return True

    def lock(self):
        self._password = None

    def seal(self, data: bytes) -> bytes:
        """Encrypt bytes for disk. Plain JSON envelope when locked."""
        if self.locked:
            return b"PLAIN:" + data
        salt = os.urandom(_salt_len)
        token = _fernet(self._password, salt).encrypt(data)
        return b"VAULT1:" + base64.b64encode(salt) + b":" + token

    def unseal(self, blob: bytes) -> bytes:
        if blob.startswith(b"VAULT1:"):
            if self.locked:
                raise ValueError("vault locked - unlock first")
            _, salt_b, token = blob.split(b":", 2)
            salt = base64.b64decode(salt_b)
            return _fernet(self._password, salt).decrypt(token)
        if blob.startswith(b"PLAIN:"):
            return blob[len(b"PLAIN:"):]
        # Legacy files written before the vault existed.
        return blob


vault = Vault()


def seal_plaintext_leftovers(v):
    """Encrypt pre-vault plaintext sensitive files in place (one-way)."""
    from sessions import JAR_DIR
    targets = list(JAR_DIR.glob("*.json"))
    for extra in (HERE / ".app_settings.json", HERE / ".session_secret"):
        if extra.exists():
            targets.append(extra)
    for path in targets:
        try:
            raw = path.read_bytes()
            if raw.startswith(b"VAULT1:"):
                continue
            path.write_bytes(v.seal(raw if raw.startswith(b"PLAIN:") else b"PLAIN:" + raw))
            try:
                path.chmod(0o600)
            except OSError:
                pass
        except OSError:
            continue


def cookie_to_dict(c):
    return {"name": c.name, "value": c.value or "", "domain": c.domain or "",
            "path": c.path or "/", "secure": bool(c.secure),
            "expires": c.expires, "discard": bool(c.discard)}


def cookie_from_dict(d):
    from http.cookiejar import Cookie
    return Cookie(version=0, name=d.get("name", ""), value=d.get("value", ""),
                  port=None, port_specified=False,
                  domain=d.get("domain", ""), domain_specified=bool(d.get("domain")),
                  domain_initial_dot=(d.get("domain") or "").startswith("."),
                  path=d.get("path", "/"), path_specified=True,
                  secure=bool(d.get("secure", False)), expires=d.get("expires"),
                  discard=bool(d.get("discard", True)), comment=None,
                  comment_url=None, rest={}, rfc2109=False)


def jar_fingerprint(path):
    """sha256 of a sealed file for the status endpoint. No content leaks."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]
