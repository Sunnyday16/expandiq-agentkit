import { StrictMode, useCallback, useEffect, useMemo, useState } from "react";
import type { Root } from "react-dom/client";
import { createRoot } from "react-dom/client";
import {
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Loader2,
  Play,
  Search,
  ShieldAlert,
  SquareArrowOutUpRight,
} from "lucide-react";
import "./styles.css";

declare global {
  interface Window {
    __agentkitRoot?: Root;
  }
}

type RunStatus = "running" | "succeeded" | "terminated";
type RunReason = "step_cap" | "cost_cap" | "stuck" | "timeout" | "error" | "succeeded";

type Step = {
  step_number: number;
  tool_name: string;
  args: Record<string, unknown>;
  result: Record<string, unknown>;
  cost: number;
  created_at: string;
};

type Run = {
  id: string;
  goal: string;
  status: RunStatus;
  reason: RunReason | null;
  total_cost: number;
  started_at: string;
  finished_at: string | null;
  steps: Step[];
};

type RunListItem = Omit<Run, "steps">;

type RunListResponse = {
  items: RunListItem[];
  limit: number;
  offset: number;
};

const terminalMessages: Record<RunReason, string> = {
  succeeded: "Completed successfully.",
  step_cap: "Reached the maximum number of steps for this run.",
  cost_cap: "Reached the budget for this run.",
  stuck: "The agent kept repeating the same action, so the run was stopped.",
  timeout: "The run took too long and was stopped.",
  error: "The run stopped because an unexpected error occurred.",
};

async function requestJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function getFinalAnswer(run: Run | null): string | null {
  const finalStep = run?.steps.find((step) => step.tool_name === "final_answer");
  const content = finalStep?.result.content;
  return typeof content === "string" ? content : null;
}

function formatCurrency(value: number): string {
  return `$${value.toFixed(3)}`;
}

function parseBackendDate(value: string): Date {
  const hasTimezone = /(?:z|[+-]\d{2}:?\d{2})$/i.test(value);
  return new Date(hasTimezone ? value : `${value}Z`);
}

