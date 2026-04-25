/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useMemo, useState } from 'react';
import { useCallback } from 'react';
import { loginRequest, signupRequest } from '../services/authService';

const TOKEN_KEY = 'geo_token';

const AuthContext = createContext(null);

function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function normalizeToken(payload) {
  if (typeof payload === 'string') {
    return payload;
  }

  if (payload && typeof payload === 'object') {
    return payload.token || payload.access_token || payload.jwt || '';
  }

  return '';
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(getStoredToken);

  const saveToken = useCallback((nextToken) => {
    localStorage.setItem(TOKEN_KEY, nextToken);
    setToken(nextToken);
  }, []);

  const login = useCallback(async (credentials) => {
    const payload = await loginRequest(credentials);
    const nextToken = normalizeToken(payload);

    if (!nextToken) {
      throw new Error('Backend response does not include a token.');
    }

    saveToken(nextToken);
  }, [saveToken]);

  const signup = useCallback(async (credentials) => {
    const payload = await signupRequest(credentials);
    const nextToken = normalizeToken(payload);

    if (!nextToken) {
      throw new Error('Backend response does not include a token.');
    }

    saveToken(nextToken);
  }, [saveToken]);

  const loginDemo = useCallback(() => {
    saveToken(`demo-${Date.now()}`);
  }, [saveToken]);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken('');
  }, []);

  const value = useMemo(
    () => ({
      token,
      isAuthenticated: Boolean(token),
      login,
      signup,
      loginDemo,
      logout,
    }),
    [token, login, signup, loginDemo, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }

  return context;
}
