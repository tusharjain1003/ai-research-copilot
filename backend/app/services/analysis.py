import logging

from pydantic import BaseModel, Field, ValidationError

from app.services.llm import LLMService, LLMError

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a business research analyst. Given website content and a research "
    "plan, extract a structured analysis of the company.\n\n"
    "Rules:\n"
    "- Only include information explicitly present in the provided website content.\n"
    '- If a section has no supporting information, set it to an empty list or "" — '
    "do not fabricate, guess, or infer details.\n"
    "- Be concise and factual. Extract, do not summarize creatively.\n\n"
    'Return ONLY valid JSON with exactly these four keys (no markdown, no code fences):\n'
    '  "company_overview": A 2-4 sentence string summarizing what the company does '
    "based solely on the website.\n"
    '  "products_and_services": A list of strings, each describing one product or '
    "service explicitly mentioned.\n"
    '  "target_customers": A string describing who the company sells to, as stated '
    "on the website.\n"
    '  "business_signals": A list of strings describing concrete business signals '
    "visible on the website (e.g. recent news, hiring, partnerships, funding, "
    "case studies, certifications).\n"
    "\n"
    "Omit any section where the source provides no relevant information "
    "(return empty list or empty string). Never make up facts."
)


class AnalysisOutput(BaseModel):
    company_overview: str = Field(default="")
    products_and_services: list[str] = Field(default_factory=list)
    target_customers: str = Field(default="")
    business_signals: list[str] = Field(default_factory=list)


class AnalysisService:

    @staticmethod
    def execute(
        company_name: str,
        website_url: str,
        research_objective: str,
        source_text: str,
        plan: dict,
    ) -> AnalysisOutput:
        source_available = bool(source_text.strip())

        user_prompt_parts = [
            f"Company Name: {company_name}",
            f"Website URL: {website_url}",
            f"Research Objective: {research_objective}",
        ]

        if source_available:
            user_prompt_parts.extend([
                "\n--- Website Content ---",
                source_text,
            ])
        else:
            user_prompt_parts.extend([
                "\n--- Website Content ---",
                "[No website content was fetched. All sections should be empty.]",
            ])

        user_prompt_parts.extend([
            "\n--- Research Plan ---",
            f"Research Focus: {plan.get('research_focus', [])}",
            f"Key Questions: {plan.get('key_questions', [])}",
        ])

        user_prompt = "\n".join(user_prompt_parts)

        if not source_available:
            logger.info(
                "Analysis: no source text for %s, returning empty output",
                company_name,
            )
            return AnalysisOutput()

        try:
            llm = LLMService()
            raw = llm.chat_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=3000,
            )
        except LLMError:
            logger.exception("Analysis: LLM call failed for %s", company_name)
            raise

        try:
            validated = AnalysisOutput.model_validate(raw)
        except ValidationError as e:
            logger.error(
                "Analysis: LLM output validation failed. Errors: %s | Raw: %s",
                e.errors(),
                raw,
            )
            raise

        logger.info(
            "Analysis: generated output for %s "
            "(overview=%d, products=%d, customers=%d, signals=%d)",
            company_name,
            len(validated.company_overview),
            len(validated.products_and_services),
            len(validated.target_customers),
            len(validated.business_signals),
        )

        return validated
