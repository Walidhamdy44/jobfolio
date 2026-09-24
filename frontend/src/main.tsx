import React from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/manrope'
import './shared/styles/tokens.css'
import './style.css'
import { AppProviders } from './app/providers'

const rootElement = document.getElementById('root')
if (rootElement) {
  createRoot(rootElement).render(
    <React.StrictMode>
      <AppProviders />
    </React.StrictMode>
  )
}
