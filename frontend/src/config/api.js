// Centralized API Configuration
// This ensures all services use the same API URL
// Uses VITE_API_URL from .env, falls back to localhost for development

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export default API_URL;
