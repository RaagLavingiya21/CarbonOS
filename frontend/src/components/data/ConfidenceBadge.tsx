import { Badge } from "@/components/ui/badge";
import { Tooltip } from "@/components/ui/tooltip";

/**
 * Confidence in an emission-factor match (0–100).
 * Thresholds mirror the backend: >=80 high, 60–79 medium, <60 low/no match.
 * Color encodes confidence: green = high, amber = medium, red = low.
 */
export function ConfidenceBadge({ score }: { score: number | null | undefined }) {
  if (score == null) {
    return (
      <Tooltip content="No emission factor was matched for this row.">
        <Badge variant="neutral">unmatched</Badge>
      </Tooltip>
    );
  }

  const rounded = Math.round(score);
  let variant: "low" | "medium" | "high";
  let label: string;
  let explanation: string;

  if (rounded >= 80) {
    variant = "low"; // green ramp = good / high confidence
    label = "High";
    explanation = "Strong match to a CEDA sector (≥80). Safe to use.";
  } else if (rounded >= 60) {
    variant = "medium";
    label = "Medium";
    explanation = "Approximate match (60–79). Review the matched sector before relying on it.";
  } else {
    variant = "high"; // red ramp = caution / low confidence
    label = "Low";
    explanation = "Weak match (<60). Flagged for human review.";
  }

  return (
    <Tooltip content={explanation}>
      <Badge variant={variant}>
        <span className="tabular-nums">{rounded}%</span>
        <span className="text-[0.95em]">· {label}</span>
      </Badge>
    </Tooltip>
  );
}
