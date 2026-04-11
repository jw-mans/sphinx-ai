import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import mkcert from 'vite-plugin-mkcert'
import tsconfigPaths from 'vite-tsconfig-paths'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '../', '')

  const frontendUrl = env.FRONTEND_URL || 'http://localhost:5173'
  const parsedUrl = new URL(frontendUrl)
  const hmrHost = parsedUrl.host

  return {
    base: '/',
    envDir: '../',

    plugins: [
      tailwindcss(),
      react(),
      tsconfigPaths(),
      ...(process.env.HTTPS ? [mkcert()] : []),
    ],

    build: {
      target: 'esnext',
    },

    publicDir: './public',

    server: {
      host: true,
      hmr: {
        protocol: process.env.HTTPS ? 'wss' : 'ws',
        host: hmrHost,
      },
    },
  }
})
