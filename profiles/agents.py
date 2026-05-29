from profiles.schemas import ProfileSchema
from pydantic_ai import Agent, RunContext

profile_analyzer_agent = Agent(
    "google:gemini-2.5-flash",
    deps_type=str,
    output_type=ProfileSchema,
    system_prompt=(
        "You are an expert profile analyzer."
        "Your task is to analyze the profile and provide a detailed analysis of the profile."
    ),
    retries=2,
    model_settings={"temperature": 0.3},
)


@profile_analyzer_agent.system_prompt
def analyze_profile_submussion(ctx: RunContext[str]) -> str:
    return f"Profile's submission: {ctx.deps}"