function formatRelativeTime(value: string): string {
  const then = parseBackendDate(value).getTime();
  const seconds = Math.max(1, Math.round((Date.now() - then) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

function describeStep(step: Step): string {
  const args = step.args;
  switch (step.tool_name) {
    case "search_docs":
      return `Searching documents for "${String(args.q ?? "the goal")}".`;
    case "fetch_doc":
      return `Opening document "${String(args.id ?? "selected document")}".`;
    case "summarise_text":
      return "Summarising the retrieved text.";
    case "web_search":
      return `Searching the web for "${String(args.q ?? "the goal")}".`;
    case "lookup_contact":
      return `Looking up contact "${String(args.name ?? "requested contact")}".`;
    case "send_email":
      return `Preparing email to ${String(args.to ?? "the selected contact")}.`;
    case "query_sql":
      return "Querying the mock database.";
    case "create_calendar_event":
      return `Creating calendar event "${String(args.title ?? "meeting")}".`;
    case "translate":
      return `Translating text to ${String(args.target_language ?? "the target language")}.`;
    case "fetch_weather":
      return `Checking weather for ${String(args.city ?? "the requested city")}.`;
    case "final_answer":
      return "Writing the final answer.";
    default:
      return `Running ${step.tool_name}.`;
  }
}

function statusTone(run: Run | RunListItem | null): string {
  if (!run) return "neutral";
  if (run.status === "running") return "running";
  if (run.status === "succeeded") return "success";
  if (run.reason === "cost_cap" || run.reason === "step_cap" || run.reason === "stuck") return "capped";
  return "error";
}

function StatusIcon({ run }: { run: Run | RunListItem | null }) {
  const tone = statusTone(run);
  if (tone === "success") return <CheckCircle2 aria-hidden="true" />;
  if (tone === "running") return <Loader2 className="spin" aria-hidden="true" />;
  if (tone === "capped") return <ShieldAlert aria-hidden="true" />;
  if (tone === "error") return <AlertCircle aria-hidden="true" />;
  return <Clock3 aria-hidden="true" />;
}

function StatusBadge({ run }: { run: Run | RunListItem | null }) {
  const reason = run?.reason ?? null;
  const label = run?.status === "running" ? "Running" : reason ? terminalMessages[reason] : "No run selected";

  return (
    <div className={`status-badge ${statusTone(run)}`}>
      <StatusIcon run={run} />
      <span>{label}</span>
      {reason && <code>{reason}</code>}
    </div>
  );
}

function Timeline({ run }: { run: Run | null }) {
  if (!run) {
    return (
      <div className="empty-state">
        <Search aria-hidden="true" />
        <p>Start a run or choose one from the list.</p>
      </div>
    );
  }

  if (run.steps.length === 0) {
    return (
      <div className="empty-state">
        <Loader2 className="spin" aria-hidden="true" />
        <p>The agent is starting.</p>
      </div>
    );
  }

  return (
    <ol className="timeline" aria-label="Run steps">
      {run.steps.map((step) => (
        <li key={`${step.step_number}-${step.tool_name}`} className="timeline-item">
          <div className="step-marker">{step.step_number}</div>
          <div className="step-body">
            <div className="step-main">
              <span>{describeStep(step)}</span>
              <small>{formatCurrency(step.cost)}</small>
            </div>
            <details>
              <summary>Raw details</summary>
              <pre>{JSON.stringify({ args: step.args, result: step.result }, null, 2)}</pre>
            </details>
          </div>
        </li>
      ))}
    </ol>
  );
}

function PastRuns({
  runs,
  selectedRunId,
  isLoading,
  onSelect,
}: {
  runs: RunListItem[];
  selectedRunId: string | null;
  isLoading: boolean;
  onSelect: (runId: string) => void;
}) {
  return (
    <aside className="sidebar" aria-label="Past runs">
      <div className="sidebar-header">
        <h2>Past runs</h2>
        {isLoading && <Loader2 className="spin small-icon" aria-label="Loading past runs" />}
      </div>
      {runs.length === 0 ? (
        <p className="muted">No runs yet.</p>
      ) : (
        <ul className="run-list">
          {runs.map((run) => (
            <li key={run.id}>
              <button
                className={run.id === selectedRunId ? "run-row selected" : "run-row"}
                type="button"
                onClick={() => onSelect(run.id)}
              >
                <span className={`run-glyph ${statusTone(run)}`}>
                  <StatusIcon run={run} />
                </span>
                <span className="run-row-text">
                  <span>{run.goal}</span>
                  <small>{formatRelativeTime(run.started_at)}</small>
                </span>
                <ChevronRight aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}

function App() {
  const [goal, setGoal] = useState("");
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [currentRun, setCurrentRun] = useState<Run | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isLoadingRuns, setIsLoadingRuns] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const finalAnswer = useMemo(() => getFinalAnswer(currentRun), [currentRun]);

  const loadRuns = useCallback(async () => {
    setIsLoadingRuns(true);
    try {
      const data = await requestJson<RunListResponse>("/api/runs?limit=25&offset=0");
      setRuns(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load past runs.");
    } finally {
      setIsLoadingRuns(false);
    }
  }, []);

  const loadRun = useCallback(async (runId: string) => {
    const run = await requestJson<Run>(`/api/runs/${runId}`);
    setCurrentRun(run);
    setSelectedRunId(run.id);
    return run;
  }, []);

  useEffect(() => {
    void loadRuns();
  }, [loadRuns]);

  useEffect(() => {
    if (!selectedRunId || currentRun?.status !== "running") return undefined;
    const interval = window.setInterval(() => {
      void loadRun(selectedRunId).then((run) => {
        if (run.status !== "running") void loadRuns();
      });
    }, 1000);
    return () => window.clearInterval(interval);
  }, [currentRun?.status, loadRun, loadRuns, selectedRunId]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedGoal = goal.trim();
    if (!trimmedGoal) return;

    setIsCreating(true);
    setError(null);
    try {
      const created = await requestJson<{ run_id: string }>("/api/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal: trimmedGoal }),
      });
      setGoal("");
      setSelectedRunId(created.run_id);
      setCurrentRun({
        id: created.run_id,
        goal: trimmedGoal,
        status: "running",
        reason: null,
        total_cost: 0,
        started_at: new Date().toISOString(),
        finished_at: null,
        steps: [],
      });
      const run = await loadRun(created.run_id);
      if (run.status !== "running") void loadRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start the run.");
    } finally {
      setIsCreating(false);
    }
  }

  async function handleSelectRun(runId: string) {
    setError(null);
    try {
      await loadRun(runId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open that run.");
    }
  }

  return (
    <main className="app-shell">
      <PastRuns
        runs={runs}
        selectedRunId={selectedRunId}
        isLoading={isLoadingRuns}
        onSelect={handleSelectRun}
      />

      <section className="workspace" aria-label="Agent run workspace">
        <header className="workspace-header">
          <div>
            <p className="eyebrow">AgentKit</p>
            <h1>Run an agent task</h1>
          </div>
          <StatusBadge run={currentRun} />
        </header>

        <form className="composer" onSubmit={handleSubmit}>
          <label htmlFor="goal">Goal</label>
          <div className="composer-row">
            <input
              id="goal"
              name="goal"
              value={goal}
              onChange={(event) => setGoal(event.target.value)}
              placeholder="Find the Q3 revenue summary"
              disabled={isCreating}
            />
            <button type="submit" disabled={isCreating || goal.trim().length === 0}>
              {isCreating ? <Loader2 className="spin" aria-hidden="true" /> : <Play aria-hidden="true" />}
              <span>{isCreating ? "Starting" : "Run"}</span>
            </button>
          </div>
        </form>

        {error && (
          <div className="error-banner" role="alert">
            <AlertCircle aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}

        {currentRun && (
          <section className="run-summary" aria-label="Current run">
            <div>
              <span className="label">Goal</span>
              <p>{currentRun.goal}</p>
            </div>
            <div>
              <span className="label">Cost</span>
              <p>{formatCurrency(currentRun.total_cost)}</p>
            </div>
            <div>
              <span className="label">Steps</span>
              <p>{currentRun.steps.length}</p>
            </div>
          </section>
        )}

        {finalAnswer && currentRun?.status === "succeeded" && (
          <section className="final-answer" aria-label="Final answer">
            <div className="final-answer-header">
              <CheckCircle2 aria-hidden="true" />
              <span>Final answer</span>
            </div>
            <p>{finalAnswer}</p>
          </section>
        )}

        {currentRun?.status === "terminated" && currentRun.reason && (
          <section className={`terminal-message ${statusTone(currentRun)}`} aria-label="Run result">
            <StatusIcon run={currentRun} />
            <div>
              <strong>{terminalMessages[currentRun.reason]}</strong>
              <p>Reason code: {currentRun.reason}</p>
            </div>
          </section>
        )}

        <section className="timeline-section">
          <div className="section-title">
            <h2>Progress</h2>
            {currentRun && (
              <a href={`/api/runs/${currentRun.id}`} target="_blank" rel="noreferrer">
                <SquareArrowOutUpRight aria-hidden="true" />
                <span>JSON</span>
              </a>
            )}
          </div>
          <Timeline run={currentRun} />
        </section>
      </section>
    </main>
  );
}

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element was not found.");
}

window.__agentkitRoot ??= createRoot(rootElement);
window.__agentkitRoot.render(
  <StrictMode>
    <App />
  </StrictMode>,
);
