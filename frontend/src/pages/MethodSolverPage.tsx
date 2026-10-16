import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { ErrorAlert } from "../components/ErrorAlert";
import { DataTable } from "../components/DataTable";
import { LatexView } from "../components/LatexView";
import { LoadingSkeleton } from "../components/LoadingSkeleton";
import { MethodForm } from "../components/MethodForm";
import { PlotPanel } from "../components/PlotPanel";
import { ResultPanel } from "../components/ResultPanel";
import { StepsPanel } from "../components/StepsPanel";
import { Tabs, type TabDef } from "../components/Tabs";
import { useMethodMeta } from "../hooks/useMethodMeta";
import { useSolverStore } from "../store/solver";
import type { SolveResponse } from "../types/api";
import { downloadText } from "../utils/download";
import { ui } from "../utils/ui";
import { CopyButton } from "../components/CopyButton";
import { NotFoundPage } from "./NotFoundPage";

type TabId = "answer" | "steps" | "table" | "graph" | "theory" | "pseudocode" | "code";

/** Method page: auto-generated form (left) + tabbed results (right). */
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
      { id: "answer", label: "Answer" },
      { id: "steps", label: "Steps", badge: response?.steps.length },
      { id: "table", label: "Table", badge: response?.tables.length },
      { id: "graph", label: "Graph" },
      { id: "theory", label: "Theory" },
      { id: "pseudocode", label: "Pseudocode" },
      { id: "code", label: "Code" },
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

  return (
    <div className="mx-auto max-w-[1500px]">
      <nav aria-label="Breadcrumb" className="text-xs text-slate-500">
        <Link to="/" className="hover:text-indigo-600 dark:hover:text-indigo-400">
          Home
        </Link>
        <span aria-hidden="true"> / </span>
        <Link
          to={`/chapters/${meta.chapter}`}
          className="hover:text-indigo-600 dark:hover:text-indigo-400"
        >
          {meta.chapter_title}
        </Link>
        <span aria-hidden="true"> / </span>
        <span>{meta.name}</span>
      </nav>

      <header className="mt-2 mb-5">
        <h1 className="text-xl font-bold text-slate-900 dark:text-slate-50">{meta.name}</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{meta.summary}</p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(320px,420px)_1fr]">
        <section className={`h-fit p-5 ${ui.card}`} aria-label="Inputs">
          {meta.status === "coming_soon" ? (
            <div className="space-y-2 text-sm text-slate-600 dark:text-slate-400">
              <p className="font-semibold text-slate-800 dark:text-slate-200">Coming soon</p>
              <p>
                This method is part of the syllabus and will be added in an upcoming chapter
                release. Its theory and pseudocode are already available in the tabs.
              </p>
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
        </section>

        <section aria-label="Results" className="min-w-0">
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
            className="min-h-[16rem]"
          >
            {activeTab === "theory" && (
              <div className="space-y-4 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                <p className="whitespace-pre-line">
                  {meta.theory || "Theory notes for this method are not written yet."}
                </p>
                {meta.formulas.length > 0 && (
                  <div className={`space-y-3 p-4 ${ui.card}`}>
                    {meta.formulas.map((formula) => (
                      <div key={formula.label}>
                        <p className="text-xs uppercase tracking-wide text-slate-500">
                          {formula.label}
                        </p>
                        <div className="mt-1 overflow-x-auto">
                          <LatexView latex={formula.latex} display />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === "pseudocode" && (
              <div className={`p-4 ${ui.card}`}>
                <div className="mb-2 flex justify-end">
                  <CopyButton text={meta.pseudocode} label="Copy pseudocode" />
                </div>
                <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-xs leading-relaxed text-slate-700 dark:text-slate-300">
                  {meta.pseudocode || "Pseudocode for this method is not written yet."}
                </pre>
              </div>
            )}

            {activeTab === "code" && (
              <div className={`p-4 ${ui.card}`}>
                <div className="mb-2 flex justify-end gap-1">
                  <CopyButton text={response?.python_source ?? ""} label="Copy source" />
                  <button
                    type="button"
                    disabled={!response?.python_source}
                    onClick={() =>
                      downloadText(`nms_${meta.id}.py`, response?.python_source ?? "", "text/x-python")
                    }
                    className={`${ui.btnGhost} disabled:opacity-40`}
                  >
                    ⤓ Download .py
                  </button>
                </div>
                <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-xs leading-relaxed text-slate-700 dark:text-slate-300">
                  {response?.python_source || "Run the solver to see its Python source."}
                </pre>
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
      <div className={`flex h-40 items-center justify-center p-5 text-center ${ui.card}`}>
        <p className="text-sm text-slate-500">
          Enter your problem on the left and press <span className="font-medium">Solve</span> to see
          the {tab}.
        </p>
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
        <p className="text-sm text-slate-500">This method did not produce a table.</p>
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
