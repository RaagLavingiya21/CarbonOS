"use client";

import { useState } from "react";

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
import { Textarea } from "@/components/ui/textarea";
import type { GapAnalyzerIntakePayload } from "@/lib/chat-api";

const SIZE_OPTIONS = ["1-100", "100-500", "500-5000", "5000+"] as const;

interface GapAnalyzerIntakeFormProps {
  disabled?: boolean;
  onSubmit: (payload: GapAnalyzerIntakePayload) => void;
}

export function GapAnalyzerIntakeForm({
  disabled = false,
  onSubmit,
}: GapAnalyzerIntakeFormProps) {
  const [companyName, setCompanyName] = useState("");
  const [size, setSize] = useState<string>("");
  const [sector, setSector] = useState("");
  const [geography, setGeography] = useState("");
  const [products, setProducts] = useState("");

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      !companyName.trim() ||
      !size ||
      !sector.trim() ||
      !geography.trim() ||
      !products.trim() ||
      disabled
    ) {
      return;
    }
    onSubmit({
      module_type: "gap_analyzer",
      company_name: companyName.trim(),
      size,
      sector: sector.trim(),
      geography: geography.trim(),
      products: products.trim(),
    });
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <div className="space-y-2">
        <Label htmlFor="gap-company-name">Company name</Label>
        <Input
          id="gap-company-name"
          value={companyName}
          disabled={disabled}
          onChange={(event) => setCompanyName(event.target.value)}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="gap-size">Company size</Label>
        <Select value={size} onValueChange={setSize} disabled={disabled}>
          <SelectTrigger id="gap-size">
            <SelectValue placeholder="Select company size" />
          </SelectTrigger>
          <SelectContent>
            {SIZE_OPTIONS.map((option) => (
              <SelectItem key={option} value={option}>
                {option}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-2">
        <Label htmlFor="gap-sector">Sector</Label>
        <Input
          id="gap-sector"
          placeholder="e.g. Apparel"
          value={sector}
          disabled={disabled}
          onChange={(event) => setSector(event.target.value)}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="gap-geography">Geography</Label>
        <Input
          id="gap-geography"
          placeholder="e.g. United States"
          value={geography}
          disabled={disabled}
          onChange={(event) => setGeography(event.target.value)}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="gap-products">Products</Label>
        <Textarea
          id="gap-products"
          placeholder="List key products or product categories"
          value={products}
          disabled={disabled}
          onChange={(event) => setProducts(event.target.value)}
        />
      </div>
      <Button
        type="submit"
        disabled={
          disabled ||
          !companyName.trim() ||
          !size ||
          !sector.trim() ||
          !geography.trim() ||
          !products.trim()
        }
        className="w-full sm:w-auto"
      >
        Submit
      </Button>
    </form>
  );
}
