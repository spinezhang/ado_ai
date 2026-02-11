"""Prompt templates for Claude AI."""

from ado_ai_cli.azure_devops.models import WorkItem

SYSTEM_PROMPT = """You are an AI assistant specialized in analyzing and completing Azure DevOps work items.

Your role is to:
1. Thoroughly analyze work item requirements, descriptions, and acceptance criteria
2. Provide actionable solutions, implementation approaches, or fixes
3. Identify potential risks, edge cases, and considerations
4. Suggest appropriate status updates based on the analysis
5. Generate professional comments suitable for adding to the work item

Always respond in valid JSON format with the specified structure.
Be concise but comprehensive in your analysis."""


def build_work_item_analysis_prompt(work_item: WorkItem, recent_comments: list = None, custom_prompt: str = None) -> str:
    """
    Build a prompt for analyzing a work item.

    Args:
        work_item: WorkItem to analyze
        recent_comments: Optional list of recent comments
        custom_prompt: Optional custom instructions from user

    Returns:
        Formatted prompt string
    """
    context = work_item.get_context_for_ai()

    # Add recent comments if available
    if recent_comments:
        comments_text = "\n\nRecent Comments:\n"
        for idx, comment in enumerate(recent_comments, 1):
            comments_text += f"{idx}. [{comment.created_by}]: {comment.text}\n"
        context += comments_text

    prompt = f"""Analyze the following Azure DevOps work item and provide a comprehensive completion strategy.

{context}

Please provide your analysis in the following JSON format:

{{
  "analysis": "Brief analysis of the work item and its requirements (2-3 sentences)",
  "solution": "Detailed solution or implementation approach (be specific and actionable)",
  "tasks": [
    "List of specific tasks needed to complete this work item",
    "Each task should be clear and actionable",
    "Include testing and verification steps"
  ],
  "risks": [
    "Potential risks, edge cases, or considerations",
    "Dependencies or blockers that should be addressed",
    "Areas that might need additional clarification"
  ],
  "suggested_status": "Recommended status (e.g., 'Resolved', 'Active', 'Closed')",
  "suggested_remaining_work": 0,
  "comment": "Professional comment to add to the work item summarizing the analysis and solution (suitable for team visibility)",
  "file_changes": [
    {{
      "path": "relative/path/to/file.ext",
      "content": "Complete file content to write",
      "description": "Brief description of what changed"
    }}
  ]
}}

Important guidelines:
- For Bugs: Focus on root cause analysis, fix verification, and preventing recurrence
- For Tasks: Provide step-by-step implementation approach
- For User Stories: Ensure acceptance criteria are addressed, suggest test scenarios
- Be specific and actionable in your recommendations
- Consider the current state and suggest appropriate next steps
- The comment should be professional and suitable for team collaboration
- file_changes is optional - only include it if the user specifically requests file modifications in their custom prompt (e.g., "create a file", "update the code", "write to a file"). Each file change should include the complete file content.
"""

    # Add custom prompt if provided
    if custom_prompt:
        prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{custom_prompt}\n"

    return prompt


def build_bug_specific_prompt(work_item: WorkItem) -> str:
    """
    Build a prompt specifically for bug work items.

    Args:
        work_item: Bug work item

    Returns:
        Formatted prompt string
    """
    context = work_item.get_context_for_ai()

    prompt = f"""Analyze this bug and provide a comprehensive fix strategy.

{context}

Please provide your analysis in JSON format with these fields:

{{
  "analysis": "Root cause analysis of the bug",
  "solution": "Detailed fix approach with specific code changes or configuration updates",
  "tasks": [
    "Steps to implement the fix",
    "Testing steps to verify the fix",
    "Steps to prevent regression"
  ],
  "risks": [
    "Potential side effects of the fix",
    "Areas that might be impacted",
    "Additional testing needed"
  ],
  "suggested_status": "Resolved",
  "suggested_remaining_work": 0,
  "comment": "Professional comment summarizing the bug analysis and fix"
}}

Focus on:
1. Root cause identification
2. Specific fix implementation
3. Verification approach
4. Prevention of similar issues in the future
"""

    return prompt


def build_task_specific_prompt(work_item: WorkItem) -> str:
    """
    Build a prompt specifically for task work items.

    Args:
        work_item: Task work item

    Returns:
        Formatted prompt string
    """
    context = work_item.get_context_for_ai()

    prompt = f"""Analyze this task and provide a detailed implementation plan.

{context}

Please provide your analysis in JSON format with these fields:

{{
  "analysis": "Understanding of the task requirements and scope",
  "solution": "Step-by-step implementation approach",
  "tasks": [
    "Specific implementation steps",
    "Configuration or setup needed",
    "Testing and validation steps",
    "Documentation updates needed"
  ],
  "risks": [
    "Potential challenges or blockers",
    "Dependencies on other work items or systems",
    "Areas requiring clarification"
  ],
  "suggested_status": "Resolved",
  "suggested_remaining_work": 0,
  "comment": "Professional comment summarizing the implementation approach"
}}

Provide practical, actionable guidance for completing this task.
"""

    return prompt


def build_user_story_specific_prompt(work_item: WorkItem) -> str:
    """
    Build a prompt specifically for user story work items.

    Args:
        work_item: User story work item

    Returns:
        Formatted prompt string
    """
    context = work_item.get_context_for_ai()

    prompt = f"""Analyze this user story and provide an implementation strategy that meets the acceptance criteria.

{context}

Please provide your analysis in JSON format with these fields:

{{
  "analysis": "Understanding of the user story and acceptance criteria",
  "solution": "Implementation approach that fulfills the acceptance criteria",
  "tasks": [
    "Development tasks to implement the story",
    "Test scenarios based on acceptance criteria",
    "UI/UX considerations if applicable",
    "Documentation or user guide updates"
  ],
  "risks": [
    "Potential UX challenges",
    "Integration points with existing features",
    "Performance or scalability considerations"
  ],
  "suggested_status": "Resolved",
  "suggested_remaining_work": 0,
  "comment": "Professional comment describing how the acceptance criteria will be met"
}}

Ensure your solution directly addresses the acceptance criteria and provides clear test scenarios.
"""

    return prompt


def get_prompt_for_work_item(work_item: WorkItem, recent_comments: list = None, custom_prompt: str = None) -> str:
    """
    Get the appropriate prompt based on work item type.

    Args:
        work_item: WorkItem to analyze
        recent_comments: Optional list of recent comments
        custom_prompt: Optional custom instructions from user

    Returns:
        Formatted prompt string
    """
    work_item_type = work_item.work_item_type.lower()

    # Get base prompt based on work item type
    if "bug" in work_item_type:
        base_prompt = build_bug_specific_prompt(work_item)
    elif "task" in work_item_type:
        base_prompt = build_task_specific_prompt(work_item)
    elif "user story" in work_item_type or "story" in work_item_type:
        base_prompt = build_user_story_specific_prompt(work_item)
    else:
        # Default to general analysis prompt
        base_prompt = build_work_item_analysis_prompt(work_item, recent_comments, custom_prompt)
        return base_prompt  # Already has custom_prompt included

    # Add custom prompt if provided (for type-specific prompts)
    if custom_prompt:
        base_prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{custom_prompt}\n"

    return base_prompt
