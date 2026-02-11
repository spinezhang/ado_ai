"""SQLAlchemy database models for ADO AI Web Service."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """User account model (for future multi-user support)."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    work_items = relationship("WorkItemHistory", back_populates="user")
    file_logs = relationship("FileAccessLog", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class UserSettings(Base):
    """Encrypted user configuration and credentials."""

    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Encrypted credentials
    azure_devops_pat_encrypted = Column(Text, nullable=False)
    anthropic_api_key_encrypted = Column(Text, nullable=True)  # Optional - can use system config

    # Plain configuration
    azure_devops_org_url = Column(String(500), nullable=False)
    azure_devops_project = Column(String(255), nullable=False)
    claude_model = Column(String(100), default="claude-opus-4-6", nullable=False)
    work_folder_path = Column(String(1000), nullable=True)

    # Optional settings
    auto_approve = Column(Boolean, default=False, nullable=False)
    max_tokens = Column(Integer, default=4096, nullable=False)
    temperature = Column(Float, default=0.7, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    timeout_seconds = Column(Integer, default=30, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="settings")

    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id}, project='{self.azure_devops_project}')>"


class WorkItemHistory(Base):
    """History of processed work items with AI analysis."""

    __tablename__ = "work_item_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    work_item_id = Column(Integer, nullable=False, index=True)
    work_item_type = Column(String(100), nullable=True)
    title = Column(String(500), nullable=True)

    # Analysis data (stored as JSON)
    analysis_result = Column(JSON, nullable=True)  # Full AnalysisResult as JSON

    # Custom prompt provided by user
    custom_prompt = Column(Text, nullable=True)

    # Work folder path for file operations
    work_folder_path = Column(String(1000), nullable=True)

    # Status tracking
    status = Column(String(50), nullable=False, default="pending")
    # Status values: 'pending', 'analyzing', 'completed', 'failed'

    error_message = Column(Text, nullable=True)

    # Token usage and cost tracking
    token_usage = Column(JSON, nullable=True)  # {input_tokens, output_tokens}
    cost = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="work_items")

    def __repr__(self):
        return f"<WorkItemHistory(id={self.id}, work_item_id={self.work_item_id}, status='{self.status}')>"


class FileAccessLog(Base):
    """Audit trail for file operations."""

    __tablename__ = "file_access_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    work_item_id = Column(Integer, nullable=True)  # Optional - link to work item if part of analysis
    file_path = Column(String(1000), nullable=False)
    operation = Column(String(50), nullable=False)  # 'read', 'write', 'list', 'delete'
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="file_logs")

    def __repr__(self):
        return f"<FileAccessLog(id={self.id}, operation='{self.operation}', file='{self.file_path}')>"
