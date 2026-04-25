import { redirect } from "next/navigation";

export default function ApiKeysRedirectPage() {
  redirect("/dashboard/settings/api-keys");
}
