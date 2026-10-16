import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/layout/AppLayout";
import { AboutPage } from "./pages/AboutPage";
import { ChapterPage } from "./pages/ChapterPage";
import { HomePage } from "./pages/HomePage";
import { MethodSolverPage } from "./pages/MethodSolverPage";
import { NotFoundPage } from "./pages/NotFoundPage";

export default function App() {
  return (
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
  );
}
