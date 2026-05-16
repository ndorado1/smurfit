import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // NO usamos rewrite — el backend ya monta sus rutas con prefijo /api,
      // asi mantenemos el mismo path en dev (Vite proxy) y en prod (FastAPI servidor).
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
