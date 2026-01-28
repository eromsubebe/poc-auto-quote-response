"use client";

import { cn } from "@/lib/utils";
import { AlertTriangle, CheckCircle, Clock, XCircle } from "lucide-react";

interface SLABadgeProps {
  deadline: string | null;
  breached: boolean;
  className?: string;
}

export function SLABadge({ deadline, breached, className }: SLABadgeProps) {
  if (!deadline) {
    return (
      <span className={cn("text-gray-400 text-sm", className)}>No SLA</span>
    );
  }

  const now = new Date();
  const deadlineDate = new Date(deadline);
  const hoursRemaining = (deadlineDate.getTime() - now.getTime()) / (1000 * 60 * 60);

  if (breached || hoursRemaining < 0) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800",
          className
        )}
      >
        <XCircle className="w-3 h-3" />
        Breached
      </span>
    );
  }

  if (hoursRemaining <= 2) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800",
          className
        )}
      >
        <AlertTriangle className="w-3 h-3" />
        {hoursRemaining.toFixed(1)}h left
      </span>
    );
  }

  if (hoursRemaining <= 8) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800",
          className
        )}
      >
        <Clock className="w-3 h-3" />
        {hoursRemaining.toFixed(1)}h left
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800",
        className
      )}
    >
      <CheckCircle className="w-3 h-3" />
      On track
    </span>
  );
}
