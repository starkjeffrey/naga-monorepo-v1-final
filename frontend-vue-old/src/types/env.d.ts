/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_GOOGLE_CLIENT_ID: string
  readonly VITE_GOOGLE_REDIRECT_URI: string
  readonly VITE_ALLOWED_EMAIL_DOMAIN: string
  // add more env variables as needed
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
