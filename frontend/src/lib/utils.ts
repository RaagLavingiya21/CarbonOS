import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatKg(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "0 kg CO2e";
  }
  return `${new Intl.NumberFormat("en", {
    maximumFractionDigits: value >= 100 ? 0 : 1,
  }).format(value)} kg CO2e`;
}

export function formatPct(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "0%";
  }
  return `${new Intl.NumberFormat("en", { maximumFractionDigits: 1 }).format(value)}%`;
}
