import type { ReactNode } from "react";

import { BuyerDashboardShell } from "@/components/dashboard/BuyerDashboardShell";

type DashboardLayoutProps = {
  children: ReactNode;
};

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return <BuyerDashboardShell>{children}</BuyerDashboardShell>;
}
