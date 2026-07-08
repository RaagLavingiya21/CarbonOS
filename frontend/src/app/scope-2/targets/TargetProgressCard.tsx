"use client";

import { CheckCircle2, TrendingDown, TrendingUp, AlertCircle } from "lucide-react";
import { Target } from "@/lib/scope2-api";

interface TargetProgressCardProps {
  target: Target;
}

export function TargetProgressCard({ target }: TargetProgressCardProps) {
  const baseYear = target.base_year;
  const targetYear = target.target_year;
  const baseTco2e = target.base_year_tco2e;

  // Calculate target emissions
  const targetTco2e = target.target_amount_tco2e ?? baseTco2e * (1 - (target.target_pct_reduction ?? 0) / 100);
  const reduction = ((baseTco2e - targetTco2e) / baseTco2e) * 100;
  const yearsToTarget = targetYear - baseYear;

  // Status badge
  const statusColors: Record<string, string> = {
    draft: "bg-gray-100 text-gray-700",
    active: "bg-blue-100 text-blue-700",
    superseded: "bg-yellow-100 text-yellow-700",
    achieved: "bg-green-100 text-green-700",
  };

  const statusIcon: Record<string, React.ReactNode> = {
    draft: <AlertCircle className="h-4 w-4" />,
    active: <TrendingDown className="h-4 w-4" />,
    superseded: <TrendingUp className="h-4 w-4" />,
    achieved: <CheckCircle2 className="h-4 w-4" />,
  };

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-semibold">
              {baseYear} → {targetYear}
            </h3>
            <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium ${statusColors[target.status]}`}>
              {statusIcon[target.status]}
              {target.status.charAt(0).toUpperCase() + target.status.slice(1)}
            </span>
          </div>
          <p className="text-sm text-gray-600">{yearsToTarget} year target</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-lg bg-gray-50 p-3">
          <p className="text-xs text-gray-600">Base Year ({baseYear})</p>
          <p className="text-lg font-semibold">{baseTco2e.toLocaleString("en-US", { maximumFractionDigits: 0 })} tCO₂e</p>
        </div>
        <div className="rounded-lg bg-blue-50 p-3">
          <p className="text-xs text-gray-600">Target ({targetYear})</p>
          <p className="text-lg font-semibold">{targetTco2e.toLocaleString("en-US", { maximumFractionDigits: 0 })} tCO₂e</p>
        </div>
      </div>

      {/* Trajectory Info */}
      <div className="rounded-lg bg-gray-50 p-3">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-medium text-gray-600">Total Reduction: {reduction.toFixed(1)}%</span>
          <span className="text-xs text-gray-500">{target.trajectory_type} trajectory</span>
        </div>
        {/* Simple progress bar */}
        <div className="h-2 overflow-hidden rounded-full bg-gray-200">
          <div className="h-full bg-blue-600" style={{ width: `${Math.min(reduction, 100)}%` }} />
        </div>
      </div>

      {target.notes && <p className="text-sm text-gray-600 italic">&ldquo;{target.notes}&rdquo;</p>}

      <div className="text-xs text-gray-500">
        {target.target_amount_tco2e
          ? `Absolute target: ${target.target_amount_tco2e.toLocaleString("en-US", { maximumFractionDigits: 0 })} tCO₂e`
          : `Percentage reduction: ${target.target_pct_reduction?.toFixed(1)}%`}
      </div>
    </div>
  );
}
