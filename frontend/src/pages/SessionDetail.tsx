import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import WorkflowProgress from "../components/WorkflowProgress";
import ReportView from "../components/ReportView";
import ChatPanel from "../components/ChatPanel";
import { api, ApiError } from "../api";
import type { Session, WorkflowStatusResponse, Report } from "../types";

type LoadState = "loading" | "loaded" | "error";

const POLL_INTERVAL_MS = 2000;
const STATUS_ACTIVE = new Set(["pending", "running"]);

function SessionDetail() {
  const { id } = useParams<{ id: string }>();
  const [session, setSession] = useState<Session | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);

  const [wfState, setWfState] = useState<WorkflowStatusResponse | null>(null);
  const [starting, setStarting] = useState(false);

  const [report, setReport] = useState<Report | null>(null);
  const [reportLoading, setReportLoading] = useState(true);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const wfRef = useRef(wfState);
  wfRef.current = wfState;

  const fetchSession = useCallback(async () => {
    if (!id) return;
    try {
      const s = await api.getSession(id);
      setSession(s);
      setLoadState("loaded");
    } catch (e) {
      setLoadState("error");
      if (e instanceof ApiError) {
        setLoadError(e.message);
      } else {
        setLoadError("An unexpected error occurred.");
      }
    }
  }, [id]);

  const fetchWorkflow = useCallback(async () => {
    if (!id) return;
    try {
      const wf = await api.getWorkflowStatus(id);
      setWfState(wf);
      return wf;
    } catch {
      return null;
    }
  }, [id]);

  const fetchReport = useCallback(async () => {
    if (!id) return;
    try {
      const r = await api.getReport(id);
      setReport(r);
    } catch {
      // report not yet available
    } finally {
      setReportLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchSession();
    fetchWorkflow();
    fetchReport();
  }, [fetchSession, fetchWorkflow, fetchReport]);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    stopPolling();
    intervalRef.current = setInterval(async () => {
      const wf = await fetchWorkflow();
      const runStatus = wf?.run?.status;
      if (!runStatus || !STATUS_ACTIVE.has(runStatus)) {
        stopPolling();
        if (runStatus === "completed") {
          fetchReport();
        }
      }
    }, POLL_INTERVAL_MS);
  }, [fetchWorkflow, fetchReport, stopPolling]);

  useEffect(() => {
    const current = wfRef.current;
    const isActive = current?.run?.status ? STATUS_ACTIVE.has(current.run.status) : false;
    if (isActive) {
      startPolling();
    }
    return stopPolling;
  }, [startPolling, stopPolling]);

  const handleStart = async () => {
    if (!id) return;
    setStarting(true);
    try {
      await api.startRun(id);
      const wf = await fetchWorkflow();
      if (wf?.run?.status && STATUS_ACTIVE.has(wf.run.status)) {
        startPolling();
      }
    } catch (e) {
      if (e instanceof ApiError) {
        setLoadError(e.message);
      }
    } finally {
      setStarting(false);
    }
  };

  if (loadState === "loading") {
    return <div className="page page-detail"><div className="loading">Loading session…</div></div>;
  }

  if (loadState === "error" || !session) {
    return (
      <div className="page page-detail">
        <Link to="/sessions" className="back-link">&larr; Back to sessions</Link>
        <div className="error">Failed to load session: {loadError}</div>
      </div>
    );
  }

  const runStatus = wfState?.run?.status;
  const isActive = runStatus ? STATUS_ACTIVE.has(runStatus) : false;
  const showReport = report && !reportLoading && !isActive;
  const showChat = !isActive && runStatus === "completed" && report !== null;

  return (
    <div className="page page-detail">
      <Link to="/sessions" className="back-link">&larr; Back to sessions</Link>

      <div className="session-info">
        <h1>{session.company_name}</h1>
        <p className="session-info-url">{session.website_url}</p>
        <p className="session-info-objective">
          <strong>Objective:</strong> {session.research_objective}
        </p>
      </div>

      <section className="detail-section">
        <h2>Research Workflow</h2>
        <WorkflowProgress
          run={wfState?.run ?? null}
          steps={wfState?.steps ?? []}
          onStart={handleStart}
          starting={starting}
        />
      </section>

      {showReport && (
        <section className="detail-section">
          <h2>Research Report</h2>
          <ReportView report={report} />
        </section>
      )}

      {showChat && (
        <section className="detail-section">
          <ChatPanel sessionId={session.id} />
        </section>
      )}
    </div>
  );
}

export default SessionDetail;
