import { createContext, useContext, useState, useEffect, useRef } from 'react';
import api from '../api/axios';
import { useAuth } from './AuthContext';

const NotificationContext = createContext(null);

export function NotificationProvider({ children }) {
  const { user } = useAuth();
  const [unreadCount, setUnreadCount] = useState(0);
  const [recentNotifications, setRecentNotifications] = useState([]);
  const wsRef = useRef(null);

  // Fetch initial unread count
  useEffect(() => {
    if (!user) return;
    api.get('/notifications/unread-count/')
      .then(res => setUnreadCount(res.data.unread_count))
      .catch(() => {});

    // Fetch recent 5
    api.get('/notifications/?page_size=5')
      .then(res => {
        const results = res.data.results || res.data;
        setRecentNotifications(Array.isArray(results) ? results : []);
      })
      .catch(() => {});
  }, [user]);

  // WebSocket connection
  useEffect(() => {
    if (!user) return;
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${proto}//${window.location.host}/ws/notifications/?token=${token}`);

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setUnreadCount(prev => prev + 1);
      setRecentNotifications(prev => [
        { id: data.id, message: data.message, notification_type: data.type, is_read: false, created_at: new Date().toISOString(), task: data.task_id, task_title: data.task_title },
        ...prev.slice(0, 4),
      ]);
    };

    ws.onclose = () => {};
    wsRef.current = ws;

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [user]);

  const markRead = async (id) => {
    await api.post(`/notifications/${id}/read/`);
    setUnreadCount(prev => Math.max(0, prev - 1));
    setRecentNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
  };

  const markAllRead = async () => {
    await api.post('/notifications/read-all/');
    setUnreadCount(0);
    setRecentNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
  };

  return (
    <NotificationContext.Provider value={{ unreadCount, recentNotifications, markRead, markAllRead, setUnreadCount }}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) throw new Error('useNotifications must be used within NotificationProvider');
  return context;
}
