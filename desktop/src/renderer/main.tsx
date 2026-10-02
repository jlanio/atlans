import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App.js'
import './index.css'

const raiz = document.getElementById('root')
if (!raiz) throw new Error('#root ausente no index.html')

createRoot(raiz).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
