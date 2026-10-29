import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/layout/AppLayout";
import { LoadingSkeleton } from "./components/LoadingSkeleton";

// Route-level code splitting keeps the first paint small; the layout itself is
// eager so the shell appears immediately while the page chunk arrives.
const HomePage = lazy(() => import("./pages/HomePage").then((module) => ({ default: module.HomePage })));
const ChapterPage = lazy(() =>
  import("./pages/ChapterPage").then((module) => ({ default: module.ChapterPage })),
);
const MethodSolverPage = lazy(() =>
  import("./pages/MethodSolverPage").then((module) => ({ default: module.MethodSolverPage })),
);
const AboutPage = lazy(() =>
  import("./pages/AboutPage").then((module) => ({ default: module.AboutPage })),
);
const NotFoundPage = lazy(() =>
  import("./pages/NotFoundPage").then((module) => ({ default: module.NotFoundPage })),
);

function RouteFallback() {
  return (
    <div className="mx-auto min-h-dvh max-w-6xl space-y-5 py-2">
      <LoadingSkeleton lines={2} />
      <LoadingSkeleton lines={6} />
    </div>
  );
}

export default function App() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/chapters/:chapterId" element={<ChapterPage />} />
          <Route path="/methods/:methodId" element={<MethodSolverPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/home" element={<Navigate to="/" replace />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
