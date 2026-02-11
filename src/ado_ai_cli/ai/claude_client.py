"""Claude AI client for work item analysis."""

import json
from typing import Any, Dict, List, Optional

from anthropic import Anthropic, APIError, RateLimitError as AnthropicRateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ado_ai_cli.ai.prompts import SYSTEM_PROMPT, get_prompt_for_work_item
from ado_ai_cli.azure_devops.models import WorkItem, WorkItemComment
from ado_ai_cli.config import Settings
from ado_ai_cli.utils.exceptions import ClaudeAPIError, RateLimitError
from ado_ai_cli.utils.logger import get_logger

logger = get_logger()


class TokenUsage:
    """Track token usage and calculate costs."""

    def __init__(self, input_tokens: int = 0, output_tokens: int = 0):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

    @property
    def total_tokens(self) -> int:
        """Get total tokens used."""
        return self.input_tokens + self.output_tokens

    def calculate_cost(self, model: str) -> float:
        """
        Calculate cost based on Claude pricing.

        Args:
            model: Model name

        Returns:
            Cost in USD
        """
        # Claude Opus 4.6 pricing: $5 per million input tokens, $25 per million output tokens
        # Claude Sonnet 4.5 pricing: $1 per million input tokens, $5 per million output tokens
        if "opus" in model.lower():
            input_cost = (self.input_tokens / 1_000_000) * 5.00
            output_cost = (self.output_tokens / 1_000_000) * 25.00
        elif "sonnet" in model.lower():
            input_cost = (self.input_tokens / 1_000_000) * 1.00
            output_cost = (self.output_tokens / 1_000_000) * 5.00
        else:
            # Default to Opus pricing
            input_cost = (self.input_tokens / 1_000_000) * 5.00
            output_cost = (self.output_tokens / 1_000_000) * 25.00

        return input_cost + output_cost

    def __repr__(self) -> str:
        return f"TokenUsage(input={self.input_tokens}, output={self.output_tokens}, total={self.total_tokens})"


class AnalysisResult:
    """Result of work item analysis."""

    def __init__(
        self,
        analysis: str,
        solution: str,
        tasks: List[str],
        risks: List[str],
        suggested_status: str,
        suggested_remaining_work: float,
        comment: str,
        token_usage: TokenUsage,
        raw_response: Optional[str] = None,
        file_changes: Optional[List[Dict[str, str]]] = None,
    ):
        self.analysis = analysis
        self.solution = solution
        self.tasks = tasks
        self.risks = risks
        self.suggested_status = suggested_status
        self.suggested_remaining_work = suggested_remaining_work
        self.comment = comment
        self.token_usage = token_usage
        self.raw_response = raw_response
        self.file_changes = file_changes or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "analysis": self.analysis,
            "solution": self.solution,
            "tasks": self.tasks,
            "risks": self.risks,
            "suggested_status": self.suggested_status,
            "suggested_remaining_work": self.suggested_remaining_work,
            "comment": self.comment,
            "file_changes": self.file_changes,
            "token_usage": {
                "input_tokens": self.token_usage.input_tokens,
                "output_tokens": self.token_usage.output_tokens,
                "total_tokens": self.token_usage.total_tokens,
            },
        }


class ClaudeClient:
    """Client for interacting with Claude AI."""

    def __init__(self, settings: Settings):
        """
        Initialize Claude client.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.model = settings.claude_model
        self.max_tokens = settings.max_tokens or 4096
        self.temperature = settings.temperature or 0.7

        try:
            self.client = Anthropic(api_key=settings.anthropic_api_key)
            logger.debug(f"Claude client initialized with model {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Claude client: {str(e)}")
            raise ClaudeAPIError(f"Failed to initialize Claude client: {str(e)}") from e

    @retry(
        retry=retry_if_exception_type((APIError,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def analyze_work_item(
        self, work_item: WorkItem, recent_comments: Optional[List[WorkItemComment]] = None, custom_prompt: Optional[str] = None
    ) -> AnalysisResult:
        """
        Analyze a work item using Claude AI.

        Args:
            work_item: WorkItem to analyze
            recent_comments: Optional list of recent comments
            custom_prompt: Optional custom instructions from user

        Returns:
            AnalysisResult with AI analysis

        Raises:
            ClaudeAPIError: If API call fails
            RateLimitError: If rate limit is exceeded
        """
        try:
            logger.info(f"Analyzing work item {work_item.id} with Claude AI")

            # Build prompt
            user_prompt = get_prompt_for_work_item(work_item, recent_comments, custom_prompt)

            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )

            # Extract token usage
            token_usage = TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

            # Extract response text
            response_text = response.content[0].text
            logger.debug(f"Received response from Claude: {len(response_text)} characters")

            # Parse JSON response
            try:
                parsed_response = self._parse_json_response(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                logger.debug(f"Raw response: {response_text}")
                raise ClaudeAPIError(f"Failed to parse JSON response from Claude: {str(e)}") from e

            # Create AnalysisResult
            result = AnalysisResult(
                analysis=parsed_response.get("analysis", ""),
                solution=parsed_response.get("solution", ""),
                tasks=parsed_response.get("tasks", []),
                risks=parsed_response.get("risks", []),
                suggested_status=parsed_response.get("suggested_status", work_item.state),
                suggested_remaining_work=parsed_response.get("suggested_remaining_work", 0),
                comment=parsed_response.get("comment", ""),
                token_usage=token_usage,
                raw_response=response_text,
                file_changes=parsed_response.get("file_changes", []),
            )

            cost = token_usage.calculate_cost(self.model)
            logger.info(
                f"Analysis complete. Tokens: {token_usage}, Cost: ${cost:.4f}"
            )

            return result

        except AnthropicRateLimitError as e:
            retry_after = getattr(e, "retry_after", None)
            logger.error(f"Rate limit exceeded. Retry after: {retry_after}")
            raise RateLimitError(retry_after=retry_after) from e
        except APIError as e:
            logger.error(f"Claude API error: {str(e)}")
            raise ClaudeAPIError(f"Claude API error: {str(e)}") from e
        except ClaudeAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during analysis: {str(e)}")
            raise ClaudeAPIError(f"Failed to analyze work item: {str(e)}") from e

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON response from Claude, handling various formats.

        Args:
            response_text: Raw response text

        Returns:
            Parsed JSON dictionary

        Raises:
            json.JSONDecodeError: If parsing fails
        """
        # Try direct JSON parsing
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code blocks
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()
            return json.loads(json_str)
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()
            return json.loads(json_str)

        # Last resort: try to find JSON-like structure
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start != -1 and end > start:
            json_str = response_text[start:end]
            return json.loads(json_str)

        # If all else fails, raise error
        raise json.JSONDecodeError("Could not find valid JSON in response", response_text, 0)
