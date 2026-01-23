import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { setAuthToken } from '../api/client';
import { authService } from '../services/authService';
import { userService } from '../services/userService';

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

  useEffect(() => {
    const storedSession = localStorage.getItem(SESSION_KEY);
    if (storedSession) {
      const parsed = JSON.parse(storedSession);
      if (parsed.token) {
        setToken(parsed.token);
        setAuthToken(parsed.token);
        setUser(normalizeUser(parsed.user));
        refreshUser(parsed.token);
        return;
      }
    }
    setLoading(false);
  }, []);

  const persistSession = (sessionToken, sessionUser) => {
    localStorage.setItem(
      SESSION_KEY,
      JSON.stringify({ token: sessionToken, user: sessionUser })
    );
  };

  const refreshUser = async (overrideToken) => {
    try {
      const response = await userService.getMe();
      const normalized = normalizeUser(response);
      setUser(normalized);
      const activeToken = overrideToken || token;
      if (activeToken) {
        persistSession(activeToken, normalized);
      }
    } catch (error) {
      console.error('Failed to refresh user:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password, role) => {
    try {
      const response = await authService.login({ username, password, role });
      const normalized = normalizeUser(response.user);
      setToken(response.access_token);
      setAuthToken(response.access_token);
      setUser(normalized);
      persistSession(response.access_token, normalized);
      return { success: true, user: normalized };
    } catch (error) {
      console.error('Login error:', {
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

  const logout = () => {
    setUser(null);
    setToken(null);
    setAuthToken(null);
    localStorage.removeItem(SESSION_KEY);
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
