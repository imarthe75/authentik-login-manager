import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    allowedHosts: [
      'loginmanager.casmart.internal'
    ],
    watch: {
      usePolling: true,
    },
    proxy: {
      '/api': {
        target: 'http://casmarts-login-backend:8000',
        changeOrigin: true,
        rewrite: (path) => path,
      }
    },
  },
});
