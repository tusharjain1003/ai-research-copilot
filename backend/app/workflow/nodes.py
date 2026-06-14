import logging

from app.workflow.state import GraphState
from app.workflow.persistence import (
    get_db,
    resolve_active_run,
    create_step,
    complete_step,
    fail_step,
    fail_run,
    run_started,
    run_completed,
)
from app.services.planner import PlannerService
from app.services.source_collection import SourceCollectionService
from app.services.analysis import AnalysisService
from app.services.risk_unknowns import RiskUnknownsService
from app.services.report import ReportGenerationService

logger = logging.getLogger(__name__)


def _run_node(
    state: GraphState,
    node_name: str,
    work_fn,
) -> dict:
    db = get_db()
    step = None
    run = None
    try:
        run = resolve_active_run(db, state["session_id"])
        if run is None:
            existing_errors = list(state.get("errors", []))
            if not existing_errors:
                existing_errors.append(
                    f"No active workflow run for session {state['session_id']}"
                )
            return {
                "errors": existing_errors,
                "workflow_status": "failed",
            }

        if run.status.value == "pending":
            run_started(db, run)

        step = create_step(db, run.id, node_name, dict(state))

        updates = work_fn(state)

        complete_step(db, step, updates)
        return updates

    except Exception as e:
        logger.exception("Node '%s' failed: %s", node_name, e)
        if step is not None:
            fail_step(db, step, str(e))
        fail_run(db, run, str(e))
        existing_errors = list(state.get("errors", []))
        existing_errors.append(str(e))
        return {
            "errors": existing_errors,
            "workflow_status": "failed",
        }
    finally:
        db.close()


def planner(state: GraphState) -> dict:
    def work(state: GraphState) -> dict:
        output = PlannerService.execute(
            company_name=state["company_name"],
            website_url=state["website_url"],
            research_objective=state["research_objective"],
        )
        plan = {
            "research_focus": output.research_focus,
            "key_questions": output.key_questions,
            "business_hypotheses": output.business_hypotheses,
            "objective": state["research_objective"],
            "steps": output.research_focus,
        }
        return {"plan": plan, "workflow_status": "running"}

    return _run_node(state, "planner", work)


def source_collection(state: GraphState) -> dict:
    def work(state: GraphState) -> dict:
        result = SourceCollectionService.fetch_and_extract(
            session_id=state["session_id"],
            website_url=state["website_url"],
        )
        return {
            "source_text": result.source_text,
            "source_metadata": result.source_metadata,
            "warnings": list(state.get("warnings", [])) + result.warnings + result.errors,
            "errors": list(state.get("errors", [])),
        }

    return _run_node(state, "source_collection", work)


def analysis(state: GraphState) -> dict:
    def work(state: GraphState) -> dict:
        output = AnalysisService.execute(
            company_name=state["company_name"],
            website_url=state["website_url"],
            research_objective=state["research_objective"],
            source_text=state.get("source_text", ""),
            plan=state.get("plan", {}),
        )
        analysis_output = {
            "company_overview": output.company_overview,
            "products_and_services": output.products_and_services,
            "target_customers": output.target_customers,
            "business_signals": output.business_signals,
            "product_insights": output.products_and_services,
            "market_position": output.target_customers,
            "key_findings": output.business_signals,
        }
        return {"analysis_output": analysis_output}

    return _run_node(state, "analysis", work)


def risk_unknowns(state: GraphState) -> dict:
    def work(state: GraphState) -> dict:
        output = RiskUnknownsService.execute(
            company_name=state["company_name"],
            website_url=state["website_url"],
            research_objective=state["research_objective"],
            source_text=state.get("source_text", ""),
            analysis_output=state.get("analysis_output", {}),
            plan=state.get("plan", {}),
        )
        return {
            "risks_and_unknowns": {
                "risks": [r.model_dump() for r in output.risks],
                "unknowns": output.unknowns,
                "unsupported_claims": [
                    c.model_dump() for c in output.unsupported_claims
                ],
                "confidence_notes": output.confidence_notes,
            }
        }

    return _run_node(state, "risk_unknowns", work)


def quality_check(state: GraphState) -> dict:
    def work(state: GraphState) -> dict:
        source_text = state.get("source_text", "")
        source_length = len(source_text)

        analysis_output = state.get("analysis_output", {})
        risks = state.get("risks_and_unknowns", {})

        missing_sections = []

        if not analysis_output.get("company_overview"):
            missing_sections.append("company_overview")
        if not analysis_output.get("products_and_services"):
            missing_sections.append("products_and_services")
        if not analysis_output.get("target_customers"):
            missing_sections.append("target_customers")
        if not analysis_output.get("business_signals"):
            missing_sections.append("business_signals")
        if not risks.get("unknowns"):
            missing_sections.append("unknowns")

        passed = source_length >= 500 and len(missing_sections) == 0

        previous_quality = state.get("quality_result", {})
        enrich_retries = previous_quality.get("enrich_retries", 0)

        # Deterministic quality scoring
        source_coverage_score = min(source_length / 2000, 1.0) * 40
        completeness_score = (1 - len(missing_sections) / 5) * 40
        unknowns = risks.get("unknowns", [])
        unknown_quality_score = min(len(unknowns), 5) / 5 * 20

        research_quality_score = round(
            source_coverage_score + completeness_score + unknown_quality_score
        )

        if research_quality_score >= 80:
            confidence = "high"
        elif research_quality_score >= 50:
            confidence = "medium"
        else:
            confidence = "low"

        quality_result = {
            "passed": passed,
            "research_quality_score": research_quality_score,
            "confidence": confidence,
            "source_length": source_length,
            "missing_sections": missing_sections,
            "enrich_retries": enrich_retries,
        }

        return {"quality_result": quality_result}

    return _run_node(state, "quality_check", work)


