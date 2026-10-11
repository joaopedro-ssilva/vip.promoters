import type { NextConfig } from "next";

const backendUrl = (
  process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value:
      "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()",
  },
];

// Notes:
// - Cache Components / Partial Prefetching are intentionally disabled: a
//   nonce-based CSP requires every page to be rendered per request, and PPR
//   is incompatible with it (see docs/01-app/02-guides/content-security-policy).
// - The Content-Security-Policy itself is set per request in src/proxy.ts.
const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
