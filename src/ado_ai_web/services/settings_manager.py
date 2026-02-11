"""Settings manager for persistent configuration storage."""

from typing import Optional
from sqlalchemy.orm import Session

from ado_ai_web.models.database import User, UserSettings
from ado_ai_web.services.encryption import get_encryption_service
from ado_ai_web.services.system_config import get_system_config


class SettingsManager:
    """
    Manages user settings with encrypted credential storage.

    Handles CRUD operations for user configuration, including:
    - Encrypting/decrypting Azure DevOps PAT and Anthropic API keys
    - Persisting settings to database
    - Loading settings for use in clients
    """

    def __init__(self, db: Session):
        """
        Initialize settings manager with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.encryption = get_encryption_service()

    def create_user_and_settings(
        self,
        username: str,
        azure_devops_org_url: str,
        azure_devops_project: str,
        azure_devops_pat: str,
        anthropic_api_key: Optional[str] = None,
        work_folder_path: Optional[str] = None,
        claude_model: str = "claude-opus-4-6",
        auto_approve: bool = False,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        email: Optional[str] = None,
    ) -> tuple[User, UserSettings]:
        """
        Create a new user with encrypted settings.

        Args:
            username: Unique username
            azure_devops_org_url: Azure DevOps organization URL
            azure_devops_project: Project name
            azure_devops_pat: Personal Access Token (will be encrypted)
            anthropic_api_key: Optional Claude API key (will be encrypted). Falls back to system config if not provided.
            work_folder_path: Optional work folder path for file operations
            claude_model: Claude model to use
            auto_approve: Skip approval prompts
            max_tokens: Max tokens for Claude
            temperature: Temperature for Claude
            email: Optional email address

        Returns:
            Tuple of (User, UserSettings)

        Raises:
            ValueError: If username already exists or no API key available
        """
        # Check if username exists
        existing_user = self.db.query(User).filter(User.username == username).first()
        if existing_user:
            raise ValueError(f"Username '{username}' already exists")

        # Check if we have an API key (user-provided or system config)
        system_config = get_system_config()
        if not anthropic_api_key and not system_config.has_anthropic_api_key():
            raise ValueError("Anthropic API key must be provided or configured in system config")

        # Create user
        user = User(username=username, email=email, is_active=True)
        self.db.add(user)
        self.db.flush()  # Get user.id

        # Encrypt credentials
        pat_encrypted = self.encryption.encrypt(azure_devops_pat)
        # Only encrypt API key if provided (otherwise use system config fallback)
        api_key_encrypted = self.encryption.encrypt(anthropic_api_key) if anthropic_api_key else None

        # Create settings
        settings = UserSettings(
            user_id=user.id,
            azure_devops_pat_encrypted=pat_encrypted,
            anthropic_api_key_encrypted=api_key_encrypted,
            azure_devops_org_url=azure_devops_org_url,
            azure_devops_project=azure_devops_project,
            claude_model=claude_model,
            work_folder_path=work_folder_path,
            auto_approve=auto_approve,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        self.db.add(settings)
        self.db.commit()
        self.db.refresh(user)
        self.db.refresh(settings)

        return user, settings

    def get_user_settings(self, user_id: int) -> Optional[UserSettings]:
        """
        Get user settings by user ID.

        Args:
            user_id: User ID

        Returns:
            UserSettings or None if not found
        """
        return self.db.query(UserSettings).filter(UserSettings.user_id == user_id).first()

    def get_default_user(self) -> Optional[User]:
        """
        Get the default user (first active user).

        For single-user mode, returns the first user created.

        Returns:
            User or None if no users exist
        """
        return self.db.query(User).filter(User.is_active == True).first()

    def get_decrypted_credentials(self, user_id: int) -> Optional[dict]:
        """
        Get decrypted credentials for a user with system config fallback.

        Args:
            user_id: User ID

        Returns:
            Dictionary with decrypted PAT and API key, or None if not found
        """
        settings = self.get_user_settings(user_id)
        if not settings:
            return None

        # Get Anthropic API key (user-provided or system config fallback)
        if settings.anthropic_api_key_encrypted:
            anthropic_api_key = self.encryption.decrypt(settings.anthropic_api_key_encrypted)
        else:
            # Fallback to system config
            system_config = get_system_config()
            anthropic_api_key = system_config.get_anthropic_api_key()
            if not anthropic_api_key:
                raise ValueError("No Anthropic API key available (not in user settings or system config)")

        return {
            "azure_devops_pat": self.encryption.decrypt(settings.azure_devops_pat_encrypted),
            "anthropic_api_key": anthropic_api_key,
            "azure_devops_org_url": settings.azure_devops_org_url,
            "azure_devops_project": settings.azure_devops_project,
            "claude_model": settings.claude_model,
            "work_folder_path": settings.work_folder_path,
            "auto_approve": settings.auto_approve,
            "max_tokens": settings.max_tokens,
            "temperature": settings.temperature,
        }

    def update_settings(
        self,
        user_id: int,
        azure_devops_org_url: Optional[str] = None,
        azure_devops_project: Optional[str] = None,
        azure_devops_pat: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        work_folder_path: Optional[str] = None,
        claude_model: Optional[str] = None,
        auto_approve: Optional[bool] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Optional[UserSettings]:
        """
        Update user settings (partial updates supported).

        Args:
            user_id: User ID
            **kwargs: Fields to update (only non-None values are updated)

        Returns:
            Updated UserSettings or None if user not found
        """
        settings = self.get_user_settings(user_id)
        if not settings:
            return None

        # Update plain fields
        if azure_devops_org_url is not None:
            settings.azure_devops_org_url = azure_devops_org_url
        if azure_devops_project is not None:
            settings.azure_devops_project = azure_devops_project
        if work_folder_path is not None:
            settings.work_folder_path = work_folder_path
        if claude_model is not None:
            settings.claude_model = claude_model
        if auto_approve is not None:
            settings.auto_approve = auto_approve
        if max_tokens is not None:
            settings.max_tokens = max_tokens
        if temperature is not None:
            settings.temperature = temperature

        # Update encrypted fields if provided
        if azure_devops_pat is not None:
            settings.azure_devops_pat_encrypted = self.encryption.encrypt(azure_devops_pat)
        if anthropic_api_key is not None:
            settings.anthropic_api_key_encrypted = self.encryption.encrypt(anthropic_api_key)

        self.db.commit()
        self.db.refresh(settings)
        return settings

    def get_redacted_settings(self, user_id: int) -> Optional[dict]:
        """
        Get settings with credentials redacted for safe display.

        Args:
            user_id: User ID

        Returns:
            Dictionary with redacted credentials, or None if not found
        """
        settings = self.get_user_settings(user_id)
        if not settings:
            return None

        return {
            "azure_devops_org_url": settings.azure_devops_org_url,
            "azure_devops_project": settings.azure_devops_project,
            "azure_devops_pat": "***REDACTED***",
            "anthropic_api_key": "***REDACTED***",
            "claude_model": settings.claude_model,
            "work_folder_path": settings.work_folder_path,
            "auto_approve": settings.auto_approve,
            "max_tokens": settings.max_tokens,
            "temperature": settings.temperature,
            "is_configured": True,
        }

    def delete_user_and_settings(self, user_id: int) -> bool:
        """
        Delete user and all associated settings.

        Args:
            user_id: User ID

        Returns:
            True if deleted, False if user not found
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        self.db.delete(user)
        self.db.commit()
        return True
