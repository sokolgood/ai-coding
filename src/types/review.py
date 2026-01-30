from typing import Literal

from pydantic import BaseModel, Field


class RequestedChange(BaseModel):
    file: str | None = Field(
        default=None,
        description=(
            "Path to the file that needs to be changed. "
            "Use None if the change applies to multiple files or is general."
        ),
    )
    description: str = Field(
        description=(
            "Clear, actionable description of what needs to be changed. "
            "Be specific about what is wrong and what should be done."
        ),
    )
    rationale: str | None = Field(
        default=None,
        description=(
            "Optional explanation of why this change is needed. " "Helps understand the reasoning behind the request."
        ),
    )
    severity: Literal["blocker", "major", "minor"] = Field(
        default="major",
        description=(
            "Severity level: 'blocker' - must be fixed before merge, "
            "'major' - important issue, 'minor' - nice to have improvement."
        ),
    )


class ReviewReport(BaseModel):
    summary: str = Field(
        description=(
            "Brief summary of the review (2-4 sentences). "
            "Keep it concise and readable for better understanding. "
            "Highlight the main findings and overall assessment."
        ),
    )
    changes: list[RequestedChange] = Field(
        default_factory=list,
        description=(
            "List of specific changes requested. "
            "Empty list means no changes needed. "
            "Each change should be actionable and specific."
        ),
    )
    positives: list[str] = Field(
        default_factory=list,
        description=(
            "List of positive aspects found in the code. "
            "What was done well, good patterns, clean code, etc. "
            "Helps provide balanced feedback."
        ),
    )
    risks: list[str] = Field(
        default_factory=list,
        description=(
            "List of potential risks, concerns, or edge cases that should be considered. "
            "Not necessarily blockers, but things to be aware of."
        ),
    )
    verdict: Literal["PASS", "FAIL"] = Field(
        description=(
            "Final verdict: 'PASS' if the code is ready to merge (may have minor suggestions), "
            "'FAIL' if there are blocking issues that must be fixed before merge."
        ),
    )
