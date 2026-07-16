import { useAuth } from '../context/AuthContext';
import Topbar from '../components/layout/Topbar';

export default function Profile() {
  const { user } = useAuth();

  return (
    <>
      <Topbar title="Profile" subtitle="Your account details" />
      <div className="p-8 max-w-2xl">
        <div className="bg-surface rounded-[12px] border border-border shadow-card overflow-hidden">
          {/* Header */}
          <div className="bg-primary/5 px-8 py-8 flex items-center gap-6 border-b border-border">
            <div className="w-20 h-20 rounded-full bg-primary text-white flex items-center justify-center text-3xl font-bold shadow-sm">
              {user?.username?.[0]?.toUpperCase() || 'U'}
            </div>
            <div>
              <h2 className="text-2xl font-bold text-text-main">{user?.username}</h2>
              <p className="text-sm text-text-muted mt-1">{user?.role} • {user?.department || 'No department'}</p>
            </div>
          </div>

          {/* Details */}
          <div className="p-8">
            <h3 className="text-sm font-semibold text-text-main mb-5 uppercase tracking-wider text-text-muted">Account Information</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-6 gap-x-8">
              <div>
                <label className="block text-xs font-medium text-text-muted mb-1">User ID</label>
                <p className="text-sm font-medium text-text-main">{user?.id}</p>
              </div>
              <div>
                <label className="block text-xs font-medium text-text-muted mb-1">Username</label>
                <p className="text-sm font-medium text-text-main">{user?.username}</p>
              </div>
              <div>
                <label className="block text-xs font-medium text-text-muted mb-1">Email Address</label>
                <p className="text-sm font-medium text-text-main">{user?.email}</p>
              </div>
              <div>
                <label className="block text-xs font-medium text-text-muted mb-1">Role</label>
                <p className="text-sm font-medium text-text-main">{user?.role}</p>
              </div>
              <div>
                <label className="block text-xs font-medium text-text-muted mb-1">Department</label>
                <p className="text-sm font-medium text-text-main">{user?.department || '—'}</p>
              </div>
              <div>
                <label className="block text-xs font-medium text-text-muted mb-1">Full Name</label>
                <p className="text-sm font-medium text-text-main">
                  {user?.first_name || user?.last_name 
                    ? `${user?.first_name} ${user?.last_name}`.trim() 
                    : '—'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
