"""Credential encryption/decryption service using Fernet symmetric encryption."""

import os
import base64
from cryptography.fernet import Fernet, InvalidToken


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive credentials.

    Uses Fernet (symmetric encryption) with AES-256 under the hood.
    Master key must be provided via ENCRYPTION_MASTER_KEY environment variable.
    """

    def __init__(self):
        """Initialize encryption service with master key from environment."""
        master_key = os.environ.get("ENCRYPTION_MASTER_KEY")

        if not master_key:
            # For development, generate a key if not set
            # WARNING: This is insecure for production - always set ENCRYPTION_MASTER_KEY
            print("WARNING: ENCRYPTION_MASTER_KEY not set. Generating temporary key.")
            print("Set ENCRYPTION_MASTER_KEY environment variable for production use.")
            master_key = Fernet.generate_key().decode()
            os.environ["ENCRYPTION_MASTER_KEY"] = master_key
            print(f"Temporary key: {master_key}")

        # Fernet expects bytes
        self.fernet = Fernet(master_key.encode())

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt (e.g., PAT token, API key)

        Returns:
            Base64-encoded encrypted string

        Raises:
            Exception: If encryption fails
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")

        try:
            encrypted_bytes = self.fernet.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            raise Exception(f"Encryption failed: {str(e)}")

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a ciphertext string.

        Args:
            ciphertext: The base64-encoded encrypted string

        Returns:
            Decrypted plaintext string

        Raises:
            InvalidToken: If decryption fails (wrong key or corrupted data)
        """
        if not ciphertext:
            raise ValueError("Cannot decrypt empty string")

        try:
            decrypted_bytes = self.fernet.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except InvalidToken:
            raise InvalidToken("Decryption failed: Invalid token or wrong encryption key")
        except Exception as e:
            raise Exception(f"Decryption failed: {str(e)}")

    def rotate_key(self, old_ciphertext: str, new_master_key: str) -> str:
        """
        Rotate encryption key by decrypting with old key and re-encrypting with new key.

        Args:
            old_ciphertext: Data encrypted with current key
            new_master_key: New encryption key to use

        Returns:
            Re-encrypted ciphertext with new key
        """
        # Decrypt with current key
        plaintext = self.decrypt(old_ciphertext)

        # Create new Fernet instance with new key
        new_fernet = Fernet(new_master_key.encode())

        # Encrypt with new key
        new_encrypted_bytes = new_fernet.encrypt(plaintext.encode())
        return new_encrypted_bytes.decode()


def generate_master_key() -> str:
    """
    Generate a new master encryption key.

    This should be called once during initial setup and the key
    should be securely stored (e.g., in environment variable,
    secrets manager, or key vault).

    Returns:
        Base64-encoded 32-byte key suitable for Fernet
    """
    key = Fernet.generate_key()
    return key.decode()


# Global encryption service instance
_encryption_service = None


def get_encryption_service() -> EncryptionService:
    """
    Get or create global encryption service instance.

    Returns:
        EncryptionService instance
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
