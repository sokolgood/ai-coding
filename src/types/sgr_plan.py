from typing import Literal

from pydantic import BaseModel, Field


class ToolHint(BaseModel):
    name: str = Field(description="Name of the tool to use")
    purpose: str = Field(description="Brief description of why this tool is needed for this step")


class SGRStep(BaseModel):
    id: str = Field(description="Unique identifier for this step (e.g., 'step_1', 'step_2')")
    goal: str = Field(description="What this step aims to accomplish")
    suggested_tools: list[ToolHint] = Field(
        default_factory=list,
        description="Tools that might be useful for this step",
    )
    done_criteria: list[str] = Field(
        default_factory=list,
        description="Criteria that indicate this step is complete",
    )


class SGRPlan(BaseModel):
    role: Literal["coder", "reviewer"] = Field(description="Role this plan is for")
    objective: str = Field(description="Overall objective of the task")
    assumptions: list[str] = Field(
        default_factory=list,
        description="Assumptions made about the codebase or task",
    )
    steps: list[SGRStep] = Field(description="Ordered list of steps to execute")
    risks: list[str] = Field(
        default_factory=list,
        description="Potential risks or challenges to be aware of",
    )
    stop_conditions: list[str] = Field(
        default_factory=list,
        description="Conditions that indicate the task should stop (success or failure)",
    )
