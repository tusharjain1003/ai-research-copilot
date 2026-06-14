import type { Report } from "../types";

interface ReportViewProps {
  report: Report;
}

function Section({ title, content }: { title: string; content: string }) {
  if (!content || content === "Information not available.") {
    return null;
  }
  return (
    <div className="report-section">
      <h3>{title}</h3>
      <div className="report-content">{renderContent(content)}</div>
    </div>
  );
}

function renderContent(text: string): React.ReactNode {
  const lines = text.split("\n").filter(Boolean);
  if (lines.length <= 1) {
    return <p>{text}</p>;
  }
  return (
    <ul>
      {lines.map((line, i) => {
        const clean = line.replace(/^[-*]\s*/, "");
        return <li key={i}>{clean}</li>;
      })}
    </ul>
  );
}

const SECTIONS: { key: keyof Report; title: string }[] = [
  { key: "company_overview", title: "Company Overview" },
  { key: "products_services", title: "Products & Services" },
  { key: "target_customers", title: "Target Customers" },
  { key: "business_signals", title: "Business Signals" },
  { key: "risks_challenges", title: "Risks & Challenges" },
  { key: "discovery_questions", title: "Suggested Discovery Questions" },
  { key: "outreach_strategy", title: "Suggested Outreach Strategy" },
  { key: "unknowns", title: "Unknowns" },
  { key: "sources", title: "Sources" },
];

function ReportView({ report }: ReportViewProps) {
  return (
    <div className="report-view">
      {SECTIONS.map(({ key, title }) => (
        <Section key={key} title={title} content={report[key]} />
      ))}
    </div>
  );
}

export default ReportView;
