import { UserSettingsPage } from "@/components/dashboard/UserSettingsPage";

export const metadata = {
  title: "Settings | AgenticBay",
  description: "Manage profile, security, API keys, notifications, and billing settings.",
};

export default function DashboardSettingsPage() {
  return <UserSettingsPage />;
}