_SECTION_GAPS = {
    "company_overview": {
        "research_gap": "Company overview, founding story, mission, leadership, and organizational size",
        "why_missing": "Not found or insufficiently covered in the source text",
        "recommended_source": "Company About page, LinkedIn company profile, or Crunchbase",
    },
    "products_and_services": {
        "research_gap": "Product catalog, service descriptions, features, pricing, and technology stack",
        "why_missing": "Source text did not contain detailed product or service information",
        "recommended_source": "Products/Services page, case studies, or G2/Capterra listings",
    },
    "target_customers": {
        "research_gap": "Target customer segments, industries served, geographic presence, and buyer personas",
        "why_missing": "Customer segmentation details were absent from the source text",
        "recommended_source": "Customer stories, testimonials page, or industry reports",
    },
    "business_signals": {
        "research_gap": "Recent news, growth indicators, partnerships, funding rounds, and hiring trends",
        "why_missing": "No recent business signals found in the available source text",
        "recommended_source": "Company blog, press releases, Crunchbase, or LinkedIn company page",
    },
    "unknowns": {
        "research_gap": "Identified unknowns and information gaps requiring further investigation",
        "why_missing": "Risk and unknowns analysis was incomplete or not generated",
        "recommended_source": "Direct outreach to company representatives or industry analyst reports",
    },
}


def enrich_unknowns(state: GraphState) -> dict:
    def work(state: GraphState) -> dict:
        current_retries = state["quality_result"].get("enrich_retries", 0)
        new_retries = current_retries + 1

        missing_sections = state["quality_result"].get("missing_sections", [])
        enriched_unknowns = state.get("risks_and_unknowns", {}).copy()

        enriched_items = enriched_unknowns.get("enriched_items", [])
        for section in missing_sections:
            gap = _SECTION_GAPS.get(section, {
                "research_gap": f"Missing information for {section}",
                "why_missing": "Not available in source text",
                "recommended_source": "Further research required",
            })
            enriched_items.append({
                "section": section,
                "research_gap": gap["research_gap"],
                "why_missing": gap["why_missing"],
                "recommended_source": gap["recommended_source"],
                "confidence": "low",
            })

        enriched_unknowns["enriched_items"] = enriched_items

        warnings = list(state.get("warnings", []))
        warnings.append(
            f"Quality below threshold after enrichment attempt {new_retries}. "
            "Forcing report generation."
        )

        updated_quality = dict(state.get("quality_result", {}))
        updated_quality["enrich_retries"] = new_retries

        updates = {
            "risks_and_unknowns": enriched_unknowns,
            "quality_result": updated_quality,
            "warnings": warnings,
        }
        return updates

    return _run_node(state, "enrich_unknowns", work)


def report_generation(state: GraphState) -> dict:
    def work(state: GraphState) -> dict:
        report = ReportGenerationService.build_report(
            company_name=state["company_name"],
            website_url=state["website_url"],
            research_objective=state["research_objective"],
            plan=state.get("plan", {}),
            analysis_output=state.get("analysis_output", {}),
            risks_and_unknowns=state.get("risks_and_unknowns", {}),
            source_metadata=state.get("source_metadata", []),
        )

        ReportGenerationService.persist_report(
            session_id=state["session_id"],
            report=report,
        )

        final_report = report.model_dump()

        db = get_db()
        try:
            run = resolve_active_run(db, state["session_id"])
            if run:
                run_completed(db, run)
        finally:
            db.close()

        return {
            "final_report": final_report,
            "workflow_status": "completed",
        }

    return _run_node(state, "report_generation", work)


def failure_handler(state: GraphState) -> dict:
    def work(state: GraphState) -> dict:
        errors = state.get("errors", [])
        warnings = state.get("warnings", [])
        logger.error(
            "Workflow failed for session %s. Errors: %s. Warnings: %s",
            state["session_id"],
            errors,
            warnings,
        )

        db = get_db()
        try:
            run = resolve_active_run(db, state["session_id"])
            if run:
                fail_run(db, run, str(errors))
        finally:
            db.close()

        return {
            "workflow_status": "failed",
            "final_report": {
                "error": "Workflow did not complete successfully.",
                "errors": errors,
            },
        }

    return _run_node(state, "failure_handler", work)
