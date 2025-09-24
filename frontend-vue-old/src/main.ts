if (import.meta.env.DEV) {
  console.log('Main.ts is loading...')
}

// import './assets/main.css' // Temporarily disabled to debug

import { createApp } from 'vue'
import { Quasar, Notify } from 'quasar'
import { createPinia } from 'pinia'
import router from './router'
import i18n from './i18n'
import { useDatabase } from './composables/useDatabase'
import App from './App.vue'

// Import icon libraries
import '@quasar/extras/material-icons/material-icons.css'

// Import Quasar css
import 'quasar/src/css/index.sass'

const pinia = createPinia()

const app = createApp(App)

app.use(Quasar, {
  plugins: {
    Notify,
  },
  config: {
    brand: {
      primary: '#7C3AED',
      secondary: '#26A69A',
      accent: '#9C27B0',
      dark: '#1d1d1d',
      positive: '#21BA45',
      negative: '#C10015',
      info: '#31CCEC',
      warning: '#F2C037',
    },
  },
})

app.use(pinia)
app.use(router)
app.use(i18n)

// Initialize database
const { initializeDatabase } = useDatabase()
initializeDatabase()
  .then(() => {
    if (import.meta.env.DEV) {
      console.log('Database ready')
    }
  })
  .catch((err: Error) => {
    if (import.meta.env.DEV) {
      console.error('Database initialization failed:', err)
    }
  })

app.mount('#app')
if (import.meta.env.DEV) {
  console.log('App mounted successfully!')
}
