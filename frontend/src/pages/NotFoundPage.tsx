import { Link } from "react-router-dom";

import { Icon } from "../components/ui/Icon";
import { usePageTitle } from "../hooks/usePageTitle";
import { ui } from "../utils/ui";

interface NotFoundPageProps {
  message?: string;
}

export function NotFoundPage({ message = "We could not find that page." }: NotFoundPageProps) {
  usePageTitle("Page not found");
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center py-14 text-center sm:py-20">
      <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-500 ring-1 ring-inset ring-indigo-100 dark:bg-indigo-500/10 dark:text-indigo-300 dark:ring-indigo-400/20">
        <Icon name="search" size={25} />
      </span>
      <p className="mt-6 bg-gradient-to-r from-indigo-600 via-violet-600 to-teal-500 bg-clip-text text-6xl font-extrabold tracking-tight text-transparent dark:from-indigo-400 dark:via-violet-400 dark:to-teal-300">
        404
      </p>
      <h1 className="mt-3 text-xl font-bold text-slate-900 dark:text-white">
        This page isn&apos;t in the syllabus
      </h1>
      <p className="mt-2 max-w-sm text-sm leading-relaxed text-slate-500 dark:text-slate-400">
        {message}
      </p>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-2.5">
        <Link to="/" className={ui.btnPrimary}>
          <Icon name="home" size={15} />
          Back to home
        </Link>
        <Link to="/about" className={ui.btn}>
          <Icon name="info" size={14} />
          About the project
        </Link>
      </div>
    </div>
  );
}
