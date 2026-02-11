"""Configuration management using Pydantic Settings."""

from pathlib import Path
from typing import Optional

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ado_ai_cli.utils.exceptions import ConfigurationError


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Azure DevOps Settings
    azure_devops_org_url: HttpUrl = Field(
        ...,
        description="Azure DevOps organization URL",
        examples=["https://dev.azure.com/GroteIndustries"],
    )
    azure_devops_project: str = Field(
        ...,
        description="Azure DevOps project name",
        examples=["EucalyptusEmbedded"],
    )
    azure_devops_pat: str = Field(
        ...,
        description="Azure DevOps Personal Access Token",
        min_length=1,
    )

    # Anthropic Claude Settings
    anthropic_api_key: str = Field(
        ...,
        description="Anthropic API key for Claude",
        min_length=1,
    )
    claude_model: str = Field(
        default="claude-opus-4-6",
        description="Claude model to use",
        examples=["claude-opus-4-6", "claude-sonnet-4-5"],
    )

    # Application Settings
    log_level: str = Field(
        default="INFO",
        description="Logging level",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
    )
    auto_approve: bool = Field(
        default=False,
        description="Automatically approve work item updates without confirmation",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for API calls",
        ge=0,
        le=10,
    )
    timeout_seconds: int = Field(
        default=30,
        description="Timeout for API calls in seconds",
        ge=1,
        le=300,
    )
    dry_run: bool = Field(
        default=False,
        description="Simulate actions without making actual changes",
    )

    # Optional Advanced Settings
    rate_limit_requests_per_minute: Optional[int] = Field(
        default=60,
        description="Rate limit for API requests per minute",
        ge=1,
        le=1000,
    )
    max_tokens: Optional[int] = Field(
        default=4096,
        description="Maximum tokens for Claude API response",
        ge=100,
        le=8192,
    )
    temperature: Optional[float] = Field(
        default=0.7,
        description="Temperature for Claude API (creativity level)",
        ge=0.0,
        le=1.0,
    )

    @field_validator("azure_devops_pat", "anthropic_api_key")
    @classmethod
    def validate_credentials(cls, v: str, info) -> str:
        """Validate that credentials are not placeholder values."""
        field_name = info.field_name
        placeholder_values = [
            "your_personal_access_token_here",
            "your_anthropic_api_key_here",
            "<personal-access-token>",
            "<api-key>",
            "placeholder",
            "changeme",
            "",
        ]

        if v.lower() in placeholder_values:
            raise ValueError(
                f"{field_name} contains a placeholder value. "
                f"Please set a valid credential in your .env file."
            )

        return v

    @field_validator("azure_devops_org_url")
    @classmethod
    def validate_org_url(cls, v: HttpUrl) -> HttpUrl:
        """Validate that the organization URL is an Azure DevOps URL."""
        url_str = str(v)
        if "dev.azure.com" not in url_str and "visualstudio.com" not in url_str:
            raise ValueError(
                f"Invalid Azure DevOps organization URL: {url_str}. "
                f"Expected format: https://dev.azure.com/YourOrganization"
            )
        return v

    @property
    def org_url_str(self) -> str:
        """Get organization URL as string."""
        return str(self.azure_devops_org_url)

    def redact_sensitive_fields(self) -> dict:
        """Return settings with sensitive fields redacted for display."""
        data = self.model_dump()
        data["azure_devops_pat"] = "***REDACTED***"
        data["anthropic_api_key"] = "***REDACTED***"
        return data


def load_settings() -> Settings:
    """
    Load and validate settings from environment variables.

    Returns:
        Validated Settings instance

    Raises:
        ConfigurationError: If configuration is invalid or missing required fields
    """
    try:
        settings = Settings()
        return settings
    except Exception as e:
        raise ConfigurationError(
            f"Failed to load configuration: {str(e)}\n\n"
            f"Please ensure you have created a .env file with all required settings.\n"
            f"Copy .env.example to .env and fill in your credentials."
        ) from e


# Global settings instance (lazy loaded)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance (singleton pattern).

    Returns:
        Settings instance
    """
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings
