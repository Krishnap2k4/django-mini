import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const navItems = [
  { to: '/', icon: 'dashboard', label: 'Dashboard' },
  { to: '/tasks', icon: 'task_alt', label: 'Tasks' },
  { to: '/notifications', icon: 'notifications', label: 'Notifications' },
  { to: '/profile', icon: 'person', label: 'Profile' },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <aside className="fixed top-0 left-0 w-[260px] h-screen text-white flex flex-col z-40 rounded-r-[16px]" style={{ background: 'linear-gradient(195deg, #1a1a2e 0%, #16213e 100%)' }}>
      <div className="px-5 py-6 flex items-center gap-3 border-b border-white/10">
        <span className="material-icons-round text-[32px] text-primary-light">task_alt</span>
        <span className="text-[16px] font-bold tracking-[0.5px]">Task Approval</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-4 space-y-1 overflow-y-auto">
        {navItems.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-[14px] py-[10px] rounded-[10px] text-[14px] font-medium transition-all mb-[2px] ${
                isActive
                  ? 'text-white shadow-primary'
                  : 'text-white/70 hover:text-white hover:bg-white/10'
              }`
            }
            style={({ isActive }) => isActive ? { background: 'linear-gradient(195deg, var(--color-primary), var(--color-primary-dark))' } : {}}
          >
            <span className="material-icons-round text-[20px]">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* User + Logout */}
      <div className="px-4 py-4 border-t border-white/10">
        <div className="flex items-center gap-3 px-4 py-2 mb-2">
          <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-sm font-semibold">
            {user?.username?.[0]?.toUpperCase() || 'U'}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium truncate">{user?.username}</p>
            <p className="text-xs text-white/50">{user?.role}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-white/60 hover:text-white hover:bg-white/5 transition-colors w-full cursor-pointer"
        >
          <span className="material-icons-round text-[20px]">logout</span>
          Sign Out
        </button>
      </div>
    </aside>
  );
}
