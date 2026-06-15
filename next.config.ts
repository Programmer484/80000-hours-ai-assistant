import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // In local dev, proxy /api/* to the FastAPI backend (uvicorn on :8000).
  // `npm run dev` starts both servers together (see package.json).
  // On Vercel this is handled by the rewrite in vercel.json instead, so this
  // is a no-op in production builds.
  async rewrites() {
    if (process.env.NODE_ENV !== 'development') return [];
    return [{ source: '/api/:path*', destination: 'http://127.0.0.1:8000/api/:path*' }];
  },
};

export default nextConfig;
