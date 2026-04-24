import { NextResponse, type NextRequest } from "next/server";

function hasIndexableQuery(request: NextRequest): boolean {
  const path = request.nextUrl.pathname;
  return request.nextUrl.search.length > 0 && !path.startsWith("/api/");
}

export function middleware(request: NextRequest) {
  const url = request.nextUrl;

  if (url.pathname.startsWith("/auto/")) {
    const vin = url.pathname.replace("/auto/", "");
    const normalizedVin = vin.toUpperCase();
    if (vin !== normalizedVin) {
      const nextUrl = url.clone();
      nextUrl.pathname = `/auto/${normalizedVin}`;
      return NextResponse.redirect(nextUrl, 308);
    }
  }

  if (url.pathname.startsWith("/cars/") && url.pathname !== url.pathname.toLowerCase()) {
    const nextUrl = url.clone();
    nextUrl.pathname = url.pathname.toLowerCase();
    return NextResponse.redirect(nextUrl, 308);
  }

  const response = NextResponse.next();
  if (hasIndexableQuery(request)) {
    response.headers.set("X-Robots-Tag", "noindex, follow");
  }
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"]
};
