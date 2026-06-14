import { useState, type FormEvent } from "react";
import type { SessionCreate } from "../types";

interface SessionFormProps {
  onSubmit: (data: SessionCreate) => Promise<void>;
  loading: boolean;
  error: string | null;
}

function SessionForm({ onSubmit, loading, error }: SessionFormProps) {
  const [companyName, setCompanyName] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [researchObjective, setResearchObjective] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!companyName.trim() || !websiteUrl.trim() || !researchObjective.trim()) {
      return;
    }
    await onSubmit({
      company_name: companyName.trim(),
      website_url: websiteUrl.trim(),
      research_objective: researchObjective.trim(),
    });
  };

  const canSubmit = companyName.trim() && websiteUrl.trim() && researchObjective.trim();

  return (
    <form className="session-form" onSubmit={handleSubmit}>
      <div className="form-field">
        <label htmlFor="company_name">Company Name</label>
        <input
          id="company_name"
          type="text"
          value={companyName}
          onChange={(e) => setCompanyName(e.target.value)}
          placeholder="e.g. Acme Corp"
          required
          disabled={loading}
        />
      </div>
      <div className="form-field">
        <label htmlFor="website_url">Website URL</label>
        <input
          id="website_url"
          type="url"
          value={websiteUrl}
          onChange={(e) => setWebsiteUrl(e.target.value)}
          placeholder="e.g. https://acme.com"
          required
          disabled={loading}
        />
      </div>
      <div className="form-field">
        <label htmlFor="research_objective">Research Objective</label>
        <textarea
          id="research_objective"
          value={researchObjective}
          onChange={(e) => setResearchObjective(e.target.value)}
          placeholder="e.g. Understand their go-to-market strategy"
          rows={4}
          required
          disabled={loading}
        />
      </div>
      {error && <div className="form-error">{error}</div>}
      <button type="submit" className="btn btn-primary" disabled={loading || !canSubmit}>
        {loading ? "Creating..." : "Start Research"}
      </button>
    </form>
  );
}

export default SessionForm;
