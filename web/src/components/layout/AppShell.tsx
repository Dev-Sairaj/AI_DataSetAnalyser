import { Link, Outlet } from "react-router-dom";
import { Database } from "lucide-react";

export default function AppShell() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <Link to="/" className="flex items-center gap-2 font-semibold">
            <Database className="h-5 w-5 text-indigo-600" />
            ADIP
            <span className="hidden text-sm font-normal text-slate-500 sm:inline">
              AI Dataset Intelligence Platform
            </span>
          </Link>
          <Link to="/" className="text-sm text-indigo-600 hover:underline">
            New analysis
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}