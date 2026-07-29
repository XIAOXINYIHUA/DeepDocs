/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/v1/:path*",
      },
    ];
  },
  output: "standalone",
};

module.exports = nextConfig;
