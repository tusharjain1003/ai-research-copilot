import logging

from pydantic import BaseModel

from app.models.report import ResearchReport

logger = logging.getLogger(__name__)


class ReportOutput(BaseModel):
    company_overview: str
    products_services: str
    target_customers: str
    business_signals: str
    risks_challenges: str
    discovery_questions: str
    outreach_strategy: str
    unknowns: str
    sources: str


_NONE = "Information not available."


def _fmt_list(items: list, prefix: str = "- ", fallback: str = _NONE) -> str:
    if not items:
        return fallback
    return "\n".join(f"{prefix}{item}" for item in items)


def _generate_discovery_questions(
    company_name: str,
    unknowns: list,
    risks: list,
    research_objective: str,
) -> list[str]:
    questions = []
    for u in unknowns:
        questions.append(
            f"What is {company_name}'s approach to {u.lower().rstrip('.')}?"
        )
    for r in risks:
        cat = r.get("category", "challenges")
        questions.append(
            f"How does {company_name} plan to address {cat.lower().rstrip('.')}?"
        )
    questions.append(
        f"What are {company_name}'s near-term priorities related to "
        f"{research_objective.lower().rstrip('.')}?"
    )
    if not questions:
        questions.append(
            f"What key initiatives is {company_name} currently pursuing?"
        )
    return questions


def _generate_outreach_strategy(
    company_name: str,
    overview: str,
    products: list,
    target_customers: str,
    research_objective: str,
) -> str:
    parts = [
        f"When reaching out to {company_name}, frame the conversation around "
        f"their need for {research_objective.lower().rstrip('.')}."
    ]
    if target_customers and target_customers != _NONE:
        parts.append(
            f"Research suggests they serve {target_customers.lower().rstrip('.')}. "
            "Position your value proposition accordingly."
        )
    if products:
        sample = products[:3]
        parts.append(
            f"Reference their specific offerings ({'; '.join(sample)}) to "
            "demonstrate familiarity and tailor the pitch."
        )
    parts.append(
        "Lead with relevant case studies or benchmarks from similar "
        "companies in their space."
    )
    return "\n".join(f"- {p}" for p in parts)


class ReportGenerationService:

    @staticmethod
    def build_report(
        company_name: str,
        website_url: str,
        research_objective: str,
        plan: dict,
        analysis_output: dict,
        risks_and_unknowns: dict,
        source_metadata: list,
    ) -> ReportOutput:
        ao = analysis_output or {}
        ru = risks_and_unknowns or {}
        unknowns = ru.get("unknowns", [])
        risks = ru.get("risks", [])

        company_overview = ao.get("company_overview", "") or _NONE
        products_services = _fmt_list(ao.get("products_and_services", []))
        target_customers = ao.get("target_customers", "") or _NONE
        business_signals = _fmt_list(
            ao.get("business_signals", []), fallback="No business signals identified."
        )
        risks_challenges = _fmt_list(
            [
                f"[{r.get('severity', 'unknown').upper()}] "
                f"{r.get('description', '')} ({r.get('category', 'general')})"
                for r in risks
                if r.get("description")
            ],
            fallback="No risks identified.",
        )

        dq = _generate_discovery_questions(
            company_name, unknowns, risks, research_objective
        )
        discovery_questions = _fmt_list(dq)

        outreach_strategy = _generate_outreach_strategy(
            company_name,
            company_overview,
            ao.get("products_and_services", []),
            target_customers,
            research_objective,
        )

        unknowns_str = _fmt_list(
            unknowns, fallback="No unknowns identified."
        )

        if source_metadata:
            sources = _fmt_list(
                [
                    (
                        f"{m.get('title', '')} ({m.get('url', '')})"
                        if m.get("title")
                        else m.get("url", "")
                    )
                    for m in source_metadata
                    if m.get("url")
                ],
                fallback=_NONE,
            )
        else:
            sources = "N/A (website content unavailable)."

        return ReportOutput(
            company_overview=company_overview,
            products_services=products_services,
            target_customers=target_customers,
            business_signals=business_signals,
            risks_challenges=risks_challenges,
            discovery_questions=discovery_questions,
            outreach_strategy=outreach_strategy,
            unknowns=unknowns_str,
            sources=sources,
        )

    @staticmethod
    def persist_report(
        session_id: str,
        report: ReportOutput,
    ) -> None:
        from app.database.session import SessionLocal

        db = SessionLocal()
        try:
            existing = (
                db.query(ResearchReport)
                .filter(ResearchReport.session_id == session_id)
                .first()
            )
            if existing:
                existing.company_overview = report.company_overview
                existing.products_services = report.products_services
                existing.target_customers = report.target_customers
                existing.business_signals = report.business_signals
                existing.risks_challenges = report.risks_challenges
                existing.discovery_questions = report.discovery_questions
                existing.outreach_strategy = report.outreach_strategy
                existing.unknowns = report.unknowns
                existing.sources = report.sources
            else:
                record = ResearchReport(
                    session_id=session_id,
                    company_overview=report.company_overview,
                    products_services=report.products_services,
                    target_customers=report.target_customers,
                    business_signals=report.business_signals,
                    risks_challenges=report.risks_challenges,
                    discovery_questions=report.discovery_questions,
                    outreach_strategy=report.outreach_strategy,
                    unknowns=report.unknowns,
                    sources=report.sources,
                )
                db.add(record)
            db.commit()
            logger.info("Persisted ResearchReport for session %s", session_id)
        except Exception:
            logger.exception(
                "Failed to persist ResearchReport for session %s", session_id
            )
            raise
        finally:
            db.close()
