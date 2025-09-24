import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'
import { quasar, transformAssetUrls } from '@quasar/vite-plugin'
import VueI18nPlugin from '@intlify/unplugin-vue-i18n/vite'
import VueDevTools from 'vite-plugin-vue-devtools'
import { visualizer } from 'rollup-plugin-visualizer'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const isProduction = mode === 'production'
  const isDevelopment = mode === 'development'

  const plugins = [
    vue({
      template: { transformAssetUrls },
    }),
    quasar({
      sassVariables: '@/css/quasar.variables.sass',
    }),
    VueI18nPlugin({
      include: resolve(__dirname, './src/i18n/locales/**'),
      runtimeOnly: isProduction, // Use runtime-only in production for smaller bundle
      strictMessage: false, // Allow HTML in i18n messages
    }),
  ]

  // Development-only plugins
  if (isDevelopment) {
    plugins.push(VueDevTools())
  }

  // Production-only plugins
  if (isProduction) {
    plugins.push(
      visualizer({
        filename: 'dist/bundle-analysis.html',
        open: false,
        gzipSize: true,
        brotliSize: true,
      })
    )
  }

  // Add PWA plugin
  plugins.push(
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'favicon.png', 'naga-trans.png'],
      manifest: {
        name: 'Naga SIS - PUCSR',
        short_name: 'PUCSR',
        description: 'Student Information System for PUCSR',
        theme_color: '#7C3AED',
        start_url: '/',
        display: 'standalone',
        background_color: '#ffffff',
        icons: [
          {
            src: 'naga-trans.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: 'naga-trans.png',
            sizes: '512x512',
            type: 'image/png',
          },
          {
            src: 'naga-trans.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
          {
            src: 'naga-trans.png',
            sizes: '180x180',
            type: 'image/png',
          },
        ],
      },
      workbox: {
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/api\.*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              networkTimeoutSeconds: 10,
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 3600,
              },
              cacheableResponse: {
                statuses: [0, 200],
              },
            },
          },
          {
            urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp)$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'images-cache',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 30 * 24 * 60 * 60, // 30 Days
              },
            },
          },
          {
            urlPattern: /\.(?:woff|woff2|ttf|otf)$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'fonts-cache',
              expiration: {
                maxEntries: 20,
                maxAgeSeconds: 60 * 60 * 24 * 365, // 1 year
              },
            },
          },
        ],
      },
      devOptions: {
        enabled: isDevelopment,
        suppressWarnings: true,
      },
    })
  )

  return {
    plugins,
    resolve: {
      alias: {
        '@': resolve(__dirname, './src'),
        '~': resolve(__dirname, './src'),
        '@stores': resolve(__dirname, './src/stores'),
        '@pages': resolve(__dirname, './src/pages'),
        '@components': resolve(__dirname, './src/components'),
        '@composables': resolve(__dirname, './src/composables'),
        '@assets': resolve(__dirname, './src/assets'),
      },
    },
    server: {
      port: 5174,
      open: isDevelopment,
      host: true,
      cors: true,
    },
    preview: {
      port: 5174,
      host: true,
    },
    build: {
      target: 'esnext',
      sourcemap: isDevelopment,
      minify: isProduction ? 'esbuild' : false,
      cssMinify: isProduction,
      reportCompressedSize: false, // Disable to improve build speed
      chunkSizeWarningLimit: 1000,
      rollupOptions: {
        output: {
          // Manual chunk splitting for better caching
          manualChunks: {
            // Vendor chunk
            vendor: ['vue', 'vue-router', 'pinia'],
            // Quasar UI framework
            quasar: ['quasar'],
            // Media pipe (large library)
            mediapipe: ['@mediapipe/face_detection'],
            // I18n
            i18n: ['vue-i18n'],
            // QR code library
            qrcode: ['qrcode'],
            // IndexedDB library
            dexie: ['dexie'],
          },
          // Better file naming for caching
          chunkFileNames: (chunkInfo) => {
            const facadeModuleId = chunkInfo.facadeModuleId
              ? chunkInfo.facadeModuleId.split('/').pop().replace(/\.\w+$/, '')
              : 'chunk'
            return `js/${facadeModuleId}-[hash].js`
          },
          assetFileNames: (assetInfo) => {
            const extType = assetInfo.name.split('.').at(1)
            if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(extType)) {
              return `images/[name]-[hash][extname]`
            }
            if (/css/i.test(extType)) {
              return `css/[name]-[hash][extname]`
            }
            return `assets/[name]-[hash][extname]`
          },
        },
        external: (id) => {
          // Don't bundle large external dependencies that can be loaded from CDN
          if (isProduction && /^(three|chart\.js)$/.test(id)) {
            return true
          }
          // Externalize mobile-specific dependencies for web builds
          if (/^(expo-secure-store|@capacitor\/)/.test(id)) {
            return true
          }
          return false
        },
      },
    },
    optimizeDeps: {
      include: [
        'vue',
        'vue-router', 
        'pinia',
        'quasar',
        'vue-i18n',
        'qrcode',
        'dexie'
      ],
      exclude: [
        '@mediapipe/face_detection' // Large library, lazy load
      ],
    },
    // Environment variable handling
    define: {
      __VUE_I18N_FULL_INSTALL__: true,
      __VUE_I18N_LEGACY_API__: false,
      __INTLIFY_PROD_DEVTOOLS__: false,
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./src/test-setup.ts'],
    },
  }
})
