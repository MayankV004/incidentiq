"use client";

import React from "react";
import { cn } from "../lib/utils";

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string;
}

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-zinc-200/80 dark:bg-zinc-800/60",
        className
      )}
      {...props}
    />
  );
}

export function TableRowSkeleton({ cols = 5 }: { cols?: number }) {
  return (
    <div className="px-6 py-4 grid grid-cols-12 gap-3 items-center">
      <div className="col-span-3 space-y-1.5">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-3 w-16" />
      </div>
      <div className="col-span-4 space-y-1.5">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-3 w-24" />
      </div>
      <div className="col-span-2">
        <Skeleton className="h-5 w-20 rounded-full" />
      </div>
      <div className="col-span-1 text-right flex justify-end">
        <Skeleton className="h-4 w-12" />
      </div>
      <div className="col-span-2 text-right flex justify-end">
        <Skeleton className="h-4 w-16" />
      </div>
    </div>
  );
}

export function MetricCardSkeleton() {
  return (
    <div className="rounded-xl border bg-white dark:bg-[#121215] border-zinc-200/80 dark:border-zinc-800/80 p-5 space-y-3">
      <Skeleton className="h-3 w-32" />
      <div className="flex items-baseline gap-2">
        <Skeleton className="h-8 w-20" />
        <Skeleton className="h-4 w-10" />
      </div>
      <Skeleton className="h-3 w-40" />
    </div>
  );
}
