"use client";

import { useEffect, useState } from "react";
import { AlertCircle, Loader2 } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import { CreateTargetPayload, scope2Api } from "@/lib/scope2-api";

interface CreateTargetDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

const CURRENT_YEAR = new Date().getFullYear();
const YEARS = Array.from({ length: 51 }, (_, i) => CURRENT_YEAR - 25 + i);

export function CreateTargetDialog({ open, onOpenChange, onSuccess }: CreateTargetDialogProps) {
  const [baseYear, setBaseYear] = useState(String(CURRENT_YEAR - 1));
  const [baseYearTco2e, setBaseYearTco2e] = useState("");
  const [targetYear, setTargetYear] = useState(String(CURRENT_YEAR + 9));
  const [targetMethod, setTargetMethod] = useState<"amount" | "percentage">("amount");
  const [targetAmount, setTargetAmount] = useState("");
  const [targetPercentage, setTargetPercentage] = useState("");
  const [trajectoryType, setTrajectoryType] = useState("linear");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    try {
      setError(null);

      if (!baseYearTco2e || (!targetAmount && !targetPercentage)) {
        setError("Please fill in all required fields");
        return;
      }

      const payload: CreateTargetPayload = {
        base_year: parseInt(baseYear, 10),
        base_year_tco2e: parseFloat(baseYearTco2e),
        target_year: parseInt(targetYear, 10),
        trajectory_type: trajectoryType,
        notes: notes || undefined,
      };

      if (targetMethod === "amount") {
        payload.target_amount_tco2e = parseFloat(targetAmount);
      } else {
        payload.target_pct_reduction = parseFloat(targetPercentage);
      }

      setLoading(true);
      await scope2Api.createTarget(payload);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create target");
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setBaseYear(String(CURRENT_YEAR - 1));
    setBaseYearTco2e("");
    setTargetYear(String(CURRENT_YEAR + 9));
    setTargetMethod("amount");
    setTargetAmount("");
    setTargetPercentage("");
    setTrajectoryType("linear");
    setNotes("");
    setError(null);
  };

  useEffect(() => {
    if (!open) {
      resetForm();
    }
  }, [open]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full max-w-lg overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Create Emissions Target</SheetTitle>
          <SheetDescription>Set a reduction target for your organization</SheetDescription>
        </SheetHeader>

        <div className="space-y-6 py-6">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Base Year Section */}
          <div className="space-y-4">
            <h3 className="font-semibold">Base Year</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="baseYear">Year</Label>
                <Select value={baseYear} onValueChange={setBaseYear}>
                  <SelectTrigger id="baseYear">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {YEARS.map((year) => (
                      <SelectItem key={year} value={String(year)}>
                        {year}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="baseYearTco2e">Total Emissions (tCO₂e)</Label>
                <Input
                  id="baseYearTco2e"
                  type="number"
                  placeholder="1000"
                  value={baseYearTco2e}
                  onChange={(e) => setBaseYearTco2e(e.target.value)}
                  step="0.01"
                  min="0"
                />
              </div>
            </div>
          </div>

          {/* Target Section */}
          <div className="space-y-4">
            <h3 className="font-semibold">Target</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="targetYear">Year</Label>
                <Select value={targetYear} onValueChange={setTargetYear}>
                  <SelectTrigger id="targetYear">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {YEARS.map((year) => (
                      <SelectItem key={year} value={String(year)}>
                        {year}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="targetMethod">Reduction Method</Label>
                <Select value={targetMethod} onValueChange={(v) => setTargetMethod(v as "amount" | "percentage")}>
                  <SelectTrigger id="targetMethod">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="amount">Absolute (tCO₂e)</SelectItem>
                    <SelectItem value="percentage">Percentage (%)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="targetValue">
                {targetMethod === "amount" ? "Target Emissions (tCO₂e)" : "Reduction Target (%)"}
              </Label>
              {targetMethod === "amount" ? (
                <Input
                  id="targetValue"
                  type="number"
                  placeholder="500"
                  value={targetAmount}
                  onChange={(e) => setTargetAmount(e.target.value)}
                  step="0.01"
                  min="0"
                />
              ) : (
                <Input
                  id="targetValue"
                  type="number"
                  placeholder="50"
                  value={targetPercentage}
                  onChange={(e) => setTargetPercentage(e.target.value)}
                  step="0.1"
                  min="0"
                  max="100"
                />
              )}
            </div>
          </div>

          {/* Trajectory */}
          <div className="space-y-2">
            <Label htmlFor="trajectory">Trajectory Type</Label>
            <Select value={trajectoryType} onValueChange={setTrajectoryType}>
              <SelectTrigger id="trajectory">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="linear">Linear</SelectItem>
                <SelectItem value="exponential">Exponential</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Notes (optional)</Label>
            <Textarea
              id="notes"
              placeholder="E.g., aligned with SBTi 1.5°C pathway"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
            />
          </div>

          {/* Buttons */}
          <div className="flex gap-3 justify-end border-t pt-6">
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={loading} className="gap-2">
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              Create Target
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
