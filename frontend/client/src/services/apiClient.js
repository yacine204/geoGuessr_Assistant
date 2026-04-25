import axios from 'axios';

const TOKEN_KEY = 'geo_token';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 15000,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const isNetworkFailure = !error?.response;
    const apiBase = apiClient.defaults.baseURL || 'http://127.0.0.1:8000';

    const message =
      (isNetworkFailure
        ? `Cannot reach API at ${apiBase}. Start backend server on that URL, then retry.`
        : error?.response?.data?.detail ||
          error?.response?.data?.message ||
          error.message) ||
      'Unexpected API error';

    return Promise.reject(new Error(message));
  }
);

export default apiClient;
