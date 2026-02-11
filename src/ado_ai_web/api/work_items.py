"""Work items API endpoints."""

from typing import List
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from ado_ai_web.database.session import get_db
from ado_ai_web.models.requests import AnalyzeWorkItemRequest
from ado_ai_web.models.responses import WorkItemResponse, AnalysisResponse, ErrorResponse
from ado_ai_web.models.database import WorkItemHistory
from ado_ai_web.services.settings_manager import SettingsManager
from ado_ai_web.services.workflow_service import WorkflowService

router = APIRouter(prefix="/api/work-items", tags=["work-items"])


@router.get("/{work_item_id}", response_model=WorkItemResponse, responses={404: {"model": ErrorResponse}})
async def get_work_item(work_item_id: int, db: Session = Depends(get_db)):
    """
    Fetch work item details from Azure DevOps.

    Args:
        work_item_id: Work item ID
        db: Database session

    Returns:
        WorkItemResponse with work item details

    Raises:
        HTTPException: If work item not found or fetch fails
    """
    settings_manager = SettingsManager(db)
    user = settings_manager.get_default_user()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="No configuration found. Please complete setup first."
        )

    workflow_service = WorkflowService(db)

    try:
        work_item_data = workflow_service.fetch_work_item(user.id, work_item_id)
        return WorkItemResponse(**work_item_data)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch work item: {str(e)}"
        )


