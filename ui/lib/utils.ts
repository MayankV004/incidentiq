import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCost(usd?: number | null): string {
  if (usd === undefined || usd === null || isNaN(usd)) return "$0.0000";
  if (usd === 0) return "$0.0000";
  return `$${usd.toFixed(4)}`;
}

export function formatLatency(ms?: number | null): string {
  if (ms === undefined || ms === null || isNaN(ms)) return "0ms";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}
