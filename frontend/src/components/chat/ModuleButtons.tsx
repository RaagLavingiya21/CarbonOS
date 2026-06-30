"use client";

import { FileUp, Mail, MessageCircle, Search } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

export interface ModuleButton {
  label: string;
  homeLabel: string;
  icon: LucideIcon;
  message: string;
  description: string;
}

export const MODULE_BUTTONS: ModuleButton[] = [
  {
    label: "Analyze BOM",
    homeLabel: "BOM Analyzer",
    icon: FileUp,
    message: "I want to analyze a bill of materials",
    description: "Upload a BOM and calculate product emissions",
  },
  {
    label: "Gap Analysis",
    homeLabel: "Gap Analyzer",
    icon: Search,
    message: "I want to run a gap analysis",
    description: "Assess Scope 3 coverage and data gaps",
  },
  {
    label: "Supplier Engagement",
    homeLabel: "Supplier Copilot",
    icon: Mail,
    message: "I want help with supplier engagement",
    description: "Rank suppliers and draft outreach emails",
  },
  {
    label: "Ask Advisor",
    homeLabel: "Advisor",
    icon: MessageCircle,
    message: "I'd like to ask the advisor a question",
    description: "Get GHG Protocol guidance and methodology help",
  },
];

interface ModuleButtonsProps {
  onSelect: (message: string) => void;
  disabled?: boolean;
}

export function ModuleButtons({ onSelect, disabled = false }: ModuleButtonsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {MODULE_BUTTONS.map(({ label, icon: Icon, message }) => (
        <Button
          key={label}
          type="button"
          variant="outline"
          size="sm"
          className="rounded-full"
          disabled={disabled}
          onClick={() => onSelect(message)}
        >
          <Icon className="h-4 w-4" />
          {label}
        </Button>
      ))}
    </div>
  );
}