@router.post("/{work_item_id}/analyze", response_model=AnalysisResponse, responses={500: {"model": ErrorResponse}})
async def analyze_work_item(
    work_item_id: int,
    request: AnalyzeWorkItemRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Analyze work item with AI (async operation).

    This endpoint starts the analysis in the background and returns immediately
    with a tracking ID. Use GET /api/work-items/history/{history_id} to check status.

    Args:
        work_item_id: Work item ID
        request: Analysis request with optional custom prompt
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        AnalysisResponse with tracking information

    Raises:
        HTTPException: If analysis fails to start
    """
    settings_manager = SettingsManager(db)
    user = settings_manager.get_default_user()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="No configuration found. Please complete setup first."
        )

    workflow_service = WorkflowService(db)

    try:
        # Start analysis in background
        history_id = workflow_service.analyze_work_item(
            user_id=user.id,
            work_item_id=work_item_id,
            custom_prompt=request.custom_prompt,
            work_folder_path=request.work_folder_path,
        )

        # Get initial status
        result = workflow_service.get_analysis_result(history_id)

        if not result:
            raise HTTPException(status_code=500, detail="Failed to create analysis record")

        return AnalysisResponse(
            work_item_id=work_item_id,
            status=result["status"],
            analysis=result["analysis_result"],
            token_usage=result["token_usage"],
            cost=result["cost"],
            created_at=result["created_at"],
            completed_at=result["completed_at"],
            error_message=result["error_message"],
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start analysis: {str(e)}"
        )


@router.get("/history/{history_id}", response_model=dict, responses={404: {"model": ErrorResponse}})
async def get_analysis_result(history_id: int, db: Session = Depends(get_db)):
    """
    Get full analysis result by history ID including work item details.

    Args:
        history_id: WorkItemHistory ID
        db: Database session

    Returns:
        Dictionary with complete analysis data

    Raises:
        HTTPException: If analysis not found
    """
    settings_manager = SettingsManager(db)
    user = settings_manager.get_default_user()

    if not user:
        raise HTTPException(status_code=404, detail="No user found")

    # Get history record
    history = db.query(WorkItemHistory).filter(
        WorkItemHistory.id == history_id,
        WorkItemHistory.user_id == user.id
    ).first()

    if not history:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis {history_id} not found"
        )

    # Return full details
    return {
        "id": history.id,
        "work_item_id": history.work_item_id,
        "work_item_type": history.work_item_type,
        "title": history.title,
        "status": history.status,
        "analysis_result": history.analysis_result,
        "custom_prompt": history.custom_prompt,
        "work_folder_path": history.work_folder_path,
        "token_usage": history.token_usage,
        "cost": history.cost,
        "error_message": history.error_message,
        "created_at": history.created_at.isoformat() if history.created_at else None,
        "completed_at": history.completed_at.isoformat() if history.completed_at else None,
    }


@router.get("/", response_model=List[dict])
async def list_work_items(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """
    List work item history.

    Args:
        limit: Maximum number of items to return (1-100)
        offset: Number of items to skip
        db: Database session

    Returns:
        List of work item history records
    """
    settings_manager = SettingsManager(db)
    user = settings_manager.get_default_user()

    if not user:
        return []

    # Query work items for this user, ordered by most recent first
    history_items = db.query(WorkItemHistory).filter(
        WorkItemHistory.user_id == user.id
    ).order_by(
        WorkItemHistory.created_at.desc()
    ).offset(offset).limit(limit).all()

    # Convert to list of dictionaries
    result = []
    for item in history_items:
        result.append({
            "id": item.id,
            "work_item_id": item.work_item_id,
            "work_item_type": item.work_item_type,
            "title": item.title,
            "status": item.status,
            "cost": item.cost,
            "custom_prompt": item.custom_prompt,
            "work_folder_path": item.work_folder_path,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "completed_at": item.completed_at.isoformat() if item.completed_at else None,
            "error_message": item.error_message,
        })

    return result


@router.post("/history/{history_id}/apply-files", responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def apply_file_changes(history_id: int, db: Session = Depends(get_db)):
    """
    Apply file changes from analysis result to the work folder.

    Args:
        history_id: WorkItemHistory ID
        db: Database session

    Returns:
        Dictionary with success status and results for each file

    Raises:
        HTTPException: If analysis not found or file operations fail
    """
    settings_manager = SettingsManager(db)
    user = settings_manager.get_default_user()

    if not user:
        raise HTTPException(status_code=404, detail="No user found")

    # Get history record
    history = db.query(WorkItemHistory).filter(
        WorkItemHistory.id == history_id,
        WorkItemHistory.user_id == user.id
    ).first()

    if not history:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis {history_id} not found"
        )

    # Check if work folder is set
    if not history.work_folder_path:
        raise HTTPException(
            status_code=400,
            detail="No work folder path specified for this analysis"
        )

    # Check if analysis has file changes
    if not history.analysis_result or not history.analysis_result.get("file_changes"):
        raise HTTPException(
            status_code=400,
            detail="No file changes found in analysis result"
        )

    work_folder = Path(history.work_folder_path)
    if not work_folder.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Work folder does not exist: {history.work_folder_path}"
        )

    file_changes = history.analysis_result.get("file_changes", [])
    results = []

    for file_change in file_changes:
        file_path_str = file_change.get("path")
        content = file_change.get("content")
        description = file_change.get("description", "")

        if not file_path_str or content is None:
            results.append({
                "path": file_path_str or "unknown",
                "success": False,
                "error": "Missing path or content"
            })
            continue

        try:
            # Resolve file path relative to work folder
            file_path = work_folder / file_path_str

            # Security check: Ensure file is within work folder
            resolved_path = file_path.resolve()
            if not str(resolved_path).startswith(str(work_folder.resolve())):
                results.append({
                    "path": file_path_str,
                    "success": False,
                    "error": "Path traversal detected - file must be within work folder"
                })
                continue

            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            file_path.write_text(content, encoding="utf-8")

            results.append({
                "path": file_path_str,
                "success": True,
                "absolute_path": str(resolved_path),
                "description": description
            })

        except Exception as e:
            results.append({
                "path": file_path_str,
                "success": False,
                "error": str(e)
            })

    # Check if all succeeded
    all_success = all(r["success"] for r in results)

    return {
        "success": all_success,
        "work_folder": str(work_folder),
        "files_processed": len(results),
        "files_succeeded": sum(1 for r in results if r["success"]),
        "files_failed": sum(1 for r in results if not r["success"]),
        "results": results
    }
