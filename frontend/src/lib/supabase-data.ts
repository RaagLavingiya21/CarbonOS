import { AnalysisDetail, AnalysisLineItem, AnalysisSummary } from "@/lib/api";
import { createSupabaseBrowserClient } from "@/lib/supabase";

const PRODUCT_COLUMNS =
  "product_id, product_name, analysis_date, total_kg_co2e, matched_items, flagged_items, status, flagged_comment";

const LINE_ITEM_COLUMNS =
  "component, material, spend_usd, matched_sector, emission_factor, ef_source, kg_co2e, share_pct, flag_status";

export async function listAnalysesFromSupabase(): Promise<AnalysisSummary[]> {
  const supabase = createSupabaseBrowserClient();
  const { data, error } = await supabase
    .from("products")
    .select(PRODUCT_COLUMNS)
    .order("analysis_date", { ascending: false });

  if (error) throw new Error(error.message);
  return (data ?? []) as AnalysisSummary[];
}

export async function getAnalysisFromSupabase(productId: string): Promise<AnalysisDetail> {
  const supabase = createSupabaseBrowserClient();
  const { data: product, error: productError } = await supabase
    .from("products")
    .select(PRODUCT_COLUMNS)
    .eq("product_id", productId)
    .single();

  if (productError) throw new Error(productError.message);

  const { data: lineItems, error: lineItemsError } = await supabase
    .from("line_items")
    .select(LINE_ITEM_COLUMNS)
    .eq("product_id", productId)
    .order("share_pct", { ascending: false, nullsFirst: false });

  if (lineItemsError) throw new Error(lineItemsError.message);

  return {
    ...(product as AnalysisSummary),
    line_items: (lineItems ?? []) as AnalysisLineItem[],
  };
}
