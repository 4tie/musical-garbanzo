import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ['127.0.0.1', '*.replit.dev', '*.pike.replit.dev', '*.repl.co'],

  // Proxy all /api and /health requests to the FastAPI backend.
  // This is required on Replit (and any proxied environment) because the
  // browser cannot reach 127.0.0.1:8000 directly — only the Next.js server
  // can. When NEXT_PUBLIC_API_BASE_URL is empty, the frontend uses relative
  // paths, which Next.js intercepts here and forwards to the backend.
  async rewrites() {
    const backendOrigin = process.env.BACKEND_ORIGIN ?? 'http://127.0.0.1:8000';
    return [
      {
        source: '/health',
        destination: `${backendOrigin}/health`,
      },
      {
        source: '/api/:path*',
        destination: `${backendOrigin}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
