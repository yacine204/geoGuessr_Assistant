import apiClient from './apiClient';

export async function loginRequest(credentials) {
  const payload = {
    email: credentials.email,
    password: credentials.password,
  };

  const response = await apiClient.post('/auth/login', payload);
  return response.data;
}

export async function signupRequest(credentials) {
  const payload = {
    pseudo: credentials.pseudo || null,
    email: credentials.email,
    password: credentials.password,
  };

  const response = await apiClient.post('/auth/register', payload);
  return response.data;
}

export async function healthRequest() {
  const response = await apiClient.get('/');
  return response.data;
}
