import type { NextConfig } from "next";

const apiOrigin = process.env.API_ORIGIN ?? "http://127.0.0.1:43180";
const extraDevOrigins = (process.env.ALLOWED_DEV_ORIGINS ?? "")
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

const nextConfig: NextConfig = {
  agentRules: false,
  devIndicators: false,
  allowedDevOrigins: ["127.0.0.1", "localhost", ...extraDevOrigins],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiOrigin}/api/:path*`,
      },
      {
        source: "/auth/:path*",
        destination: `${apiOrigin}/auth/:path*`,
      },
      {
        source: "/users",
        destination: `${apiOrigin}/users`,
      },
      {
        source: "/profiles/:path*",
        destination: `${apiOrigin}/profiles/:path*`,
      },
      {
        source: "/inventory/:path*",
        destination: `${apiOrigin}/inventory/:path*`,
      },
    ];
  },
};

export default nextConfig;
