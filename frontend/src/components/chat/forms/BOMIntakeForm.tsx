"use client";

import { useRef, useState } from "react";
import { Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { BomIntakePayload } from "@/lib/chat-api";

interface BOMIntakeFormProps {
  disabled?: boolean;
  onSubmit: (payload: BomIntakePayload) => void;
}

export function BOMIntakeForm({ disabled = false, onSubmit }: BOMIntakeFormProps) {
  const [productName, setProductName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!productName.trim() || !file || disabled) return;
    onSubmit({
      module_type: "bom_analyzer",
      product_name: productName.trim(),
      file,
    });
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <div className="space-y-2">
        <Label htmlFor="bom-product-name">Product name</Label>
        <Input
          id="bom-product-name"
          placeholder="e.g. Organic Cotton T-Shirt"
          value={productName}
          disabled={disabled}
          onChange={(event) => setProductName(event.target.value)}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="bom-file">BOM file</Label>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <Input
            ref={fileInputRef}
            id="bom-file"
            type="file"
            accept=".csv,.xlsx,.xls"
            disabled={disabled}
            className="hidden"
            onChange={(event) => {
              const selected = event.target.files?.[0] ?? null;
              setFile(selected);
            }}
          />
          <Button
            type="button"
            variant="outline"
            disabled={disabled}
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="h-4 w-4" />
            Choose file
          </Button>
          <span className="text-sm text-muted-foreground">
            {file ? file.name : "CSV or Excel (.csv, .xlsx, .xls)"}
          </span>
        </div>
      </div>
      <Button
        type="submit"
        disabled={disabled || !productName.trim() || !file}
        className="w-full sm:w-auto"
      >
        Submit
      </Button>
    </form>
  );
}
