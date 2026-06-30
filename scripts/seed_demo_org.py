#!/usr/bin/env python3
"""Seed demo org with sample org_memory entries.

Products must be created separately (e.g. via the BOM Analyzer UI) under a
demo-owner account that belongs to the demo org. This script adds org-level
context the chat agent loads into Layer 3.

Usage:
    DEMO_ORG_ID=<uuid> python scripts/seed_demo_org.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from db.client import get_service_client

DEMO_MEMORIES = [
    (
        "company_context",
        "Aspire Inc. is an apparel manufacturer exploring Scope 3 reductions across its supply chain.",
    ),
    (
        "target",
        "Aspire Inc. is targeting a 30% Scope 3 reduction by 2030 from a 2022 baseline.",
    ),
    (
        "shared_knowledge",
        "Packaging and cotton fabric are the top emission hotspots across the product portfolio.",
    ),
]


def main() -> None:
    org_id = os.getenv("DEMO_ORG_ID", "").strip()
    owner_id = os.getenv("DEMO_OWNER_USER_ID", "").strip()
    if not org_id:
        print("Set DEMO_ORG_ID in .env to your demo organization UUID.")
        sys.exit(1)

    client = get_service_client()
    client.table("organizations").update({"is_demo": True}).eq("id", org_id).execute()

    if not owner_id:
        members = (
            client.table("org_members")
            .select("user_id")
            .eq("org_id", org_id)
            .limit(1)
            .execute()
        )
        if members.data:
            owner_id = str(members.data[0]["user_id"])
        else:
            print("Set DEMO_OWNER_USER_ID or add at least one member to the demo org.")
            sys.exit(1)

    for category, content in DEMO_MEMORIES:
        existing = (
            client.table("org_memory")
            .select("memory_id")
            .eq("org_id", org_id)
            .eq("content", content)
            .limit(1)
            .execute()
        )
        if existing.data:
            print(f"skip (exists): {content[:50]}...")
            continue

        client.table("org_memory").insert(
            {
                "org_id": org_id,
                "created_by": owner_id,
                "category": category,
                "content": content,
            }
        ).execute()
        print(f"added: {content[:50]}...")

    print("Done. Marked org as demo and seeded org_memory.")


if __name__ == "__main__":
    main()
