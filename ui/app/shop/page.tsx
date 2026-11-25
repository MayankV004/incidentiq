"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { ShopView } from "../../components/tabs/ShopView";

export default function ShopPage() {
  const router = useRouter();
  return <ShopView onSwitchToLive={() => router.push("/")} />;
}
