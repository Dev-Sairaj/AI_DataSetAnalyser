import type { ButtonHTMLAttributes, ReactNode } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import type { ColumnKind, Severity } from "../../types/api";

export type Tone = "slate" | "indigo" | "green" | "amber" | "red" | "blue";

const BADGE: Record<Tone, string> = {
  slate: "bg-slate-100 text-slate-700",
  indigo: "bg-indigo-100 text-indigo-700",
  green: "bg-emerald-100 text-emerald-700",
  amber: "bg-amber-100 text-amber-800",
  red: "bg-red-100 text-red-700",
  blue: "bg-sky-100 text-sky-700",
};

const ALERT: Record<Tone, string> = {
  slate: "border-slate-200 bg-slate-50 text-slate-700",
  indigo: "border-indigo-200 bg-indigo-50 text-indigo-800",
  green: "border-emerald-200 bg-emerald-50 text-emerald-800",
  amber: "border-amber-200 bg-amber-50 text-amber-900",
  red: "border-red-200 bg-red-50 text-red-800",
  blue: "border-sky-200 bg-sky-50 text-sky-800",
};

export function gradeTone(grade: string): Tone {
  if (grade === "A" || grade === "B") return "green";
  if (grade === "C" || grade === "D") return "amber";
  return "red";
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      {children}
    </div>
  );
}

export function Section({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-lg font-semibold">{title}</h2>
        {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
      </div>
      {children}
    </section>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <Card>
      <div className="text-sm text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-slate-400">{hint}</div>}
    </Card>
  );
}

export function Badge({ tone = "slate", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ${BADGE[tone]}`}
    >
      {children}
    </span>
  );
}

const SEVERITY_TONE: Record<Severity, Tone> = { critical: "red", warning: "amber", info: "blue" };
export function SeverityBadge({ severity }: { severity: Severity }) {
  return <Badge tone={SEVERITY_TONE[severity]}>{severity}</Badge>;
}

const KIND_TONE: Record<ColumnKind, Tone> = {
  numeric: "indigo",
  categorical: "blue",
  boolean: "green",
  datetime: "amber",
  text: "slate",
  empty: "red",
};
export function KindBadge({ kind }: { kind: ColumnKind }) {
  return <Badge tone={KIND_TONE[kind]}>{kind}</Badge>;
}

export function Alert({ tone = "amber", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <div className={`flex items-start gap-2 rounded-lg border px-4 py-3 text-sm ${ALERT[tone]}`}>
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      <div>{children}</div>
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-slate-500">
      <Loader2 className="h-5 w-5 animate-spin" />
      {label && <span>{label}</span>}
    </div>
  );
}

export function ProgressBar({ value }: { value: number }) {
  return (
    <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200">
      <div
        className="h-full rounded-full bg-indigo-600 transition-all duration-500"
        style={{ width: `${Math.round(value * 100)}%` }}
      />
    </div>
  );
}

export function buttonClasses(variant: "primary" | "secondary" = "primary"): string {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50";
  return variant === "primary"
    ? `${base} bg-indigo-600 text-white hover:bg-indigo-700`
    : `${base} border border-slate-300 bg-white text-slate-700 hover:bg-slate-50`;
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary";
};
export function Button({ variant = "primary", className = "", ...props }: ButtonProps) {
  return <button type="button" {...props} className={`${buttonClasses(variant)} ${className}`} />;
}

export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">{children}</table>
    </div>
  );
}
export function Th({ children }: { children?: ReactNode }) {
  return (
    <th className="whitespace-nowrap border-b border-slate-200 bg-slate-50 px-3 py-2 font-medium text-slate-600">
      {children}
    </th>
  );
}
export function Td({ children, className = "" }: { children?: ReactNode; className?: string }) {
  return <td className={`border-b border-slate-100 px-3 py-2 align-top ${className}`}>{children}</td>;
}