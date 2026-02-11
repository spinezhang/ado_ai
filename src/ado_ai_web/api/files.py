"""File browser API endpoints."""

from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ado_ai_cli.utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/api/files", tags=["files"])


class FileEntry(BaseModel):
    """File or directory entry."""
    name: str
    path: str
    is_directory: bool
    size: Optional[int] = None
    modified: Optional[str] = None


class BrowseResponse(BaseModel):
    """Response for browse directory endpoint."""
    current_path: str
    parent_path: Optional[str]
    entries: List[FileEntry]


# Security: Define allowed base directories for browsing
ALLOWED_BASE_DIRS = [
    Path.home(),  # User's home directory
    Path("/Users"),  # Mac users directory
    Path("/home"),  # Linux users directory
    Path("/var/www"),  # Common web root
    Path("/opt"),  # Optional software
]


def is_path_allowed(path: Path) -> bool:
    """Check if path is within allowed directories."""
    try:
        resolved_path = path.resolve()
        return any(
            str(resolved_path).startswith(str(base_dir.resolve()))
            for base_dir in ALLOWED_BASE_DIRS
            if base_dir.exists()
        )
    except (OSError, RuntimeError):
        return False


@router.get("/browse", response_model=BrowseResponse)
async def browse_directory(
    path: str = Query(default=str(Path.home()), description="Directory path to browse")
):
    """
    Browse server file system with security restrictions.

    Security features:
    - Only allows browsing within predefined base directories
    - Prevents directory traversal attacks
    - Hides system files and hidden files

    Args:
        path: Directory path to browse

    Returns:
        BrowseResponse with directory contents

    Raises:
        HTTPException: If path is invalid or not allowed
    """
    try:
        browse_path = Path(path).resolve()

        # Security check: Ensure path is within allowed directories
        if not is_path_allowed(browse_path):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: Path '{path}' is outside allowed directories"
            )

        # Check if path exists
        if not browse_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Path not found: {path}"
            )

        # Check if it's a directory
        if not browse_path.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"Path is not a directory: {path}"
            )

        # Get parent directory (if not at root)
        parent_path = None
        if browse_path != browse_path.parent:
            parent = browse_path.parent
            if is_path_allowed(parent):
                parent_path = str(parent)

        # List directory contents
        entries = []
        try:
            for item in sorted(browse_path.iterdir()):
                # Skip hidden files and system files
                if item.name.startswith('.'):
                    continue

                # Skip common system directories
                if item.name in ['System', 'Library', 'Applications', 'tmp', 'proc', 'sys', 'dev']:
                    continue

                try:
                    stat = item.stat()
                    entries.append(FileEntry(
                        name=item.name,
                        path=str(item),
                        is_directory=item.is_dir(),
                        size=stat.st_size if item.is_file() else None,
                        modified=str(stat.st_mtime)
                    ))
                except (OSError, PermissionError) as e:
                    # Skip files we can't access
                    logger.debug(f"Skipping inaccessible file {item}: {e}")
                    continue

        except PermissionError:
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: Cannot read directory '{path}'"
            )

        # Sort: directories first, then files, both alphabetically
        entries.sort(key=lambda x: (not x.is_directory, x.name.lower()))

        return BrowseResponse(
            current_path=str(browse_path),
            parent_path=parent_path,
            entries=entries
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error browsing directory {path}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to browse directory: {str(e)}"
        )


@router.get("/validate-path")
async def validate_path(path: str = Query(..., description="Path to validate")):
    """
    Validate if a path is accessible and allowed.

    Args:
        path: Path to validate

    Returns:
        Dictionary with validation result
    """
    try:
        check_path = Path(path).resolve()

        if not is_path_allowed(check_path):
            return {
                "valid": False,
                "message": "Path is outside allowed directories"
            }

        if not check_path.exists():
            return {
                "valid": False,
                "message": "Path does not exist"
            }

        if not check_path.is_dir():
            return {
                "valid": False,
                "message": "Path is not a directory"
            }

        return {
            "valid": True,
            "message": "Path is valid and accessible",
            "path": str(check_path)
        }

    except Exception as e:
        return {
            "valid": False,
            "message": f"Invalid path: {str(e)}"
        }
