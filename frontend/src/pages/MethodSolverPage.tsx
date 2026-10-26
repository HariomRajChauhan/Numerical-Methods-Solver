import {
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { CodePanel } from "../components/CodePanel";
import { CopyButton } from "../components/CopyButton";
import { DataTable } from "../components/DataTable";
import { ErrorAlert } from "../components/ErrorAlert";
import { LatexView } from "../components/LatexView";
import { LoadingSkeleton } from "../components/LoadingSkeleton";
import { MethodForm } from "../components/MethodForm";
import { MethodStatusBadge } from "../components/StatusBadge";
import { PlotPanel } from "../components/PlotPanel";
import { ResultPanel } from "../components/ResultPanel";
import { StepsPanel } from "../components/StepsPanel";
import { Tabs, type TabDef } from "../components/Tabs";
import { Icon } from "../components/ui/Icon";
import { ResizeDivider } from "../components/workspace/ResizeDivider";
import { WorkspaceToolbar } from "../components/workspace/WorkspaceToolbar";
import { useMethodMeta } from "../hooks/useMethodMeta";
import { useSolverStore } from "../store/solver";
import { toast } from "../store/toast";
import type { SolveResponse } from "../types/api";
import { chapterVisual } from "../utils/chapters";
import { downloadText } from "../utils/download";
import { buildShareUrl, readShareState } from "../utils/shareState";
import { ui } from "../utils/ui";
import { NotFoundPage } from "./NotFoundPage";

type TabId = "answer" | "steps" | "table" | "graph" | "theory" | "pseudocode" | "code";

const TAB_IDS = new Set<TabId>([
  "answer",
  "steps",
  "table",
  "graph",
  "theory",
  "pseudocode",
  "code",
]);

function isTabId(value: unknown): value is TabId {
  return typeof value === "string" && TAB_IDS.has(value as TabId);
}

const INPUT_WIDTH_KEY = "nms.workspace.input-width";
const DEFAULT_INPUT_WIDTH = 34;
const MIN_INPUT_WIDTH = 26;
const MAX_INPUT_WIDTH = 56;

function clampInputWidth(value: number): number {
  return Math.min(MAX_INPUT_WIDTH, Math.max(MIN_INPUT_WIDTH, value));
}

/** Method page: auto-generated form (left) + tabbed results and method notes (right). */
export function MethodSolverPage() {
  const { methodId } = useParams();
  const location = useLocation();
  const { meta, loading, error } = useMethodMeta(methodId);
  const [activeTab, setActiveTab] = useState<TabId>(() => {
    const shared = readShareState(location.search);
    return shared && isTabId(shared.tab) ? shared.tab : "answer";
  });
  const [solveVersion, setSolveVersion] = useState(0);
  const [inputWidth, setInputWidth] = useState(() => {
    if (typeof window === "undefined") return DEFAULT_INPUT_WIDTH;
    try {
      const stored = Number(window.localStorage.getItem(INPUT_WIDTH_KEY));
      return Number.isFinite(stored) && stored > 0 ? clampInputWidth(stored) : DEFAULT_INPUT_WIDTH;
    } catch {
      return DEFAULT_INPUT_WIDTH;
    }
  });
  const [inputsCollapsed, setInputsCollapsed] = useState(false);
  const [resizing, setResizing] = useState(false);
  const workspaceRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ startX: number; startWidth: number; paneWidth: number } | null>(null);
  const appliedLocationRef = useRef<string | null>(null);

  const inputs = useSolverStore((state) => state.inputs);
  const status = useSolverStore((state) => state.status);
  const response = useSolverStore((state) => state.response);
  const solveError = useSolverStore((state) => state.error);
  const initialize = useSolverStore((state) => state.initialize);
  const setInput = useSolverStore((state) => state.setInput);
  const loadExample = useSolverStore((state) => state.loadExample);
  const run = useSolverStore((state) => state.run);
  const clearResult = useSolverStore((state) => state.clearResult);

  useEffect(() => {
    if (!meta) return;
    const locationKey = `${meta.id}:${location.search}`;
    if (appliedLocationRef.current === locationKey) return;
    appliedLocationRef.current = locationKey;

    const shared = readShareState(location.search);
    if (shared && shared.method === meta.id) {
      const allowed = new Set(meta.input_schema.map((field) => field.key));
      const restored = Object.fromEntries(
        Object.entries(shared.inputs).filter(([key]) => allowed.has(key)),
      );
      loadExample(restored, meta);
      toast({
        tone: "info",
        title: "Shared setup restored",
        message: "Re-solving the shared inputs now.",
        duration: 3600,
      });
      void run(meta);
      return;
    }

    initialize(meta);
  }, [meta, location.search, initialize, loadExample, run]);

  useEffect(() => {
    try {
      window.localStorage.setItem(INPUT_WIDTH_KEY, String(Math.round(inputWidth)));
    } catch {
      // A blocked storage API must never stop the workspace from working.
    }
  }, [inputWidth]);

  function startResize(event: ReactPointerEvent<HTMLDivElement>): void {
    if (event.button !== 0) return;
    const pane = workspaceRef.current;
    if (!pane) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      startX: event.clientX,
      startWidth: inputWidth,
      paneWidth: pane.clientWidth,
    };
    setResizing(true);
  }

  function moveResize(event: ReactPointerEvent<HTMLDivElement>): void {
    const drag = dragRef.current;
    if (!drag) return;
    const delta = ((event.clientX - drag.startX) / Math.max(drag.paneWidth, 1)) * 100;
    setInputWidth(clampInputWidth(drag.startWidth + delta));
  }

  function endResize(event: ReactPointerEvent<HTMLDivElement>): void {
    if (!dragRef.current) return;
    dragRef.current = null;
    setResizing(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function nudgeWidth(delta: number): void {
    setInputWidth((value) => clampInputWidth(value + delta));
  }

  function resetWidth(): void {
    setInputWidth(DEFAULT_INPUT_WIDTH);
  }

  const tabs = useMemo<TabDef[]>(
    () => [
      { id: "answer", label: "Answer", icon: "sparkles" },
      { id: "steps", label: "Steps", icon: "list", badge: response?.steps.length },
      { id: "table", label: "Table", icon: "table", badge: response?.tables.length },
      { id: "graph", label: "Graph", icon: "chart" },
      { id: "theory", label: "Theory", icon: "book" },
      { id: "pseudocode", label: "Pseudocode", icon: "terminal" },
      { id: "code", label: "Code", icon: "code" },
    ],
    [response],
  );

  const shareUrl = useMemo(
    () => (meta ? buildShareUrl(meta.id, inputs, activeTab) : ""),
    [meta, inputs, activeTab],
  );

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 py-8">
        <LoadingSkeleton lines={2} />
        <LoadingSkeleton lines={6} />
      </div>
    );
  }

  if (error || !meta) {
    return <NotFoundPage message={error?.message ?? "That method does not exist."} />;
  }

  const busy = status === "loading";
  const visual = chapterVisual(meta.chapter);
  const method = meta;

  async function handleSolve(): Promise<void> {
    setActiveTab("answer");
    await run(method);
    setSolveVersion((value) => value + 1);
    const result = useSolverStore.getState();
    if (result.status === "done" && result.response) {
      const steps = result.response.steps.length;
      const tables = result.response.tables.length;
      toast({
        tone: "success",
        title: `${method.name} solved`,
        message: `${steps} step${steps === 1 ? "" : "s"}${
          tables > 0 ? ` · ${tables} table${tables === 1 ? "" : "s"}` : ""
        } ready to explore.`,
        duration: 3800,
      });
    } else if (result.status === "error" && result.error) {
      toast({
        tone: "error",
        title: "Solve failed",
        message: result.error.message,
        duration: 5200,
      });
    }
  }

  return (
    <div className="mx-auto max-w-[1600px]">
      <nav
        aria-label="Breadcrumb"
        className="flex flex-wrap items-center gap-1.5 text-xs text-ink-muted"
      >
        <Link
          to="/"
          className="inline-flex items-center gap-1 rounded-control px-1 py-0.5 transition duration-150 hover:text-accent-text"
        >
          <Icon name="home" size={13} />
          Home
        </Link>
        <Icon name="chevronRight" size={12} className="text-ink-subtle" />
        <Link
          to={`/chapters/${meta.chapter}`}
          className="rounded-control px-1 py-0.5 transition duration-150 hover:text-accent-text"
        >
          {meta.chapter_title}
        </Link>
        <Icon name="chevronRight" size={12} className="text-ink-subtle" />
        <span className="truncate font-medium text-ink">{meta.name}</span>
      </nav>

      <header className="mb-5 mt-3 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Link
              to={`/chapters/${meta.chapter}`}
              className={`inline-flex items-center gap-1.5 rounded-pill border px-2.5 py-1 text-2xs font-semibold tabular-nums transition duration-150 hover:opacity-80 ${visual.border} ${visual.tint}`}
            >
              <Icon name={visual.icon} size={12} />
              Chapter {meta.chapter_number} · {meta.chapter_title}
            </Link>
            <MethodStatusBadge status={meta.status} />
          </div>
          <h1 className="mt-3 text-2xl font-bold tracking-tight text-ink sm:text-display">
            {meta.name}
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-ink-muted">{meta.summary}</p>
        </div>
        <button
          type="button"
          onClick={() => setActiveTab("theory")}
          className={`${ui.btn} hidden shrink-0 sm:inline-flex`}
        >
          <Icon name="book" size={15} />
          Read theory
        </button>
      </header>

      <WorkspaceToolbar
        formId="method-form"
        busy={busy}
        canSolve={meta.status === "available"}
        methodId={meta.id}
        methodName={meta.name}
        shareUrl={shareUrl}
        inputs={inputs}
        examples={meta.examples}
        hasResult={Boolean(response)}
        inputsCollapsed={inputsCollapsed}
        onToggleInputs={() => setInputsCollapsed((value) => !value)}
        onLoadExample={(exampleInputs) => {
          setInputsCollapsed(false);
          loadExample(exampleInputs, meta);
        }}
      />

      <div
        ref={workspaceRef}
        className="flex flex-col gap-6 lg:flex-row lg:items-start lg:gap-0"
      >
        {!inputsCollapsed && (
          <aside
            id="workspace-inputs"
            aria-label="Inputs"
            style={{ "--workspace-input-width": `${inputWidth}%` } as CSSProperties}
            className="min-w-0 space-y-3 lg:sticky lg:top-[7.75rem] lg:max-h-[calc(100dvh-9rem)] lg:w-[var(--workspace-input-width)] lg:shrink-0 lg:self-start lg:overflow-y-auto lg:pr-1 lg:scroll-slim"
          >
            <div className="space-y-3">
              <section className={`overflow-hidden ${ui.card}`}>
                <div className="flex items-center gap-2.5 border-b border-line px-5 py-4">
                  <span className={`${ui.iconBox} h-8 w-8`}>
                    <Icon name="play" size={15} />
                  </span>
                  <div>
                    <h2 className="text-sm font-semibold text-ink">Problem setup</h2>
                    <p className="text-2xs text-ink-muted">Enter the inputs, then press Solve.</p>
                  </div>
                </div>

                <div className="p-5">
                  {meta.status === "coming_soon" ? (
                    <div className="space-y-4">
                      <span className="flex h-11 w-11 items-center justify-center rounded-panel bg-warning-soft text-warning ring-1 ring-inset ring-warning/20">
                        <Icon name="clock" size={20} />
                      </span>
                      <div>
                        <h3 className="text-sm font-semibold text-ink">Coming soon</h3>
                        <p className="mt-1.5 text-xs leading-relaxed text-ink-muted">
                          This method is part of the syllabus and will be added in an upcoming
                          chapter release. Its theory, formulas and pseudocode are already
                          available in the tabs.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setActiveTab("theory")}
                        className={ui.btn}
                      >
                        <Icon name="book" size={15} />
                        Read the theory
                        <Icon name="arrowRight" size={14} />
                      </button>
                    </div>
                  ) : (
                    <MethodForm
                      meta={meta}
                      inputs={inputs}
                      status={status}
                      error={solveError}
                      formId="method-form"
                      showSubmit={false}
                      onChange={setInput}
                      onSubmit={() => void handleSolve()}
                      onClear={clearResult}
                      onLoadExample={(exampleInputs) => loadExample(exampleInputs, meta)}
                    />
                  )}
                </div>
              </section>

              {meta.status === "available" && (
                <div className="hidden items-start gap-2.5 rounded-panel border border-line bg-surface-muted p-3.5 text-2xs leading-relaxed text-ink-muted lg:flex">
                  <Icon name="info" size={14} className="mt-0.5 shrink-0 text-accent-text" />
                  <p>
                    Use the on-screen keypad for powers, roots and functions. Press{" "}
                    <kbd className="rounded border border-line bg-surface px-1 font-mono text-[10px] text-ink-muted">
                      Ctrl/⌘ + ↵
                    </kbd>{" "}
                    to solve from anywhere in the form.
                  </p>
                </div>
              )}
            </div>
          </aside>
        )}

        {!inputsCollapsed && (
          <ResizeDivider
            value={inputWidth}
            min={MIN_INPUT_WIDTH}
            max={MAX_INPUT_WIDTH}
            resizing={resizing}
            onPointerDown={startResize}
            onPointerMove={moveResize}
            onPointerUp={endResize}
            onPointerCancel={endResize}
            onNudge={nudgeWidth}
            onReset={resetWidth}
          />
        )}

        <section aria-label="Results" className="min-w-0 flex-1">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-control bg-surface-muted text-ink-muted ring-1 ring-inset ring-line">
                <Icon name="sparkles" size={15} />
              </span>
              <div>
                <h2 className="text-sm font-semibold text-ink">Solution workspace</h2>
                <p className="text-2xs text-ink-muted">
                  Answer, working, tables, graph and method notes.
                </p>
              </div>
            </div>
            {response && (
              <span className="inline-flex items-center gap-1.5 rounded-pill border border-success/20 bg-success-soft px-2.5 py-1 text-2xs font-medium text-success">
                <Icon name="check" size={12} />
                Solved
              </span>
            )}
          </div>

          <Tabs
            tabs={tabs}
            activeId={activeTab}
            onChange={(id) => setActiveTab(id as TabId)}
            className="mb-4"
          />

          <div
            role="tabpanel"
            id={`panel-${activeTab}`}
            aria-labelledby={`tab-${activeTab}`}
            tabIndex={0}
            className="min-h-[18rem] rounded-panel focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-2 focus-visible:ring-offset-canvas"
          >
            {activeTab === "theory" && (
              <div className="animate-fade-in space-y-4">
                <section className={`p-5 ${ui.card}`}>
                  <div className="flex items-center gap-2">
                    <span className={`${ui.iconBox} h-7 w-7`}>
                      <Icon name="book" size={14} />
                    </span>
                    <h2 className="text-sm font-semibold text-ink">How {meta.name} works</h2>
                  </div>
                  <p className="mt-3 whitespace-pre-line text-sm leading-7 text-ink-muted">
                    {meta.theory || "Theory notes for this method are not written yet."}
                  </p>
                </section>

                {meta.formulas.length > 0 && (
                  <div className="grid gap-3 sm:grid-cols-2">
                    {meta.formulas.map((formula) => (
                      <div key={formula.label} className={`p-4 ${ui.card}`}>
                        <p className="text-2xs font-semibold uppercase tracking-[0.14em] text-ink-muted">
                          {formula.label}
                        </p>
                        <div
                          role="region"
                          aria-label={`${formula.label} formula`}
                          tabIndex={0}
                          className="mt-2 overflow-x-auto focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent-500"
                        >
                          <LatexView latex={formula.latex} display />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "pseudocode" && (
              <div className="animate-fade-in">
                <CodePanel
                  title="Pseudocode"
                  icon="terminal"
                  language="Algorithm"
                  code={meta.pseudocode}
                  emptyMessage="Pseudocode for this method is not written yet."
                  actions={<CopyButton text={meta.pseudocode} label="Copy pseudocode" />}
                />
              </div>
            )}

            {activeTab === "code" && (
              <div className="animate-fade-in">
                <CodePanel
                  title="Python source"
                  icon="code"
                  language="Python"
                  code={response?.python_source ?? ""}
                  emptyMessage="Run the solver to see its Python source."
                  actions={
                    <>
                      <CopyButton text={response?.python_source ?? ""} label="Copy source" />
                      <button
                        type="button"
                        disabled={!response?.python_source}
                        onClick={() =>
                          downloadText(
                            `nms_${meta.id}.py`,
                            response?.python_source ?? "",
                            "text/x-python",
                          )
                        }
                        className={`${ui.btnGhost} disabled:opacity-40`}
                      >
                        <Icon name="download" size={13} />
                        Download .py
                      </button>
                    </>
                  }
                />
              </div>
            )}

            {(activeTab === "answer" ||
              activeTab === "steps" ||
              activeTab === "table" ||
              activeTab === "graph") && (
              <SolveView
                tab={activeTab}
                busy={busy}
                error={solveError}
                response={response}
                methodName={meta.name}
                solveVersion={solveVersion}
                onClear={clearResult}
              />
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

interface SolveViewProps {
  tab: "answer" | "steps" | "table" | "graph";
  busy: boolean;
  error?: ApiError;
  response?: SolveResponse;
  methodName: string;
  solveVersion: number;
  onClear: () => void;
}

/** Right-hand panel content for the four result tabs (loading / error / empty / data). */
function SolveView({
  tab,
  busy,
  error,
  response,
  methodName,
  solveVersion,
  onClear,
}: SolveViewProps) {
  if (busy) {
    return (
      <div className={`p-5 ${ui.card}`}>
        <LoadingSkeleton lines={5} />
      </div>
    );
  }
  if (error) {
    return <ErrorAlert error={error} onDismiss={onClear} />;
  }
  if (!response) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-panel border border-dashed border-line-strong bg-surface-muted px-6 py-14 text-center">
        <span className={`${ui.iconBox} h-12 w-12 rounded-panel`}>
          <Icon name="sparkles" size={22} />
        </span>
        <div>
          <p className="text-sm font-semibold text-ink">Ready when you are</p>
          <p className="mt-1 max-w-sm text-xs leading-relaxed text-ink-muted">
            Set up your problem on the left and press{" "}
            <span className="font-semibold text-ink">Solve</span> to see the {tab}.
          </p>
        </div>
      </div>
    );
  }

  switch (tab) {
    case "answer":
      return <ResultPanel response={response} />;
    case "steps":
      return <StepsPanel key={solveVersion} steps={response.steps} />;
    case "table":
      return response.tables.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-2 rounded-panel border border-dashed border-line-strong bg-surface-muted px-6 py-12 text-center">
          <span className="flex h-10 w-10 items-center justify-center rounded-control bg-surface text-ink-subtle shadow-sm">
            <Icon name="table" size={19} />
          </span>
          <p className="text-sm text-ink-muted">
            This method did not produce an iteration table.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {response.tables.map((table) => (
            <DataTable key={table.title} table={table} />
          ))}
        </div>
      );
    case "graph":
      return <PlotPanel plot={response.plot} title={`${methodName} — graph`} />;
    default:
      return null;
  }
}
