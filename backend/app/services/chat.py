import logging
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.models.chat import ChatMessage
from app.models.enums import MessageRole
from app.models.report import ResearchReport
from app.models.session import ResearchSession
from app.models.source import ResearchSource
from app.models.workflow import WorkflowRun, WorkflowStep
from app.schemas.chat import ChatHistoryResponse, ChatMessageResponse
from app.services.llm import LLMService, LLMError, LLMConfigurationError

logger = logging.getLogger(__name__)

MAX_SOURCE_CHARS = 20000
MAX_HISTORY_TURNS = 10
UNSUPPORTED_RESPONSE = (
    "I don't have enough information from the collected research to answer that."
)

SYSTEM_PROMPT = (
    "You are a research assistant. You have access to research data collected about "
    "a company. Answer the user's follow-up questions using ONLY the context below.\n\n"
    "Rules:\n"
    '- If the context contains the information needed, answer concisely and directly '
    "based on that information.\n"
    "- If the context does NOT contain enough information to answer the question, "
    'respond with EXACTLY this message (no additions, no variations):\n'
    f'"{UNSUPPORTED_RESPONSE}"\n'
    "- Do NOT speculate, guess, or invent information that is not present in the "
    "provided context.\n"
    "- Do NOT reference the context structure or mention that you are reading from "
    "a report. Just answer naturally.\n"
    "- Be concise. Prefer short paragraphs over lists unless listing is natural.\n\n"
    "### Context ###\n"
)


