import { useState } from "react";
import type { WorkflowRun, WorkflowStep } from "../types";

interface WorkflowProgressProps {
  run: WorkflowRun | null;
  steps: WorkflowStep[];
  onStart: () => void;
  starting: boolean;
}

const NODE_LABELS: Record<string, string> = {
  planner: "Planner",
  source_collection: "Source Collection",
  analysis: "Analysis",
  risk_unknowns: "Risks & Unknowns",
  quality_check: "Quality Check",
  enrich_unknowns: "Enrich Unknowns",
  report_generation: "Report Generation",
  failure_handler: "Failure Handler",
};

const NODE_ORDER = [
  "planner",
  "source_collection",
  "analysis",
  "risk_unknowns",
  "quality_check",
  "report_generation",
];

const LOOP_NODES = ["enrich_unknowns"];

function formatTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function calcDuration(startIso: string, endIso: string | null | undefined): string {
  if (!startIso || !endIso) return "";
  const diff = new Date(endIso).getTime() - new Date(startIso).getTime();
  if (diff < 1000) return `${diff}ms`;
  return `${(diff / 1000).toFixed(1)}s`;
}

function statusLabel(status: string): string {
  switch (status) {
    case "pending":
      return "Pending";
    case "running":
      return "Running";
    case "completed":
      return "Completed";
    case "failed":
      return "Failed";
    case "skipped":
      return "Skipped";
    default:
      return status;
  }
}

function outputPreview(data: Record<string, unknown> | null): string {
  if (!data) return "";
  const json = JSON.stringify(data, null, 1);
  if (json.length <= 300) return json;
  return json.slice(0, 300) + "\n… (truncated)";
}

function WorkflowProgress({ run, steps, onStart, starting }: WorkflowProgressProps) {
  if (!run) {
    return (
      <div className="workflow-not-started">
        <p>No research has been run yet.</p>
        <button className="btn btn-primary" onClick={onStart} disabled={starting}>
          {starting ? "Starting…" : "Run Research"}
        </button>
      </div>
    );
  }

  const isActive = run.status === "pending" || run.status === "running";

  const stepLookup = new Map<string, WorkflowStep>();
  for (const s of steps) {
    stepLookup.set(s.node_name, s);
  }

  const finishedSteps = steps.filter((s) => s.status !== "running" && s.status !== "pending");

  return (
    <div className="workflow-pipeline">
      <div className="pipeline-header">
        <span className={`pipeline-badge pipeline-badge-${run.status}`}>
          {statusLabel(run.status)}
        </span>
        {isActive && <span className="pipeline-spinner" />}
        {!isActive && steps.length > 0 && (
          <span className="pipeline-summary">
            {finishedSteps.length} steps completed
          </span>
        )}
      </div>

      <div className="pipeline-timeline">
        {NODE_ORDER.map((nodeName, idx) => {
          const step = stepLookup.get(nodeName);
          const isLast = idx === NODE_ORDER.length - 1;
          const isCurrent =
            isActive &&
            !step &&
            finishedSteps.every((s) => NODE_ORDER.indexOf(s.node_name) < idx);

          const enrichedNodes = steps.filter((s) => LOOP_NODES.includes(s.node_name));
          const hasEnriched = enrichedNodes.length > 0;
          const enrichmentAfter = nodeName === "quality_check";

          return (
            <TimelineNode
              key={nodeName}
              label={NODE_LABELS[nodeName] || nodeName}
              step={step}
              isCurrent={isCurrent}
              isLast={isLast}
              showEnrichmentBranch={enrichmentAfter && hasEnriched}
              enrichedSteps={enrichmentAfter ? enrichedNodes : []}
            />
          );
        })}
      </div>
    </div>
  );
}

interface TimelineNodeProps {
  label: string;
  step: WorkflowStep | undefined;
  isCurrent: boolean;
  isLast: boolean;
  showEnrichmentBranch: boolean;
  enrichedSteps: WorkflowStep[];
}

