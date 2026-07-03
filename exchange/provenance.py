"""Footprint provenance and methodology statement builders."""

from __future__ import annotations


def build_provenance_markdown(provenance: dict) -> str:
    """Render a human-readable methodology statement from a provenance object."""
    metadata = provenance.get("metadata") or {}
    method = provenance.get("method_statement") or {}
    dqr = provenance.get("aggregate_dqr") or {}
    lines = [
        f"# Footprint methodology — {metadata.get('product_name', 'Product')}",
        "",
        "## Product metadata",
        f"- Declared unit: {metadata.get('declared_unit') or 'piece'}",
        f"- System boundary: {metadata.get('system_boundary') or 'cradle-to-gate'}",
        f"- Geography: {metadata.get('geography_country') or 'not specified'}",
        f"- Reporting period: {metadata.get('reporting_period_start')} to {metadata.get('reporting_period_end')}",
        "",
        "## Method",
        method.get("summary", ""),
        method.get("detail", ""),
        "",
        f"- Primary data share: {(provenance.get('primary_data_share') or 0) * 100:.1f}%",
        (
            "- Aggregate DQR (technological / geographical / temporal): "
            f"{dqr.get('technological', '—')} / {dqr.get('geographical', '—')} / {dqr.get('temporal', '—')}"
        ),
        "",
        "## Line-item traceability",
    ]

    for item in provenance.get("line_items") or []:
        lines.append(
            f"- **{item.get('component') or '—'} / {item.get('material') or '—'}**: "
            f"sector={item.get('matched_sector') or 'unmatched'}, "
            f"EF={item.get('emission_factor')}, "
            f"kg CO₂e={item.get('kg_co2e')}, "
            f"source={item.get('ef_source') or 'none'}, "
            f"confidence={item.get('ef_confidence')}, "
            f"data_source={item.get('data_source')}, "
            f"DQR T{item.get('technological_dqr')}/G{item.get('geographical_dqr')}/Y{item.get('temporal_dqr')}"
        )

    lines.extend(["", "## Version lineage"])
    for version in provenance.get("version_lineage") or []:
        lines.append(
            f"- v{version.get('version')} (ID {version.get('product_id')}): "
            f"status={version.get('status')}, date={version.get('analysis_date')}"
        )

    return "\n".join(lines).strip() + "\n"
