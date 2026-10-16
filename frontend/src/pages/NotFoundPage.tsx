import { Link } from "react-router-dom";

import { ui } from "../utils/ui";

interface NotFoundPageProps {
  message?: string;
}

export function NotFoundPage({ message = "We could not find that page." }: NotFoundPageProps) {
  return (
    <div className="mx-auto max-w-lg py-16 text-center">
      <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50">404</h1>
      <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">{message}</p>
      <Link to="/" className={`mt-6 ${ui.btnPrimary}`}>
        Back to home
      </Link>
    </div>
  );
}
