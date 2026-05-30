/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for minimal Docker image (no node_modules at runtime)
  output: "standalone",
  experimental: {},

  // Proxy /api/* to backend in development so the browser never needs to
  // reach a different origin (avoids CORS and cross-port issues in previews).
  async rewrites() {
    // BACKEND_URL = server-side only (WSL/container IP), not exposed to browser
    // NEXT_PUBLIC_API_BASE_URL = client-side override (leave empty for proxy mode)
    const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8080";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};
export default nextConfig;
