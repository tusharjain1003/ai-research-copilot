import logging

from pydantic import BaseModel, Field, ValidationError

from app.services.llm import LLMService, LLMError

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a senior business research analyst preparing a research plan for a "
    "sales or business development meeting. Given a company name, website URL, "
    "and research objective, produce a structured research plan."
    "\n\n"
    "Return ONLY valid JSON with exactly these three keys (no markdown, no code fences):\n"
    '  "research_focus": list of 3-6 specific areas to investigate about the company\n'
    '  "key_questions": list of 3-6 critical questions the research must answer\n'
    '  "business_hypotheses": list of 2-4 hypotheses about the company\'s situation or needs that the research should validate or invalidate\n'
    "\n"
    "Each item must be a concise, actionable string. Be specific to the company "
    "and objective provided."
)


class PlannerOutput(BaseModel):
    research_focus: list[str] = Field(..., min_length=1)
    key_questions: list[str] = Field(..., min_length=1)
    business_hypotheses: list[str] = Field(..., min_length=1)


class PlannerService:

    @staticmethod
    def execute(
        company_name: str,
        website_url: str,
        research_objective: str,
    ) -> PlannerOutput:
        user_prompt = (
            f"Company Name: {company_name}\n"
            f"Website URL: {website_url}\n"
            f"Research Objective: {research_objective}\n"
        )

        try:
            llm = LLMService()
            raw = llm.chat_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
        except LLMError:
            logger.exception("Planner: LLM call failed")
            raise

        try:
            validated = PlannerOutput.model_validate(raw)
        except ValidationError as e:
            logger.error(
                "Planner: LLM output validation failed. Errors: %s | Raw: %s",
                e.errors(),
                raw,
            )
            raise

        logger.info(
            "Planner: generated plan with %d focus areas, %d questions, %d hypotheses",
            len(validated.research_focus),
            len(validated.key_questions),
            len(validated.business_hypotheses),
        )

        return validated
