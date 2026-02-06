// Centralized API Configuration
// This ensures all services use the same API URL

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default API_URL;