def _get_or_404(db: DBSession, session_id: str) -> ResearchSession:
    session = (
        db.query(ResearchSession)
        .filter(ResearchSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    return session


def _build_context(db: DBSession, session: ResearchSession) -> str:
    parts: list[str] = []

    parts.append(f"Company Name: {session.company_name}")
    parts.append(f"Website URL: {session.website}")
    parts.append(f"Research Objective: {session.research_objective}")

    report = (
        db.query(ResearchReport)
        .filter(ResearchReport.session_id == session.id)
        .first()
    )
    if report:
        parts.append("\n--- Research Report ---")
        for label, field in [
            ("Company Overview", report.company_overview),
            ("Products & Services", report.products_services),
            ("Target Customers", report.target_customers),
            ("Business Signals", report.business_signals),
            ("Risks & Challenges", report.risks_challenges),
            ("Discovery Questions", report.discovery_questions),
            ("Outreach Strategy", report.outreach_strategy),
            ("Unknowns", report.unknowns),
            ("Sources", report.sources),
        ]:
            if field:
                parts.append(f"{label}: {field}")

    source = (
        db.query(ResearchSource)
        .filter(ResearchSource.session_id == session.id)
        .order_by(ResearchSource.created_at.desc())
        .first()
    )
    if source and source.content:
        content = source.content
        if len(content) > MAX_SOURCE_CHARS:
            content = content[:MAX_SOURCE_CHARS] + "\n… [truncated]"
        parts.append(f"\n--- Website Content ---\n{content}")

    run = (
        db.query(WorkflowRun)
        .filter(
            WorkflowRun.session_id == session.id,
            WorkflowRun.status == "completed",
        )
        .order_by(WorkflowRun.created_at.desc())
        .first()
    )
    if run:
        steps = (
            db.query(WorkflowStep)
            .filter(WorkflowStep.run_id == run.id)
            .order_by(WorkflowStep.created_at.asc())
            .all()
        )
        workflow_outputs = []
        for step in steps:
            if step.output_data:
                node_key = step.node_name
                output = step.output_data
                summary = _summarize_output(node_key, output)
                if summary:
                    workflow_outputs.append(summary)
        if workflow_outputs:
            parts.append("\n--- Workflow Analysis Details ---")
            parts.extend(workflow_outputs)

    return "\n".join(parts)


def _summarize_output(node_name: str, output: dict) -> Optional[str]:
    if node_name == "analysis" and output.get("analysis_output"):
        ao = output["analysis_output"]
        summary_parts = []
        if ao.get("company_overview"):
            summary_parts.append(f"Overview: {ao['company_overview']}")
        products = ao.get("products_and_services", [])
        if products:
            summary_parts.append(f"Products: {'; '.join(products[:5])}")
        if ao.get("target_customers"):
            summary_parts.append(f"Customers: {ao['target_customers']}")
        signals = ao.get("business_signals", [])
        if signals:
            summary_parts.append(f"Signals: {'; '.join(signals[:5])}")
        return f"Analysis:\n" + "\n".join(summary_parts) if summary_parts else None

    if node_name == "risk_unknowns" and output.get("risks_and_unknowns"):
        ru = output["risks_and_unknowns"]
        summary_parts = []
        risks = ru.get("risks", [])
        if risks:
            for r in risks[:5]:
                summary_parts.append(
                    f"- [{r.get('severity', '?')}] {r.get('description', '')}"
                )
        unknowns = ru.get("unknowns", [])
        if unknowns:
            summary_parts.append(f"Unknowns: {'; '.join(unknowns[:5])}")
        return (
            "Risks & Unknowns:\n" + "\n".join(summary_parts)
            if summary_parts
            else None
        )

    if node_name == "planner" and output.get("plan"):
        plan = output["plan"]
        focus = plan.get("research_focus", [])
        questions = plan.get("key_questions", [])
        parts = []
        if focus:
            parts.append(f"Focus: {'; '.join(focus[:3])}")
        if questions:
            parts.append(f"Questions: {'; '.join(questions[:3])}")
        return "Plan:\n" + "\n".join(parts) if parts else None

    if node_name == "quality_check" and output.get("quality_result"):
        qr = output["quality_result"]
        return (
            f"Quality: passed={qr.get('passed', False)}, "
            f"missing={qr.get('missing_sections', [])}"
        )

    return None


def _format_history(db: DBSession, session_id: str) -> list[dict[str, str]]:
    recent = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(MAX_HISTORY_TURNS * 2)
        .all()
    )
    recent.reverse()
    return [{"role": m.role.value, "content": m.content} for m in recent]


class ChatService:

    @staticmethod
    def get_messages(db: DBSession, session_id: str) -> ChatHistoryResponse:
        _get_or_404(db, session_id)

        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )

        return ChatHistoryResponse(
            messages=[
                ChatMessageResponse(
                    id=m.id,
                    role=m.role.value,
                    content=m.content,
                    created_at=m.created_at,
                )
                for m in messages
            ]
        )

    @staticmethod
    def send_message(db: DBSession, session_id: str, text: str) -> ChatMessageResponse:
        session = _get_or_404(db, session_id)

        user_msg = ChatMessage(
            session_id=session_id,
            role=MessageRole.user,
            content=text,
        )
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)

        context = _build_context(db, session)
        history = _format_history(db, session_id)

        assistant_content = _call_llm(context, history)

        assistant_msg = ChatMessage(
            session_id=session_id,
            role=MessageRole.assistant,
            content=assistant_content,
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        return ChatMessageResponse(
            id=assistant_msg.id,
            role=assistant_msg.role.value,
            content=assistant_msg.content,
            created_at=assistant_msg.created_at,
        )


def _call_llm(context: str, history: list[dict[str, str]]) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n" + context},
    ]
    messages.extend(history)

    try:
        llm = LLMService()
        response = llm.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2,
            max_tokens=1000,
        )
        content = response.choices[0].message.content
        if content is None or not content.strip():
            return UNSUPPORTED_RESPONSE
        return content.strip()
    except LLMConfigurationError:
        logger.warning("LLM not configured for chat, returning unsupported response")
        return UNSUPPORTED_RESPONSE
    except LLMError:
        logger.exception("LLM call failed for follow-up chat")
        return UNSUPPORTED_RESPONSE
