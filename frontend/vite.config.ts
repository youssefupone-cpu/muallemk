import { defineConfig } from 'vite'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import babel from '@rolldown/plugin-babel'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    // React Compiler (P1-5) — API v6: react() + babel({ presets: [reactCompilerPreset()] })
    react(),
    babel({ presets: [reactCompilerPreset()] }),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      workbox: {
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/api/books'),
            handler: 'NetworkFirst',
            options: { cacheName: 'books', expiration: { maxEntries: 50 } },
          },
          {
            urlPattern: ({ url }) => url.pathname === '/api/rag/ask',
            handler: 'NetworkOnly',
          },
        ],
      },
      includeAssets: ['favicon.svg', 'pwa-192x192.png', 'pwa-512x512.png'],
      manifest: {
        name: 'معلّمك — مساعد الدراسة',
        short_name: 'معلمك',
        description: 'مساعد دراسة ذكي محلي بالذكاء الاصطناعي',
        display: 'standalone',
        background_color: '#f8fafc',
        theme_color: '#0f172a',
        icons: [
          { src: '/pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: '/pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: '/favicon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'maskable' },
        ],
      },
    }),
  ],
  server: {
    host: '0.0.0.0',
    // المنفذان 3000/3001 مشغولان بخدمات أخرى على جهاز التطوير — ثبّتنا 3002.
    port: 3002,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  // Code-splitting عبر function form (متوافق مع Vite 8 / Rolldown)
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (
              id.includes('react-dom') ||
              id.includes('/react/') ||
              id.includes('react-router')
            ) {
              return 'vendor'
            }
            if (
              id.includes('react-markdown') ||
              id.includes('remark-math') ||
              id.includes('rehype-') ||
              id.includes('/katex')
            ) {
              return 'markdown'
            }
            if (id.includes('@tanstack') || id.includes('zustand')) {
              return 'query'
            }
          }
        },
      },
    },
  },
})
