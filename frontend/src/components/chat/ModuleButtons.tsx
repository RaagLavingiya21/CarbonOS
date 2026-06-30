"use client";

import { FileUp, Mail, MessageCircle, Search } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

interface ModuleButton {
  label: string;
  icon: LucideIcon;
  message: string;
}

const MODULE_BUTTONS: ModuleButton[] = [
  {
    label: "Analyze BOM",
    icon: FileUp,
    message: "I want to analyze a bill of materials",
  },
  {
    label: "Gap Analysis",
    icon: Search,
    message: "I want to run a gap analysis",
  },
  {
    label: "Supplier Engagement",
    icon: Mail,
    message: "I want help with supplier engagement",
  },
  {
    label: "Ask Advisor",
    icon: MessageCircle,
    message: "I'd like to ask the advisor a question",
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
