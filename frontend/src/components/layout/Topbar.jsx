import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useNotifications } from '../../context/NotificationContext';

export default function Topbar({ title, subtitle }) {
  const { user } = useAuth();
  const { unreadCount, recentNotifications, markRead, markAllRead } = useNotifications();
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  }, []);

  const timeAgo = (dateStr) => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  };

  return (
    <header className="flex items-center justify-between px-8 py-4 bg-transparent">
      <div>
        <h1 className="text-xl font-semibold text-text-main">{title || 'Dashboard'}</h1>
        {subtitle && <p className="text-sm text-text-muted mt-0.5">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-5">
        {/* Notification Bell */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={(e) => { e.stopPropagation(); setShowDropdown(!showDropdown); }}
            className="relative p-1 text-text-muted hover:text-text-main transition-colors cursor-pointer"
          >
            <span className="material-icons-round text-[24px]">notifications</span>
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 bg-danger text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </button>

          {showDropdown && (
            <div className="absolute top-11 right-0 w-[340px] bg-surface border border-border rounded-xl shadow-lg overflow-hidden z-50">
              <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                <span className="text-sm font-semibold">Notifications</span>
                <button
                  onClick={() => { markAllRead(); }}
                  className="text-xs text-primary font-semibold hover:underline cursor-pointer"
                >
                  Mark all read
                </button>
              </div>
              <div className="max-h-[280px] overflow-y-auto">
                {recentNotifications.length === 0 ? (
                  <div className="px-4 py-6 text-center text-sm text-text-muted">
                    No notifications
                  </div>
                ) : (
                  recentNotifications.map(n => (
                    <div
                      key={n.id}
                      className={`flex items-start gap-3 px-4 py-3 border-b border-border ${!n.is_read ? 'bg-primary/3' : ''}`}
                    >
                      <span className="material-icons-round text-info text-[18px] mt-0.5">circle_notifications</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-[13px] text-text-main leading-snug">{n.message}</p>
                        <span className="text-[11px] text-text-muted">{timeAgo(n.created_at)}</span>
                      </div>
                      {!n.is_read && (
                        <button
                          onClick={() => markRead(n.id)}
                          className="text-text-muted hover:text-primary cursor-pointer"
                          title="Mark as read"
                        >
                          <span className="material-icons-round text-[16px]">check</span>
                        </button>
                      )}
                    </div>
                  ))
                )}
              </div>
              <Link
                to="/notifications"
                onClick={() => setShowDropdown(false)}
                className="block text-center py-2.5 text-sm font-medium text-primary border-t border-border hover:bg-surface-alt transition-colors"
              >
                View all notifications
              </Link>
            </div>
          )}
        </div>

        {/* User */}
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center text-sm font-semibold">
            {user?.username?.[0]?.toUpperCase() || 'U'}
          </div>
          <div>
            <p className="text-sm font-medium text-text-main">{user?.username}</p>
            <p className="text-xs text-text-muted">{user?.role}</p>
          </div>
        </div>
      </div>
    </header>
  );
}
