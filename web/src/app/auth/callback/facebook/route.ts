import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type FacebookOAuthResponse = {
  access_token?: string;
  user?: {
    is_new_user?: boolean;
  };
  email_required?: boolean;
  pending_token?: string;
};

function appendSetCookieHeaders(response: NextResponse, backendResponse: Response) {
  const headersWithCookies = backendResponse.headers as Headers & {
    getSetCookie?: () => string[];
  };
  const setCookies = headersWithCookies.getSetCookie?.() ?? [];

  if (setCookies.length > 0) {
    setCookies.forEach((cookie) => response.headers.append("set-cookie", cookie));
    return;
  }

  const setCookie = backendResponse.headers.get("set-cookie");
  if (setCookie) {
    response.headers.append("set-cookie", setCookie);
  }
}

function oauthError(request: NextRequest, errorType: string) {
  return NextResponse.redirect(new URL(`/auth/error?error_type=${errorType}`, request.url));
}

export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code");
  const state = request.nextUrl.searchParams.get("state");
  const error = request.nextUrl.searchParams.get("error");

  if (error) {
    return oauthError(request, `oauth_${error}`);
  }

  if (!code || !state) {
    return oauthError(request, "oauth_invalid");
  }

  const backendUrl = new URL(`${API_BASE_URL}/api/auth/facebook/callback`);
  backendUrl.searchParams.set("code", code);
  backendUrl.searchParams.set("state", state);

  const backendResponse = await fetch(backendUrl, {
    headers: {
      cookie: request.headers.get("cookie") ?? "",
    },
    cache: "no-store",
  });

  if (!backendResponse.ok) {
    return oauthError(request, "oauth_failed");
  }

  const data = (await backendResponse.json()) as FacebookOAuthResponse;

  if (data.email_required) {
    const emailUrl = new URL("/auth/error?error_type=oauth_email_required", request.url);
    if (data.pending_token) {
      emailUrl.searchParams.set("pending_token", data.pending_token);
    }
    return NextResponse.redirect(emailUrl);
  }

  const redirectPath = data.user?.is_new_user ? "/profile/complete" : "/dashboard";
  const response = NextResponse.redirect(new URL(redirectPath, request.url));

  appendSetCookieHeaders(response, backendResponse);

  if (data.access_token && data.user) {
    response.cookies.set("post_oauth", JSON.stringify(data), {
      maxAge: 60,
      path: "/",
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
    });
  }

  return response;
}
