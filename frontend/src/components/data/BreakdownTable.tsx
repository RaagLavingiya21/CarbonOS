import { ConfidenceBadge } from "@/components/data/ConfidenceBadge";
import { SourceCitation } from "@/components/data/SourceCitation";
import { cn } from "@/lib/utils";

export interface BreakdownRow {
  rowIndex: number;
  component: string | null;
  material: string | null;
  spendUsd: number | null;
  sector: string | null;
  efSource: string | null;
  confidence: number | null;
  kgCo2e: number | null;
  sharePct: number | null;
}

function fmtMoney(value: number | null): string {
  if (value == null) return "—";
  return value.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

function fmtKg(value: number | null): string {
  if (value == null) return "—";
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

/**
 * Auditable line-item breakdown: right-aligned tabular figures, inline confidence
 * and source citation per row, sticky header. Every number is traceable.
 */
export function BreakdownTable({ rows }: { rows: BreakdownRow[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full border-collapse text-small">
        <thead>
          <tr className="border-b bg-muted/40 text-left text-caption uppercase tracking-wide text-muted-foreground">
            <th className="px-3 py-2 font-medium">Component / material</th>
            <th className="px-3 py-2 text-right font-medium">Spend</th>
            <th className="px-3 py-2 font-medium">Matched sector</th>
            <th className="px-3 py-2 font-medium">Confidence</th>
            <th className="px-3 py-2 text-right font-medium">kg CO₂e</th>
            <th className="px-3 py-2 text-right font-medium">Share</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.rowIndex} className="border-b last:border-0 align-top">
              <td className="px-3 py-2.5">
                <div className="font-medium">{row.component ?? "—"}</div>
                <div className="text-caption text-muted-foreground">{row.material ?? "—"}</div>
              </td>
              <td className="px-3 py-2.5 text-right tabular-nums">{fmtMoney(row.spendUsd)}</td>
              <td className="px-3 py-2.5">
                <div className="max-w-[16rem] truncate">{row.sector ?? "unmatched"}</div>
                {row.efSource ? <SourceCitation source={row.efSource} className="mt-0.5" /> : null}
              </td>
              <td className="px-3 py-2.5">
                <ConfidenceBadge score={row.confidence} />
              </td>
              <td className={cn("px-3 py-2.5 text-right tabular-nums", row.kgCo2e == null && "text-muted-foreground")}>
                {fmtKg(row.kgCo2e)}
              </td>
              <td className="px-3 py-2.5 text-right tabular-nums text-muted-foreground">
                {row.sharePct == null ? "—" : `${row.sharePct.toFixed(1)}%`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
