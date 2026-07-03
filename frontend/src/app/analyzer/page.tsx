"use client";

import { Suspense } from "react";

import { AnalyzerPageContent } from "@/components/analyzer/AnalyzerFlow";

export default function AnalyzerPage() {
  return (
    <Suspense fallback={null}>
      <AnalyzerPageContent />
    </Suspense>
  );
}
