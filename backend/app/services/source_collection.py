import logging
import re
from datetime import datetime, timezone
from html import unescape as html_unescape
from typing import Optional

import httpx

from app.core.url_validation import validate_external_url
from app.database.session import SessionLocal
from app.models.source import ResearchSource

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15.0
MAX_CONTENT_CHARS = 50000

USER_AGENT = (
    "Mozilla/5.0 (compatible; AIResearchCopilot/1.0; "
    "+https://github.com/anomalyco/research-copilot)"
)

BLOCK_TAGS = (
    r"br|/?(?:p|div|h[1-6]|li|tr|th|td|section|article|blockquote|pre|"
    r"ol|ul|dl|dt|dd|table|thead|tbody|tfoot|caption|details|summary)"
)

STRIP_TAGS = ["script", "style", "noscript", "svg", "nav", "footer", "header"]


class SourceCollectionResult:
    def __init__(
        self,
        source_text: str,
        source_metadata: list,
        warnings: list[str],
        errors: list[str],
    ) -> None:
        self.source_text = source_text
        self.source_metadata = source_metadata
        self.warnings = warnings
        self.errors = errors


class SourceCollectionService:

    @staticmethod
    def fetch_and_extract(
        session_id: str,
        website_url: str,
    ) -> SourceCollectionResult:
        try:
            try:
                validate_external_url(website_url)
            except ValueError as e:
                return SourceCollectionResult(
                    source_text="",
                    source_metadata=[],
                    warnings=[str(e)],
                    errors=["url_validation_failed"],
                )

            response = httpx.get(
                website_url,
                follow_redirects=True,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()

            html_content = response.text
            title = _extract_title(html_content)
            text = _extract_text(html_content)

            persist_warnings: list[str] = []
            try:
                _persist_source(
                    session_id=session_id,
                    url=str(response.url),
                    title=title,
                    content=text,
                )
            except Exception:
                logger.exception(
                    "Failed to persist ResearchSource for %s", response.url
                )
                persist_warnings.append("source_persistence_failed")

            return SourceCollectionResult(
                source_text=text,
                source_metadata=[
                    {
                        "url": str(response.url),
                        "title": title,
                        "source_type": "website",
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    }
                ],
                warnings=persist_warnings,
                errors=[],
            )

        except Exception as exc:
            logger.warning(
                "Failed to fetch %s: %s",
                website_url,
                exc,
            )
            return SourceCollectionResult(
                source_text="",
                source_metadata=[],
                warnings=["website_content_unavailable"],
                errors=["website_fetch_failed"],
            )


def _extract_title(html_content: str) -> Optional[str]:
    match = re.search(
        r"<title[^>]*>(.*?)</title>",
        html_content,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        raw = re.sub(r"<[^>]+>", "", match.group(1))
        return html_unescape(raw).strip()
    return None


def _extract_text(html_content: str) -> str:
    for tag in STRIP_TAGS:
        html_content = re.sub(
            rf"<{tag}[^>]*>.*?</{tag}>",
            "",
            html_content,
            flags=re.DOTALL | re.IGNORECASE,
        )

    html_content = re.sub(
        rf"<({BLOCK_TAGS})[^>]*>",
        "\n",
        html_content,
        flags=re.IGNORECASE,
    )

    text = re.sub(r"<[^>]+>", "", html_content)

    text = html_unescape(text)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    if len(text) > MAX_CONTENT_CHARS:
        text = text[:MAX_CONTENT_CHARS] + (
            "\n\n[Content truncated at 50000 characters]"
        )

    return text


def _persist_source(
    session_id: str,
    url: str,
    title: Optional[str],
    content: str,
) -> None:
    db = SessionLocal()
    try:
        source = ResearchSource(
            session_id=session_id,
            url=url,
            title=title,
            content=content,
            source_type="website",
            fetched_at=datetime.now(timezone.utc),
        )
        db.add(source)
        db.commit()
        logger.info(
            "Persisted ResearchSource for session %s, url=%s",
            session_id,
            url,
        )
    finally:
        db.close()
