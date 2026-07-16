import { createContext, useContext, useState, useEffect } from 'react';
import api from '../api/axios';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('user');
    return stored ? JSON.parse(stored) : null;
  });
  const [loading, setLoading] = useState(false);

  const login = async (username, password) => {
    const res = await api.post('/auth/login/', { username, password });
    const { access, refresh } = res.data;
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);

    // Decode JWT payload to get user info
    const payload = JSON.parse(atob(access.split('.')[1]));
    
    // Fetch full user details from a task to get role info
    // SimpleJWT includes user_id by default. We'll store basic info
    // and fetch role from the dashboard counts endpoint (which includes role context)
    const userData = { id: payload.user_id, username, role: null };

    // We need to get the role — let's make a quick request
    // The register endpoint returns role, but login doesn't. 
    // We'll use a workaround: fetch dashboard counts (authenticated endpoint)
    // and infer from the response, or better yet, we need a /me endpoint.
    // For now, let's create a simple approach: decode what we can.
    
    // Actually, let's add a profile fetch. First, store what we have.
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
    
    // We need user role for conditional rendering. Let's fetch it.
    const profileRes = await api.get('/auth/me/');
    const fullUser = profileRes.data;
    localStorage.setItem('user', JSON.stringify(fullUser));
    setUser(fullUser);
    return fullUser;
  };

  const register = async (data) => {
    const res = await api.post('/auth/register/', { ...data, role: 'STAFF' });
    const { user: userData, access, refresh } = res.data;
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);
    return userData;
  };

  const logout = async () => {
    const refresh = localStorage.getItem('refresh_token');
    try {
      if (refresh) await api.post('/auth/logout/', { refresh });
    } catch {
      // Ignore logout errors
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
