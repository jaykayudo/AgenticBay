import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const SIGN_IN_PATH = "/login";

const PROTECTED_PATHS = ["/dashboard", "/wallet", "/agents", "/settings", "/jobs"];
const PUBLIC_ONLY_PATHS = ["/login", "/auth/signin", "/auth/email/request", "/auth/email/verify"];

function isLocalRedirect(path: string | null) {
  return Boolean(path?.startsWith("/") && !path.startsWith("//"));
}

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const refreshToken = request.cookies.get("refresh_token")?.value;

  const isProtected = PROTECTED_PATHS.some((path) => pathname.startsWith(path));
  const isPublicOnly = PUBLIC_ONLY_PATHS.some((path) => pathname.startsWith(path));

  if (isProtected && !refreshToken) {
    const url = new URL(SIGN_IN_PATH, request.url);
    url.searchParams.set("redirect_after", `${pathname}${search}`);
    return NextResponse.redirect(url);
  }

  if (isPublicOnly && refreshToken) {
    const redirectAfter = request.nextUrl.searchParams.get("redirect_after");
    const redirectPath =
      isLocalRedirect(redirectAfter) && redirectAfter ? redirectAfter : "/dashboard";
    return NextResponse.redirect(new URL(redirectPath, request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
