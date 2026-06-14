import logging

from pydantic import BaseModel, Field, ValidationError

from app.services.llm import LLMService, LLMError

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a critical review analyst. Your job is to examine a company analysis "
    "alongside its source material and identify gaps, risks, and overreach.\n\n"
    "Rules:\n"
    "- Only identify risks and unknowns that are genuinely present or absent in the "
    "source material.\n"
    "- If the source text is empty or very thin, your unknowns list should be "
    "correspondingly large.\n"
    '- For "unsupported_claims", examine each claim in company_overview, '
    "products_and_services, target_customers, and business_signals. If a claim "
    "goes beyond what the source text actually says, flag it.\n"
    "- Be specific and cite which claim or gap you are referring to.\n"
    "- Do not hallucinate risks or challenges that have no basis.\n\n"
    'Return ONLY valid JSON with exactly these four keys (no markdown, no code fences):\n'
    '  "risks": A list of objects with keys "category" (str), "description" (str), '
    'and "severity" ("low", "medium", or "high"). Each risk must be grounded in '
    "what the source or analysis reveals about the company.\n"
    '  "unknowns": A list of strings, each describing a specific piece of '
    "information that would be valuable for decision-making but is missing from "
    "the source.\n"
    '  "unsupported_claims": A list of objects with keys "claim" (str) and '
    '"reason" (str). Only include claims from the analysis that are not fully '
    "supported by the source text. If all claims are supported, return an empty list.\n"
    '  "confidence_notes": A single string (2-4 sentences) summarizing how '
    "reliable the overall analysis is, what key information is missing, and how "
    "confident we should be in using this research for decision-making.\n"
    "\n"
    "Be honest about gaps. Confidence_notes should clearly state limitations."
)

RISK_SEVERITY_VALUES = {"low", "medium", "high"}


class RiskItem(BaseModel):
    category: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    severity: str = Field(..., min_length=1)


class ClaimItem(BaseModel):
    claim: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1)


class RiskUnknownsOutput(BaseModel):
    risks: list[RiskItem] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    unsupported_claims: list[ClaimItem] = Field(default_factory=list)
    confidence_notes: str = Field(default="")

    def model_post_init(self, __context) -> None:
        for r in self.risks:
            if r.severity not in RISK_SEVERITY_VALUES:
                r.severity = "medium"


class RiskUnknownsService:

    @staticmethod
    def execute(
        company_name: str,
        website_url: str,
        research_objective: str,
        source_text: str,
        analysis_output: dict,
        plan: dict,
    ) -> RiskUnknownsOutput:
        source_available = bool(source_text.strip())

        if not source_available:
            logger.info(
                "RiskUnknowns: no source text for %s, returning empty output",
                company_name,
            )
            return RiskUnknownsOutput(
                unknowns=["No website content was available to analyze."],
                confidence_notes=(
                    f"No source content was fetched for {company_name}. "
                    "All derived analysis is speculative. Further research is "
                    "required before any decisions can be made."
                ),
            )

        user_prompt_parts = [
            f"Company Name: {company_name}",
            f"Website URL: {website_url}",
            f"Research Objective: {research_objective}",
            "\n--- Source Text ---",
            source_text,
            "\n--- Analysis Output ---",
        ]

        ao = analysis_output or {}
        if ao.get("company_overview"):
            user_prompt_parts.append(
                f"company_overview: {ao['company_overview']}"
            )
        if ao.get("products_and_services"):
            user_prompt_parts.append(
                f"products_and_services: {ao['products_and_services']}"
            )
        if ao.get("target_customers"):
            user_prompt_parts.append(
                f"target_customers: {ao['target_customers']}"
            )
        if ao.get("business_signals"):
            user_prompt_parts.append(
                f"business_signals: {ao['business_signals']}"
            )

        user_prompt_parts.extend([
            "\n--- Research Plan ---",
            f"Research Focus: {plan.get('research_focus', [])}",
            f"Key Questions: {plan.get('key_questions', [])}",
        ])

        user_prompt = "\n".join(user_prompt_parts)

        try:
            llm = LLMService()
            raw = llm.chat_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.4,
                max_tokens=3000,
            )
        except LLMError:
            logger.exception(
                "RiskUnknowns: LLM call failed for %s", company_name
            )
            raise

        try:
            validated = RiskUnknownsOutput.model_validate(raw)
        except ValidationError as e:
            logger.error(
                "RiskUnknowns: LLM output validation failed. "
                "Errors: %s | Raw: %s",
                e.errors(),
                raw,
            )
            raise

        logger.info(
            "RiskUnknowns: generated for %s "
            "(risks=%d, unknowns=%d, unsupported=%d)",
            company_name,
            len(validated.risks),
            len(validated.unknowns),
            len(validated.unsupported_claims),
        )

        return validated
