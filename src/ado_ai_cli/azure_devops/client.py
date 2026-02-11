"""Azure DevOps API client."""

from typing import Any, Dict, List, Optional

from azure.devops.connection import Connection
from azure.devops.exceptions import AzureDevOpsServiceError
from azure.devops.v7_1.work_item_tracking import WorkItemTrackingClient
from azure.devops.v7_1.work_item_tracking.models import (
    CommentCreate,
    JsonPatchOperation,
    Wiql,
)
from msrest.authentication import BasicAuthentication
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ado_ai_cli.azure_devops.models import (
    UpdateWorkItemResult,
    WorkItem,
    WorkItemComment,
)
from ado_ai_cli.config import Settings
from ado_ai_cli.utils.exceptions import (
    AuthenticationError,
    AzureDevOpsError,
    WorkItemNotFoundError,
)
from ado_ai_cli.utils.logger import get_logger

logger = get_logger()


class AzureDevOpsClient:
    """Client for interacting with Azure DevOps API."""

    def __init__(self, settings: Settings):
        """
        Initialize Azure DevOps client.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.organization_url = settings.org_url_str
        self.project = settings.azure_devops_project
        self.pat = settings.azure_devops_pat

        # Initialize connection
        try:
            credentials = BasicAuthentication("", self.pat)
            self.connection = Connection(base_url=self.organization_url, creds=credentials)
            self.wit_client: WorkItemTrackingClient = self.connection.clients.get_work_item_tracking_client()
            logger.debug(f"Azure DevOps client initialized for {self.organization_url}")
        except Exception as e:
            logger.error(f"Failed to initialize Azure DevOps client: {str(e)}")
            raise AuthenticationError(f"Failed to authenticate with Azure DevOps: {str(e)}") from e

    @retry(
        retry=retry_if_exception_type((AzureDevOpsServiceError,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def get_work_item(self, work_item_id: int, expand: Optional[str] = "all") -> WorkItem:
        """
        Fetch a work item by ID.

        Args:
            work_item_id: Work item ID to fetch
            expand: Fields to expand (all, relations, fields, links, none)

        Returns:
            WorkItem model

        Raises:
            WorkItemNotFoundError: If work item doesn't exist
            AzureDevOpsError: For other API errors
        """
        try:
            logger.info(f"Fetching work item {work_item_id}")
            raw_work_item = self.wit_client.get_work_item(
                id=work_item_id, project=self.project, expand=expand
            )

            if raw_work_item is None:
                raise WorkItemNotFoundError(work_item_id)

            # Extract fields
            fields = raw_work_item.fields or {}

            # Map Azure DevOps fields to our model
            work_item = WorkItem(
                id=raw_work_item.id,
                work_item_type=fields.get("System.WorkItemType", "Unknown"),
                title=fields.get("System.Title", ""),
                state=fields.get("System.State", ""),
                description=fields.get("System.Description") or fields.get("Microsoft.VSTS.TCM.ReproSteps"),
                assigned_to=self._extract_identity_name(fields.get("System.AssignedTo")),
                created_by=self._extract_identity_name(fields.get("System.CreatedBy")),
                created_date=fields.get("System.CreatedDate"),
                changed_date=fields.get("System.ChangedDate"),
                area_path=fields.get("System.AreaPath"),
                iteration_path=fields.get("System.IterationPath"),
                tags=fields.get("System.Tags"),
                priority=fields.get("Microsoft.VSTS.Common.Priority"),
                remaining_work=fields.get("Microsoft.VSTS.Scheduling.RemainingWork"),
                completed_work=fields.get("Microsoft.VSTS.Scheduling.CompletedWork"),
                acceptance_criteria=fields.get("Microsoft.VSTS.Common.AcceptanceCriteria"),
                repro_steps=fields.get("Microsoft.VSTS.TCM.ReproSteps"),
                system_info=fields.get("Microsoft.VSTS.TCM.SystemInfo"),
                url=raw_work_item._links.additional_properties.get("html", {}).get("href") if raw_work_item._links else None,
                raw_fields=fields,
            )

            logger.debug(f"Successfully fetched work item {work_item_id}: {work_item.title}")
            return work_item

        except AzureDevOpsServiceError as e:
            if e.status_code == 404:
                raise WorkItemNotFoundError(work_item_id) from e
            elif e.status_code == 401 or e.status_code == 403:
                raise AuthenticationError("Invalid PAT or insufficient permissions") from e
            else:
                raise AzureDevOpsError(f"Azure DevOps API error: {str(e)}") from e
        except WorkItemNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching work item {work_item_id}: {str(e)}")
            raise AzureDevOpsError(f"Failed to fetch work item: {str(e)}") from e

    @retry(
        retry=retry_if_exception_type((AzureDevOpsServiceError,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def update_work_item(
        self, work_item_id: int, fields: Dict[str, Any], comment: Optional[str] = None
    ) -> UpdateWorkItemResult:
        """
        Update a work item.

        Args:
            work_item_id: Work item ID to update
            fields: Dictionary of fields to update (e.g., {"System.State": "Resolved"})
            comment: Optional comment to add to the work item

        Returns:
            UpdateWorkItemResult

        Raises:
            AzureDevOpsError: If update fails
        """
        try:
            logger.info(f"Updating work item {work_item_id} with fields: {list(fields.keys())}")

            # Build JSON patch document
            patch_document = []

            # Add field updates
            for field_path, value in fields.items():
                patch_document.append(
                    JsonPatchOperation(op="add", path=f"/fields/{field_path}", value=value)
                )

            # Update the work item
            updated_item = self.wit_client.update_work_item(
                document=patch_document,
                id=work_item_id,
                project=self.project,
            )

            # Add comment if provided
            if comment:
                self.add_comment(work_item_id, comment)

            logger.info(f"Successfully updated work item {work_item_id}")
            return UpdateWorkItemResult(
                success=True,
                work_item_id=work_item_id,
                updated_fields=list(fields.keys()),
            )

        except AzureDevOpsServiceError as e:
            error_msg = f"Azure DevOps API error: {str(e)}"
            logger.error(error_msg)
            return UpdateWorkItemResult(
                success=False,
                work_item_id=work_item_id,
                updated_fields=[],
                error_message=error_msg,
            )
        except Exception as e:
            error_msg = f"Failed to update work item: {str(e)}"
            logger.error(error_msg)
            return UpdateWorkItemResult(
                success=False,
                work_item_id=work_item_id,
                updated_fields=[],
                error_message=error_msg,
            )

    @retry(
        retry=retry_if_exception_type((AzureDevOpsServiceError,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def add_comment(self, work_item_id: int, comment: str) -> None:
        """
        Add a comment to a work item.

        Args:
            work_item_id: Work item ID
            comment: Comment text to add

        Raises:
            AzureDevOpsError: If adding comment fails
        """
        try:
            logger.debug(f"Adding comment to work item {work_item_id}")
            comment_create = CommentCreate(text=comment)
            self.wit_client.add_comment(
                request=comment_create,
                project=self.project,
                work_item_id=work_item_id,
            )
            logger.debug(f"Successfully added comment to work item {work_item_id}")
        except Exception as e:
            logger.error(f"Failed to add comment to work item {work_item_id}: {str(e)}")
            raise AzureDevOpsError(f"Failed to add comment: {str(e)}") from e

    def get_comments(self, work_item_id: int, top: int = 10) -> List[WorkItemComment]:
        """
        Get comments for a work item.

        Args:
            work_item_id: Work item ID
            top: Maximum number of comments to retrieve

        Returns:
            List of WorkItemComment models
        """
        try:
            logger.debug(f"Fetching comments for work item {work_item_id}")
            comments_result = self.wit_client.get_comments(
                project=self.project,
                work_item_id=work_item_id,
                top=top,
                order="desc",  # Most recent first
            )

            comments = []
            if comments_result and comments_result.comments:
                for comment in comments_result.comments:
                    comments.append(
                        WorkItemComment(
                            id=comment.id,
                            text=comment.text,
                            created_by=self._extract_identity_name(comment.created_by),
                            created_date=comment.created_date,
                            modified_date=comment.modified_date,
                        )
                    )

            logger.debug(f"Fetched {len(comments)} comments for work item {work_item_id}")
            return comments

        except Exception as e:
            logger.warning(f"Failed to fetch comments for work item {work_item_id}: {str(e)}")
            return []

    def _extract_identity_name(self, identity: Any) -> Optional[str]:
        """
        Extract display name from an identity object.

        Args:
            identity: Identity object or string

        Returns:
            Display name or None
        """
        if identity is None:
            return None

        if isinstance(identity, str):
            return identity

        if isinstance(identity, dict):
            return identity.get("displayName") or identity.get("uniqueName")

        # For IdentityRef objects
        if hasattr(identity, "display_name"):
            return identity.display_name
        elif hasattr(identity, "unique_name"):
            return identity.unique_name

        return str(identity)
