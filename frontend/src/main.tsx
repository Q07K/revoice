import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from '@/App'
import '@/index.css'

// Apply the theme before first paint (defaults to the studio dark) to avoid a flash.
const storedTheme = localStorage.getItem('revoice-theme')
document.documentElement.classList.toggle('dark', storedTheme !== 'light')

const rootElement = document.getElementById('root')
if (rootElement === null) {
  throw new Error('Root element #root not found.')
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
