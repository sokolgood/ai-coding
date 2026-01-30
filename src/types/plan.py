from typing import Literal

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    step_number: int = Field(description="Sequential step number in the plan")
    action: str = Field(description="What action to take (e.g., 'read_file', 'search_code', 'modify_code', 'verify')")
    target: str = Field(description="Target of the action (file path, search query, etc.)")
    reason: str = Field(description="Why this step is needed")
    expected_outcome: str | None = Field(
        default=None,
        description="What we expect to achieve with this step",
    )


class ExecutionPlan(BaseModel):
    goal: str = Field(description="Overall goal of this execution plan")
    steps: list[PlanStep] = Field(description="Ordered list of steps to execute")
    estimated_complexity: Literal["simple", "medium", "complex"] = Field(
        default="medium",
        description="Estimated complexity of the plan",
    )


class ExecutionResult(BaseModel):
    success: bool = Field(description="Whether the execution completed successfully and the task is done")
    result_summary: str = Field(
        description=(
            "Brief summary of what was accomplished in this iteration. "
            "What was done, what changed, what was learned."
        ),
    )
    completion_reason: str | None = Field(
        default=None,
        description=(
            "If success is true, explain why the task is complete. "
            "What was implemented and how it addresses the issue."
        ),
    )
