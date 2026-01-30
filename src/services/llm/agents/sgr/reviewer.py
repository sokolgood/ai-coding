from src.prompts.registry import PromptsRegistry
from src.services.llm.agents.base import Agent
from src.services.llm.engine import LLM
from src.services.llm.tools.base import Tool
from src.types.context import ReviewerContext
from src.types.main import Message
from src.types.sgr_plan import SGRPlan


class SGRReviewerAgent(Agent):
    def __init__(self, llm: LLM, prompts_registry: PromptsRegistry) -> None:
        super().__init__(llm, prompts_registry)

    async def run(self, ctx: ReviewerContext, tools: list[Tool]) -> SGRPlan:
        tools_brief = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])
        repo_context_str = ctx.repo.to_string()

        system_prompt = self.prompts_registry.sgr_reviewer.system.render(
            repo_context=repo_context_str,
            tools=tools_brief,
        )

        pr_diff_preview = ctx.pr_diff[:2000] + "..." if len(ctx.pr_diff) > 2000 else ctx.pr_diff
        task_context_parts = [
            f"Issue Description:\n{ctx.issue_body}",
            f"PR Diff:\n{pr_diff_preview}",
        ]
        if ctx.ci_summary:
            task_context_parts.append(f"CI Results:\n{ctx.ci_summary}")
        task_context = "\n\n".join(task_context_parts)

        user_prompt = self.prompts_registry.sgr_reviewer.user.render(
            task_context=task_context,
        )

        messages: list[Message] = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]

        completion = await self.llm.invoke(
            messages=messages,
            model="gpt-4o-mini",
            tools=None,
            response_format=SGRPlan,
        )

        message = completion.choices[0].message

        if message.refusal:
            return SGRPlan(role="reviewer", objective=f"Model refused: {message.refusal}", steps=[])

        if message.parsed:
            plan = message.parsed
            if plan.role != "reviewer":
                plan.role = "reviewer"
            return plan

        return SGRPlan(role="reviewer", objective="Failed to get parsed plan", steps=[])
