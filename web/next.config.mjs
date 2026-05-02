/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Browser-side requests go directly to NEXT_PUBLIC_API_BASE_URL via
  // lib/api.ts — no Next.js proxy needed. CORS is permissive on the
  // FastAPI side, so direct calls are fine.
};

export default nextConfig;
