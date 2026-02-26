import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
      '/auth': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
      '/users': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/posts': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/jobs': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/matches': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/threads': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/interviews': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/offers': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/notifications': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/messages': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/learning': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/courses': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/resumes': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/jds': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/companies': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/sessions': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/questions': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/flows': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/planners': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/sandbox': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/research': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/agents': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/opportunities': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/recommendations': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/smart-notifications': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/pipelines': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/applications': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/verification': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/admin': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/hackathons': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/analytics': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/demo': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
    }
  }
})


