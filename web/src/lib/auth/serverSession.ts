import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import type { UserProfile } from "@/lib/api/auth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function getServerSession(): Promise<UserProfile | null> {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get("refresh_token")?.value;

  if (!refreshToken) {
    return null;
  }

  try {
    const refreshResponse = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: "no-store",
    });

    if (!refreshResponse.ok) {
      return null;
    }

    const tokenData = (await refreshResponse.json()) as { access_token?: string };

    if (!tokenData.access_token) {
      return null;
    }

    const profileResponse = await fetch(`${API_BASE_URL}/api/auth/me`, {
      headers: {
        Authorization: `Bearer ${tokenData.access_token}`,
      },
      cache: "no-store",
    });

    if (!profileResponse.ok) {
      return null;
    }

    return (await profileResponse.json()) as UserProfile;
  } catch {
    return null;
  }
}

export async function requireAuth(): Promise<UserProfile> {
  const session = await getServerSession();

  if (!session) {
    redirect("/login");
  }

  return session;
}

export async function requireAdmin(): Promise<UserProfile> {
  const session = await requireAuth();

  if (session.role.toLowerCase() !== "admin") {
    redirect("/dashboard");
  }

  return session;
}
