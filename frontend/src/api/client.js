import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: false,
});

let authToken = null;

export const setAuthToken = (token) => {
  authToken = token;
};

api.interceptors.request.use((config) => {
  console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`, config);
  if (!config.headers) {
    config.headers = {};
  }
  if (authToken) {
    config.headers.Authorization = `Bearer ${authToken}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`, response.data);
    return response;
  },
  (error) => {
    console.error(`API Error: ${error.message}`, {
      url: error.config?.url,
      status: error.response?.status,
      data: error.response?.data
    });
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'Unexpected error';
    return Promise.reject(new Error(message));
  }
);


