import { Link } from "react-router-dom";
import type { Session } from "../types";

interface SessionListProps {
  sessions: Session[];
  loading: boolean;
  error: string | null;
}

function statusLabel(status: string): string {
  switch (status) {
    case "draft":
      return "Not Started";
    case "in_progress":
      return "In Progress";
    case "completed":
      return "Completed";
    case "failed":
      return "Failed";
    default:
      return status;
  }
}

function statusClass(status: string): string {
  switch (status) {
    case "completed":
      return "badge badge-completed";
    case "failed":
      return "badge badge-failed";
    case "in_progress":
      return "badge badge-running";
    default:
      return "badge badge-draft";
  }
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function SessionList({ sessions, loading, error }: SessionListProps) {
  if (loading) {
    return <div className="loading">Loading sessions...</div>;
  }

  if (error) {
    return <div className="error">Failed to load sessions: {error}</div>;
  }

  if (sessions.length === 0) {
    return (
      <div className="empty-state">
        <p>No research sessions yet.</p>
        <Link to="/sessions/new" className="btn btn-primary">Create your first session</Link>
      </div>
    );
  }

  return (
    <div className="session-list">
      {sessions.map((s) => (
        <Link to={`/sessions/${s.id}`} key={s.id} className="session-card">
          <div className="session-card-header">
            <h3>{s.company_name}</h3>
            <span className={statusClass(s.status)}>{statusLabel(s.status)}</span>
          </div>
          <p className="session-card-url">{s.website_url}</p>
          <p className="session-card-objective">{s.research_objective}</p>
          <p className="session-card-date">{formatDate(s.created_at)}</p>
        </Link>
      ))}
    </div>
  );
}

export default SessionList;
