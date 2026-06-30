import { Tooltip } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

/**
 * Plain-language definitions for carbon jargon, sourced from the project glossary.
 * Wrap any term in <Term name="scope 3">Scope 3</Term> to give non-expert users a
 * one-hover definition.
 */
const GLOSSARY: Record<string, string> = {
  "scope 3":
    "Emissions from a company's value chain — not its own operations. Category 1 is purchased goods and services.",
  "scope 3 category 1":
    "Purchased Goods & Services — emissions from producing the goods and services a company buys.",
  "cradle-to-gate":
    "A boundary covering raw-material extraction through manufacturing, up to the point the product leaves the factory gate.",
  "emission factor":
    "An estimate of greenhouse gases released per unit of activity — e.g. kg CO₂e per USD of spend.",
  hotspot:
    "A material, process, or supplier that contributes a disproportionately large share of a product's footprint — a priority for reduction.",
  "primary data":
    "Firsthand, supplier- or facility-specific data from your value chain (e.g. a supplier's measured emissions).",
  "secondary data":
    "Industry-average data (databases, literature) used when primary data isn't available.",
  gwp: "Global Warming Potential — the warming effect of a gas over a time horizon (usually 100 years), normalized to CO₂e.",
  "co2e": "Carbon dioxide equivalent — a common unit that normalizes all greenhouse gases by their warming potential.",
  bom: "Bill of Materials — the list of components, materials, quantities, and weights that make up a product.",
  "activity data":
    "A quantitative measure of operations that generate emissions — fuel use, energy, or materials purchased.",
  "emission factor match confidence":
    "How well a material was matched to a CEDA sector: high (≥80), medium (60–79), or low (<60).",
};

export function Term({
  name,
  children,
  className,
}: {
  name: string;
  children: React.ReactNode;
  className?: string;
}) {
  const definition = GLOSSARY[name.trim().toLowerCase()];
  if (!definition) return <>{children}</>;
  return (
    <Tooltip content={definition}>
      <span
        className={cn(
          "cursor-help underline decoration-dotted decoration-muted-foreground/50 underline-offset-2",
          className,
        )}
      >
        {children}
      </span>
    </Tooltip>
  );
}

export const GLOSSARY_TERMS = Object.keys(GLOSSARY);
