from pydantic import BaseModel, Field


class CoderResult(BaseModel):
    success: bool = Field(description="Whether the task was completed successfully")
    summary: str = Field(description="Brief summary of what was implemented or changed")
    files_modified: list[str] = Field(
        default_factory=list,
        description="List of file paths that were modified or created",
    )
