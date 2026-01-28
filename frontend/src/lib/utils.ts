import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateStr: string | null): string {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatCurrency(
  amount: number | null,
  currency = "USD"
): string {
  if (amount === null || amount === undefined) return "-";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(amount);
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    received: "bg-blue-100 text-blue-800",
    parsing: "bg-yellow-100 text-yellow-800",
    rates_lookup: "bg-purple-100 text-purple-800",
    rates_pending: "bg-orange-100 text-orange-800",
    rates_found: "bg-green-100 text-green-800",
    quote_draft: "bg-indigo-100 text-indigo-800",
    quote_review: "bg-cyan-100 text-cyan-800",
    sent: "bg-emerald-100 text-emerald-800",
    cancelled: "bg-gray-100 text-gray-800",
    ACTIVE: "bg-green-100 text-green-800",
    EXPIRED: "bg-red-100 text-red-800",
  };
  return colors[status] || "bg-gray-100 text-gray-800";
}

export function getUrgencyColor(urgency: string): string {
  return urgency === "URGENT"
    ? "bg-red-100 text-red-800"
    : "bg-gray-100 text-gray-600";
}

export function getDaysUntilExpiry(validTo: string): number {
  const now = new Date();
  const expiry = new Date(validTo);
  const diffTime = expiry.getTime() - now.getTime();
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
}

export function getExpiryColor(daysUntil: number): string {
  if (daysUntil < 0) return "text-gray-500";
  if (daysUntil <= 3) return "text-red-600";
  if (daysUntil <= 7) return "text-yellow-600";
  return "text-green-600";
}
