"""Configuration API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ado_ai_web.database.session import get_db
from ado_ai_web.models.requests import UpdateConfigRequest
from ado_ai_web.models.responses import ConfigResponse, ErrorResponse
from ado_ai_web.services.settings_manager import SettingsManager

router = APIRouter(prefix="/api", tags=["configuration"])


@router.get("/config", response_model=ConfigResponse, responses={404: {"model": ErrorResponse}})
async def get_config(db: Session = Depends(get_db)):
    """
    Get current configuration with redacted credentials.

    Returns:
        ConfigResponse with current settings

    Raises:
        HTTPException: If no configuration found
    """
    manager = SettingsManager(db)
    user = manager.get_default_user()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="No configuration found. Please complete setup first."
        )

    redacted = manager.get_redacted_settings(user.id)
    if not redacted:
        raise HTTPException(
            status_code=404,
            detail="Settings not found"
        )

    return ConfigResponse(**redacted)


@router.put("/config", response_model=ConfigResponse, responses={404: {"model": ErrorResponse}})
async def update_config(request: UpdateConfigRequest, db: Session = Depends(get_db)):
    """
    Update configuration (partial updates supported).

    Only non-null fields in the request will be updated.

    Args:
        request: Configuration updates
        db: Database session

    Returns:
        ConfigResponse with updated settings

    Raises:
        HTTPException: If no configuration found or update fails
    """
    manager = SettingsManager(db)
    user = manager.get_default_user()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="No configuration found. Please complete setup first."
        )

    # Build update dictionary with only non-None values
    updates = {}
    if request.azure_devops_org_url is not None:
        updates["azure_devops_org_url"] = str(request.azure_devops_org_url)
    if request.azure_devops_project is not None:
        updates["azure_devops_project"] = request.azure_devops_project
    if request.azure_devops_pat is not None:
        updates["azure_devops_pat"] = request.azure_devops_pat
    if request.anthropic_api_key is not None:
        updates["anthropic_api_key"] = request.anthropic_api_key
    if request.work_folder_path is not None:
        updates["work_folder_path"] = request.work_folder_path
    if request.claude_model is not None:
        updates["claude_model"] = request.claude_model
    if request.auto_approve is not None:
        updates["auto_approve"] = request.auto_approve
    if request.max_tokens is not None:
        updates["max_tokens"] = request.max_tokens
    if request.temperature is not None:
        updates["temperature"] = request.temperature

    try:
        updated_settings = manager.update_settings(user.id, **updates)

        if not updated_settings:
            raise HTTPException(status_code=404, detail="Settings not found")

        redacted = manager.get_redacted_settings(user.id)
        return ConfigResponse(**redacted)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@router.get("/config/status")
async def get_config_status(db: Session = Depends(get_db)):
    """
    Check if setup is complete.

    Returns:
        Dictionary with configuration status
    """
    manager = SettingsManager(db)
    user = manager.get_default_user()

    return {
        "is_configured": user is not None,
        "user_id": user.id if user else None,
        "username": user.username if user else None,
    }
