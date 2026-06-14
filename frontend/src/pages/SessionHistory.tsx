import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import SessionList from "../components/SessionList";
import { api, ApiError } from "../api";
import type { Session } from "../types";

function SessionHistory() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSessions = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listSessions();
      setSessions(res.sessions);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError("An unexpected error occurred.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  return (
    <div className="page page-history">
      <div className="page-header">
        <h1>Research Sessions</h1>
        <Link to="/sessions/new" className="btn btn-primary">New Session</Link>
      </div>
      <SessionList sessions={sessions} loading={loading} error={error} />
    </div>
  );
}

export default SessionHistory;
