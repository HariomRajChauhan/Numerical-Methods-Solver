import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { CodePanel } from "../components/CodePanel";
import { CopyButton } from "../components/CopyButton";
import { DataTable } from "../components/DataTable";
import { ErrorAlert } from "../components/ErrorAlert";
import { ExportButtons } from "../components/ExportButtons";
import { LatexView } from "../components/LatexView";
import { LoadingSkeleton } from "../components/LoadingSkeleton";
import { MethodForm } from "../components/MethodForm";
import { MethodStatusBadge } from "../components/StatusBadge";
import { PlotPanel } from "../components/PlotPanel";
import { ResultPanel } from "../components/ResultPanel";
import { StepsPanel } from "../components/StepsPanel";
import { Tabs, type TabDef } from "../components/Tabs";
import { Icon } from "../components/ui/Icon";
import { useMethodMeta } from "../hooks/useMethodMeta";
import { useSolverStore } from "../store/solver";
import type { SolveResponse } from "../types/api";
import { chapterVisual } from "../utils/chapters";
import { downloadText } from "../utils/download";
import { ui } from "../utils/ui";
import { NotFoundPage } from "./NotFoundPage";

type TabId = "answer" | "steps" | "table" | "graph" | "theory" | "pseudocode" | "code";

/** Method page: auto-generated form (left) + tabbed results and method notes (right). */
export function MethodSolverPage() {
  const { methodId } = useParams();
  const { meta, loading, error } = useMethodMeta(methodId);
  const [activeTab, setActiveTab] = useState<TabId>("answer");

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
    if (meta) initialize(meta);
  }, [meta, initialize]);

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

  return (
    <div className="mx-auto max-w-[1500px]">
      <nav
        aria-label="Breadcrumb"
        className="flex flex-wrap items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400"
      >
        <Link
          to="/"
          className="inline-flex items-center gap-1 rounded-md px-1 py-0.5 transition hover:text-indigo-600 dark:hover:text-indigo-300"
        >
          <Icon name="home" size={13} />
          Home
        </Link>
        <Icon name="chevronRight" size={12} className="text-slate-300 dark:text-slate-600" />
        <Link
          to={`/chapters/${meta.chapter}`}
          className="rounded-md px-1 py-0.5 transition hover:text-indigo-600 dark:hover:text-indigo-300"
        >
          {meta.chapter_title}
        </Link>
        <Icon name="chevronRight" size={12} className="text-slate-300 dark:text-slate-600" />
        <span className="truncate font-medium text-slate-700 dark:text-slate-200">
          {meta.name}
        </span>
      </nav>

      <header className="mb-6 mt-3 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Link
              to={`/chapters/${meta.chapter}`}
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold transition hover:opacity-80 ${visual.border} ${visual.tint}`}
            >
              <Icon name={visual.icon} size={12} />
              Chapter {meta.chapter_number} · {meta.chapter_title}
            </Link>
            <MethodStatusBadge status={meta.status} />
          </div>
          <h1 className="mt-3 text-2xl font-bold tracking-tight text-slate-900 sm:text-[2rem] dark:text-white">
            {meta.name}
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-600 dark:text-slate-400">
            {meta.summary}
          </p>
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

      <div className="grid gap-6 lg:grid-cols-[minmax(330px,420px)_minmax(0,1fr)]">
        <aside aria-label="Inputs" className="min-w-0">
          <div className="space-y-3 lg:sticky lg:top-20 lg:max-h-[calc(100dvh-6rem)] lg:overflow-y-auto lg:pr-1 lg:scroll-slim">
            <section className={`overflow-hidden ${ui.card}`}>
              <div className="flex items-center gap-2.5 border-b border-slate-200/80 px-5 py-4 dark:border-white/[0.07]">
                <span className={`${ui.iconBox} h-8 w-8`}>
                  <Icon name="play" size={15} />
                </span>
                <div>
                  <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
                    Problem setup
                  </h2>
                  <p className="text-[11px] text-slate-600 dark:text-slate-400">
                    Enter the inputs, then press Solve.
                  </p>
                </div>
              </div>

              <div className="p-5">
                {meta.status === "coming_soon" ? (
                  <div className="space-y-4">
                    <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-amber-50 text-amber-600 ring-1 ring-inset ring-amber-200/70 dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-400/20">
                      <Icon name="clock" size={20} />
                    </span>
                    <div>
                      <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                        Coming soon
                      </h3>
                      <p className="mt-1.5 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                        This method is part of the syllabus and will be added in an upcoming
                        chapter release. Its theory, formulas and pseudocode are already available
                        in the tabs.
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
                    onChange={setInput}
                    onSubmit={() => {
                      setActiveTab("answer");
                      void run(meta);
                    }}
                    onClear={clearResult}
                    onLoadExample={(exampleInputs) => loadExample(exampleInputs, meta)}
                  />
                )}
              </div>
            </section>

            {meta.status === "available" && (
              <div className="hidden items-start gap-2.5 rounded-2xl border border-slate-200/70 bg-white/50 p-3.5 text-[11px] leading-relaxed text-slate-600 lg:flex dark:border-white/[0.06] dark:bg-white/[0.02] dark:text-slate-400">
                <Icon name="info" size={14} className="mt-0.5 shrink-0 text-indigo-500" />
                <p>
                  Use the on-screen keypad for powers, roots and functions. Press{" "}
                  <kbd className="rounded border border-slate-300 bg-white px-1 font-mono text-[10px] text-slate-600 dark:border-white/10 dark:bg-white/[0.06] dark:text-slate-300">
                    Ctrl/⌘ + ↵
                  </kbd>{" "}
                  to solve from anywhere in the form.
                </p>
              </div>
            )}
          </div>
        </aside>

        <section aria-label="Results" className="min-w-0">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-slate-500 dark:bg-white/[0.06] dark:text-slate-400">
                <Icon name="sparkles" size={15} />
              </span>
              <div>
                <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
                  Solution workspace
                </h2>
                <p className="text-[11px] text-slate-600 dark:text-slate-400">
                  Answer, working, tables, graph and method notes.
                </p>
              </div>
            </div>
            {response && <ExportButtons methodId={meta.id} inputs={inputs} />}
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
            className="min-h-[18rem] rounded-2xl focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-50 dark:focus-visible:ring-offset-[#070a13]"
          >
            {activeTab === "theory" && (
              <div className="animate-fade-in space-y-4">
                <section className={`p-5 ${ui.card}`}>
                  <div className="flex items-center gap-2">
                    <span className={`${ui.iconBox} h-7 w-7`}>
                      <Icon name="book" size={14} />
                    </span>
                    <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                      How {meta.name} works
                    </h2>
                  </div>
                  <p className="mt-3 whitespace-pre-line text-sm leading-7 text-slate-600 dark:text-slate-300">
                    {meta.theory || "Theory notes for this method are not written yet."}
                  </p>
                </section>

                {meta.formulas.length > 0 && (
                  <div className="grid gap-3 sm:grid-cols-2">
                    {meta.formulas.map((formula) => (
                      <div key={formula.label} className={`p-4 ${ui.card}`}>
                        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600 dark:text-slate-400">
                          {formula.label}
                        </p>
                        <div
                          role="region"
                          aria-label={`${formula.label} formula`}
                          tabIndex={0}
                          className="mt-2 overflow-x-auto focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-indigo-500"
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
  onClear: () => void;
}

/** Right-hand panel content for the four result tabs (loading / error / empty / data). */
function SolveView({ tab, busy, error, response, methodName, onClear }: SolveViewProps) {
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
      <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-slate-300 bg-white/50 px-6 py-14 text-center dark:border-white/10 dark:bg-white/[0.02]">
        <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 ring-1 ring-inset ring-indigo-100 dark:bg-indigo-500/10 dark:text-indigo-300 dark:ring-indigo-400/20">
          <Icon name="sparkles" size={22} />
        </span>
        <div>
          <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
            Ready when you are
          </p>
          <p className="mt-1 max-w-sm text-xs leading-relaxed text-slate-500 dark:text-slate-400">
            Set up your problem on the left and press{" "}
            <span className="font-semibold text-slate-700 dark:text-slate-200">Solve</span> to
            see the {tab}.
          </p>
        </div>
      </div>
    );
  }

  switch (tab) {
    case "answer":
      return <ResultPanel response={response} />;
    case "steps":
      return <StepsPanel steps={response.steps} />;
    case "table":
      return response.tables.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-slate-300 bg-white/50 px-6 py-12 text-center dark:border-white/10 dark:bg-white/[0.02]">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-400 dark:bg-white/[0.06] dark:text-slate-500">
            <Icon name="table" size={19} />
          </span>
          <p className="text-sm text-slate-500 dark:text-slate-400">
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