function TimelineNode({
  label,
  step,
  isCurrent,
  isLast,
  showEnrichmentBranch,
  enrichedSteps,
}: TimelineNodeProps) {
  const [showOutput, setShowOutput] = useState(false);

  const status: string = step?.status ?? (isCurrent ? "running" : "pending");
  const isFailed = status === "failed";

  const toggleOutput = () => setShowOutput((v) => !v);
  const hasOutput = step?.output_data && Object.keys(step.output_data).length > 0;

  return (
    <div className={`timeline-node-container ${isFailed ? "timeline-node-failed" : ""}`}>
      <div className="timeline-connector">
        <div className={`timeline-dot timeline-dot-${status}`} />
        {!isLast && <div className={`timeline-line timeline-line-${status}`} />}
      </div>

      <div className={`timeline-node timeline-node-${status}`}>
        <div className="timeline-node-main">
          <div className="timeline-node-left">
            <span className="timeline-node-name">{label}</span>
            <span className={`timeline-node-status timeline-node-status-${status}`}>
              {statusLabel(status)}
            </span>
          </div>
          <div className="timeline-node-right">
            {step?.created_at && status !== "pending" && (
              <span className="timeline-node-time" title={formatDate(step.created_at)}>
                {formatTime(step.created_at)}
              </span>
            )}
            {step?.created_at && step?.updated_at && status !== "running" && status !== "pending" && (
              <span className="timeline-node-duration">
                {calcDuration(step.created_at, step.updated_at)}
              </span>
            )}
          </div>
        </div>

        {status === "running" && (
          <div className="timeline-node-running-bar">
            <div className="timeline-running-fill" />
          </div>
        )}

        {step?.error_message && (
          <div className="timeline-node-error">{step.error_message}</div>
        )}

        {hasOutput && (status === "completed" || status === "failed") && (
          <div className="timeline-node-output">
            <button
              className="timeline-output-toggle"
              onClick={toggleOutput}
              type="button"
            >
              {showOutput ? "Hide output" : "Show output"}
            </button>
            {showOutput && (
              <pre className="timeline-output-json">
                {outputPreview(step!.output_data)}
              </pre>
            )}
          </div>
        )}
      </div>

      {showEnrichmentBranch && enrichedSteps.length > 0 && (
        <div className="timeline-enrichment-branch">
          {enrichedSteps.map((es) => (
            <EnrichmentNode key={es.id} step={es} />
          ))}
        </div>
      )}
    </div>
  );
}

function EnrichmentNode({ step }: { step: WorkflowStep }) {
  const [showOutput, setShowOutput] = useState(false);
  const status = step.status;
  const hasOutput = step?.output_data && Object.keys(step.output_data).length > 0;

  return (
    <div className={`timeline-node-container enrichment-node`}>
      <div className="timeline-connector enrichment-connector">
        <div className="timeline-dot timeline-dot-loop" />
      </div>
      <div className={`timeline-node timeline-node-${status}`}>
        <div className="timeline-node-main">
          <div className="timeline-node-left">
            <span className="timeline-node-name">{NODE_LABELS[step.node_name] || step.node_name}</span>
            <span className={`timeline-node-status timeline-node-status-${status}`}>
              {statusLabel(status)}
            </span>
          </div>
          <div className="timeline-node-right">
            {step.created_at && (
              <span className="timeline-node-time" title={formatDate(step.created_at)}>
                {formatTime(step.created_at)}
              </span>
            )}
          </div>
        </div>
        {step.error_message && (
          <div className="timeline-node-error">{step.error_message}</div>
        )}
        {hasOutput && (
          <div className="timeline-node-output">
            <button
              className="timeline-output-toggle"
              onClick={() => setShowOutput((v) => !v)}
              type="button"
            >
              {showOutput ? "Hide output" : "Show output"}
            </button>
            {showOutput && (
              <pre className="timeline-output-json">
                {outputPreview(step!.output_data)}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default WorkflowProgress;
