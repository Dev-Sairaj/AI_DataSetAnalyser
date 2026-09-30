export function fmtInt(n: number): string {
  return n.toLocaleString("en-US");
}

export function fmtNum(n: number | null | undefined): string {
  if (n === null || n === undefined) return "–";
  if (Number.isInteger(n)) return n.toLocaleString("en-US");
  if (Math.abs(n) >= 1000) return Math.round(n).toLocaleString("en-US");
  return Number(n.toPrecision(4)).toString();
}

const compact = new Intl.NumberFormat("en", { notation: "compact", maximumSignificantDigits: 3 });
export function fmtCompact(n: number): string {
  return compact.format(n);
}

export function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  const units = ["KB", "MB", "GB"];
  let value = n / 1024;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i++;
  }
  return `${value.toFixed(1)} ${units[i]}`;
}

export function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}