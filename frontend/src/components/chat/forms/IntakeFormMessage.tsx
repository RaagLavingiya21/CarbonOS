"use client";

import { BOMIntakeForm } from "@/components/chat/forms/BOMIntakeForm";
import { GapAnalyzerIntakeForm } from "@/components/chat/forms/GapAnalyzerIntakeForm";
import { SupplierCopilotIntakeForm } from "@/components/chat/forms/SupplierCopilotIntakeForm";
import type { IntakeForm, IntakeSubmitPayload } from "@/lib/chat-api";

interface IntakeFormMessageProps {
  intakeForm: IntakeForm;
  disabled?: boolean;
  onSubmit: (payload: IntakeSubmitPayload) => void;
}

export function IntakeFormMessage({
  intakeForm,
  disabled = false,
  onSubmit,
}: IntakeFormMessageProps) {
  return (
    <div className="mt-3 rounded-lg border border-border/60 bg-secondary/30 p-4">
      <div className="mb-4">
        <p className="text-sm font-medium text-foreground">{intakeForm.title}</p>
        <p className="mt-1 text-xs text-muted-foreground">
          {intakeForm.description}
        </p>
      </div>
      {intakeForm.module_type === "bom_analyzer" ? (
        <BOMIntakeForm disabled={disabled} onSubmit={onSubmit} />
      ) : null}
      {intakeForm.module_type === "gap_analyzer" ? (
        <GapAnalyzerIntakeForm disabled={disabled} onSubmit={onSubmit} />
      ) : null}
      {intakeForm.module_type === "supplier_copilot" ? (
        <SupplierCopilotIntakeForm disabled={disabled} onSubmit={onSubmit} />
      ) : null}
    </div>
  );
}
