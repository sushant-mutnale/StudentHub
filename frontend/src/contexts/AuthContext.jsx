import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { setAuthToken, setOnSessionExpired, setOnTokenRefreshed } from '../api/client';
import { authService } from '../services/authService';
import { userService } from '../services/userService';
import { clearAllPersistedState } from '../hooks/usePersistedState';

const SESSION_KEY = 'studenthub_session';

const AuthContext = createContext(null);

const normalizeUser = (rawUser) => {
  if (!rawUser) return null;
  const formatted = {
    ...rawUser,
    id: rawUser.id || rawUser._id,
    fullName: rawUser.full_name || rawUser.fullName || '',
    companyName: rawUser.company_name || rawUser.companyName || '',
    contactNumber: rawUser.contact_number || rawUser.contactNumber || '',
    website: rawUser.website || rawUser.companyWebsite || '',
  };
  return formatted;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const tokenRef = useRef(null);

  const logout = () => {
    setUser(null);
    setToken(null);
    setAuthToken(null);
    tokenRef.current = null;
    localStorage.removeItem(SESSION_KEY);
    clearAllPersistedState();
  };

  useEffect(() => {
    // When the silent refresh in client.js ultimately fails, end the session.
    setOnSessionExpired(() => {
      logout();
    });

    // Persist freshly-issued access tokens so reloads keep a valid session.
    setOnTokenRefreshed((newToken) => {
      tokenRef.current = newToken;
      setToken(newToken);
      const stored = localStorage.getItem(SESSION_KEY);
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          parsed.token = newToken;
          localStorage.setItem(SESSION_KEY, JSON.stringify(parsed));
        } catch {
          /* ignore malformed session */
        }
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const storedSession = localStorage.getItem(SESSION_KEY);
    if (storedSession) {
      const parsed = JSON.parse(storedSession);
      if (parsed.token) {
        tokenRef.current = parsed.token;
        setToken(parsed.token);
        setAuthToken(parsed.token);
        setUser(normalizeUser(parsed.user));
        refreshUser(parsed.token);
        return;
      }
    }
    setLoading(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const persistSession = (sessionToken, sessionUser) => {
    localStorage.setItem(
      SESSION_KEY,
      JSON.stringify({ token: sessionToken, user: sessionUser })
    );
  };

  const refreshUser = async (overrideToken) => {
    console.log('AuthContext: refreshUser called', { hasOverrideToken: !!overrideToken });
    try {
      const response = await userService.getMe();
      console.log('AuthContext: refreshUser success');
      const normalized = normalizeUser(response);
      setUser(normalized);
      const activeToken = overrideToken || token;
      if (activeToken) {
        persistSession(activeToken, normalized);
      }
    } catch (error) {
      console.error('AuthContext: Failed to refresh user:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password, role) => {
    console.log('AuthContext: login attempt', { username, role });
    try {
      const response = await authService.login({ username, password, role });
      console.log('AuthContext: login success');
      const normalized = normalizeUser(response.user);
      tokenRef.current = response.access_token;
      setToken(response.access_token);
      setAuthToken(response.access_token);
      setUser(normalized);
      persistSession(response.access_token, normalized);
      return { success: true, user: normalized };
    } catch (error) {
      console.error('AuthContext: Login error details:', {
        message: error.message,
        code: error.code,
        responseStatus: error.response?.status,
        responseData: error.response?.data,
        requestURL: error.config?.url,
        requestBaseURL: error.config?.baseURL,
      });

      const messageFromServer =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        error.message ||
        'Unexpected error, please try again.';

      return { success: false, error: messageFromServer };
    } finally {
      setLoading(false);
    }
  };

  const signupStudent = async (payload) => {
    try {
      await authService.signupStudent(payload);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  const signupRecruiter = async (payload) => {
    try {
      await authService.signupRecruiter(payload);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  const updateUser = (updates) => {
    setUser((prev) => {
      if (!prev) return prev;
      const merged = normalizeUser({ ...prev, ...updates });
      if (token) {
        persistSession(token, merged);
      }
      return merged;
    });
  };

  const value = useMemo(
    () => ({
      user,
      token,
      login,
      signupStudent,
      signupRecruiter,
      logout,
      updateUser,
      refreshUser,
      isAuthenticated: !!user,
      loading,
    }),
    [user, token, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
