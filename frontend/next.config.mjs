/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for minimal Docker image (no node_modules at runtime)
  output: "standalone",
  experimental: {},

  // Proxy /api/* to backend in development so the browser never needs to
  // reach a different origin (avoids CORS and cross-port issues in previews).
  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8082";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};
export default nextConfig;
