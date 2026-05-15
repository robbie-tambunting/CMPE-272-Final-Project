"""Generate sender Ed25519 signing keys and receiver X25519 key-exchange keys."""

from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, NoEncryption, PrivateFormat, PublicFormat,
)

KEYS_DIR = Path("keys")


def main() -> None:
    KEYS_DIR.mkdir(exist_ok=True)

    # Sender: Ed25519 signing keypair
    sign_priv = Ed25519PrivateKey.generate()
    sign_pub = sign_priv.public_key()
    (KEYS_DIR / "sender_sign_priv.pem").write_bytes(
        sign_priv.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    )
    (KEYS_DIR / "sender_sign_pub.pem").write_bytes(
        sign_pub.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    )

    # Receiver: X25519 key-exchange keypair
    recv_priv = X25519PrivateKey.generate()
    recv_pub = recv_priv.public_key()
    (KEYS_DIR / "receiver_x25519_priv.pem").write_bytes(
        recv_priv.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    )
    (KEYS_DIR / "receiver_x25519_pub.pem").write_bytes(
        recv_pub.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    )

    print(f"Keys written to {KEYS_DIR}/")
    print("  sender_sign_priv.pem / sender_sign_pub.pem  (Ed25519)")
    print("  receiver_x25519_priv.pem / receiver_x25519_pub.pem  (X25519)")


if __name__ == "__main__":
    main()
