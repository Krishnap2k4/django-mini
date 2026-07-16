import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/axios';
import Topbar from '../components/layout/Topbar';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import EmptyState from '../components/ui/EmptyState';
import { useNotifications } from '../context/NotificationContext';

export default function Notifications() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // 'all' or 'unread'
  const [nextCursor, setNextCursor] = useState(null);
  const [prevCursor, setPrevCursor] = useState(null);
  const { markRead: contextMarkRead, markAllRead: contextMarkAllRead, unreadCount } = useNotifications();

  const fetchNotifications = async (cursorUrl = null) => {
    setLoading(true);
    try {
      const url = cursorUrl || '/notifications/';
      const res = await api.get(url);
      setNotifications(res.data.results || []);
      setNextCursor(res.data.next);
      setPrevCursor(res.data.previous);
    } catch (err) {
      console.error('Failed to fetch notifications:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, [unreadCount]); // Re-fetch if unreadCount changes (new WS message)

  const filteredNotifications = notifications.filter(n => filter === 'all' || !n.is_read);

  const handleMarkRead = async (id) => {
    await contextMarkRead(id);
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
  };

  const handleMarkAllRead = async () => {
    await contextMarkAllRead();
    setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
  };

  return (
    <>
      <Topbar title="Notifications" subtitle="All your alerts and updates" />
      <div className="p-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex bg-surface border border-border rounded-lg p-1">
            <button
              onClick={() => setFilter('all')}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors cursor-pointer ${
                filter === 'all' ? 'bg-primary text-white shadow-sm' : 'text-text-muted hover:text-text-main'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilter('unread')}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors cursor-pointer ${
                filter === 'unread' ? 'bg-primary text-white shadow-sm' : 'text-text-muted hover:text-text-main'
              }`}
            >
              Unread
            </button>
          </div>

          <button
            onClick={handleMarkAllRead}
            disabled={loading || notifications.every(n => n.is_read)}
            className="inline-flex items-center gap-1.5 px-4 py-2 border border-border text-sm font-medium text-text-muted rounded-lg hover:bg-surface-alt transition-colors disabled:opacity-50 cursor-pointer"
          >
            <span className="material-icons-round text-[16px]">done_all</span>
            Mark all read
          </button>
        </div>

        {loading ? <LoadingSpinner /> : filteredNotifications.length === 0 ? (
          <EmptyState icon="notifications_none" message="No notifications found" />
        ) : (
          <div className="bg-surface rounded-[12px] border border-border shadow-card overflow-hidden">
            <div className="divide-y divide-border">
              {filteredNotifications.map(n => (
                <div key={n.id} className={`flex gap-4 p-5 transition-colors ${!n.is_read ? 'bg-primary/3' : 'hover:bg-surface-alt'}`}>
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                    !n.is_read ? 'bg-primary/20 text-primary' : 'bg-surface-alt text-text-muted border border-border'
                  }`}>
                    <span className="material-icons-round text-[20px]">
                      {n.notification_type === 'ADMIN_MESSAGE' ? 'campaign' : 'notifications'}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className={`text-sm ${!n.is_read ? 'font-semibold text-text-main' : 'text-text-main'}`}>
                          {n.message}
                        </p>
                        {n.task && (
                          <Link to={`/tasks/${n.task}`} className="text-xs text-primary font-medium hover:underline mt-1 inline-block">
                            View Task: {n.task_title || `#${n.task}`}
                          </Link>
                        )}
                        <p className="text-xs text-text-muted mt-1.5">
                          {new Date(n.created_at).toLocaleString()}
                        </p>
                      </div>
                      {!n.is_read && (
                        <button
                          onClick={() => handleMarkRead(n.id)}
                          className="w-8 h-8 rounded-full flex items-center justify-center text-text-muted hover:bg-white hover:shadow-sm border border-transparent hover:border-border transition-all cursor-pointer shrink-0"
                          title="Mark as read"
                        >
                          <span className="material-icons-round text-[18px]">check</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-6 py-3 border-t border-border bg-surface-alt">
              <button
                onClick={() => prevCursor && fetchNotifications(prevCursor)}
                disabled={!prevCursor}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg border border-border bg-surface text-text-muted hover:text-text-main disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed transition-colors"
              >
                <span className="material-icons-round text-[16px]">chevron_left</span> Previous
              </button>
              <button
                onClick={() => nextCursor && fetchNotifications(nextCursor)}
                disabled={!nextCursor}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg border border-border bg-surface text-text-muted hover:text-text-main disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed transition-colors"
              >
                Next <span className="material-icons-round text-[16px]">chevron_right</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
