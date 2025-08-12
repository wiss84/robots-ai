import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    hmr: {
      clientPort: 5173,
    },
    proxy: {
      '/project': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});