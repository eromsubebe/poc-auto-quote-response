/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",

  // Proxy API calls from the browser to the backend without hardcoding the backend URL
  // into the client bundle.
  //
  // Cloud Run deployment: set BACKEND_URL to the deployed backend's URL.
  // Example: BACKEND_URL=https://creseada-rfq-backend-xxxxx-uc.a.run.app
  async rewrites() {
    const backend = process.env.BACKEND_URL;
    if (!backend) return [];
    return [
      {
        source: "/api/:path*",
        destination: `${backend}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
