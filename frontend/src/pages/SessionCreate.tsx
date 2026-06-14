import { useState } from "react";
import { useNavigate } from "react-router-dom";
import SessionForm from "../components/SessionForm";
import { api, ApiError } from "../api";
import type { SessionCreate as SessionCreateData } from "../types";

function SessionCreate() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (data: SessionCreateData) => {
    setLoading(true);
    setError(null);
    try {
      const session = await api.createSession(data);
      try {
        await api.startRun(session.id);
      } catch {
        // Research failed to start; user can retry on the detail page.
      }
      navigate(`/sessions/${session.id}`);
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

  return (
    <div className="page page-create">
      <h1>New Research Session</h1>
      <p className="page-subtitle">
        Enter a company name and website to generate a research report.
      </p>
      <SessionForm onSubmit={handleSubmit} loading={loading} error={error} />
    </div>
  );
}

export default SessionCreate;
