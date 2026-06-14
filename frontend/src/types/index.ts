export interface Session {
  id: string;
  company_name: string;
  website_url: string;
  research_objective: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface SessionCreate {
  company_name: string;
  website_url: string;
  research_objective: string;
}

export interface SessionListResponse {
  sessions: Session[];
}

export interface WorkflowStep {
  id: string;
  node_name: string;
  status: string;
  input_data: Record<string, unknown> | null;
  output_data: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowRun {
  id: string;
  session_id: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowStatusResponse {
  run: WorkflowRun | null;
  steps: WorkflowStep[];
}

export interface RunStartResponse {
  run_id: string;
  session_id: string;
  status: string;
}

export interface Report {
  company_overview: string;
  products_services: string;
  target_customers: string;
  business_signals: string;
  risks_challenges: string;
  discovery_questions: string;
  outreach_strategy: string;
  unknowns: string;
  sources: string;
}
