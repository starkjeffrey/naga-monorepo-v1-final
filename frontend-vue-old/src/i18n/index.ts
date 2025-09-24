import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import km from './locales/km.json'

// Define the messages structure
interface Messages {
  en: typeof en
  km: typeof km
}

const messages: Messages = {
  en,
  km,
}

// Create i18n instance with type safety
const i18n = createI18n({
  legacy: false,
  locale: 'en',
  fallbackLocale: 'en',
  messages,
  globalInjection: true,
})

export default i18n

// Export types for use in components
export type MessageSchema = typeof en
export type LocaleCode = keyof Messages
