from langfuse.decorators import observe
from rich.console import Console
from rich.panel import Panel

from src.prompts.registry import PromptsRegistry
from src.services.llm.agents.base import Agent
from src.services.llm.engine import LLM
from src.services.llm.tools.base import Tool
from src.types.context import CoderContext
from src.types.main import Message
from src.types.sgr_plan import SGRPlan

console = Console()


class SGRCoderAgent(Agent):
    def __init__(self, llm: LLM, prompts_registry: PromptsRegistry, model_name: str = "gpt-4o-mini") -> None:
        super().__init__(llm, prompts_registry)
        self.model_name = model_name

    @observe(name="SGRCoderAgent")
    async def run(self, ctx: CoderContext, tools: list[Tool]) -> SGRPlan:
        tools_brief = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])
        repo_context_str = ctx.repo.to_string()

        system_prompt = self.prompts_registry.sgr_coder.system.render(
            repo_context=repo_context_str,
            tools=tools_brief,
        )
        user_prompt = self.prompts_registry.sgr_coder.user.render(
            task_context=f"Issue to implement:\n{ctx.issue_body}",
        )

        messages: list[Message] = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]

        completion = await self.llm.invoke(
            messages=messages,
            model=self.model_name,
            tools=None,
            response_format=SGRPlan,
        )

        message = completion.choices[0].message

        if message.refusal:
            error_msg = f"Model refused to create plan: {message.refusal}"
            console.print(Panel(error_msg, title="[bold red]SGR Plan Error[/bold red]", border_style="red"))
            return SGRPlan(role="coder", objective=f"Model refused: {message.refusal}", steps=[])

        if message.parsed:
            plan = message.parsed
            if plan.role != "coder":
                plan.role = "coder"
            return plan

        error_msg = "Failed to parse SGR plan from LLM response"
        console.print(Panel(error_msg, title="[bold red]SGR Plan Error[/bold red]", border_style="red"))
        return SGRPlan(role="coder", objective="Failed to get parsed plan", steps=[])
