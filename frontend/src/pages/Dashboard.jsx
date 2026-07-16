import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';
import Topbar from '../components/layout/Topbar';
import StatusBadge from '../components/ui/StatusBadge';
import PriorityBadge from '../components/ui/PriorityBadge';
import LoadingSpinner from '../components/ui/LoadingSpinner';

export default function Dashboard() {
  const { user } = useAuth();
  const [counts, setCounts] = useState(null);
  const [recentTasks, setRecentTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [countsRes, tasksRes] = await Promise.all([
          api.get('/dashboard/counts/'),
          api.get('/tasks/'),
        ]);
        setCounts(countsRes.data);
        const results = tasksRes.data.results || tasksRes.data;
        setRecentTasks(Array.isArray(results) ? results.slice(0, 5) : []);
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const statCards = counts ? [
    { label: 'Drafts', value: counts.draft, icon: 'edit_note', bg: 'linear-gradient(195deg, #64748b, #475569)' },
    { label: 'Submitted', value: counts.submitted, icon: 'send', bg: 'linear-gradient(195deg, #3b82f6, #1d4ed8)' },
    { label: 'Approved', value: counts.approved, icon: 'check_circle', bg: 'linear-gradient(195deg, #06d6a0, #059669)' },
    { label: 'Rejected', value: counts.rejected, icon: 'cancel', bg: 'linear-gradient(195deg, #ef4444, #dc2626)' },
    ...(user?.role === 'MANAGER' ? [{ label: 'Pending Review', value: counts.pending_review, icon: 'rate_review', bg: 'linear-gradient(195deg, #f59e0b, #d97706)' }] : []),
  ] : [];

  if (loading) return (
    <>
      <Topbar title="Dashboard" subtitle={`Welcome back, ${user?.username}`} />
      <LoadingSpinner />
    </>
  );

  return (
    <>
      <Topbar title="Dashboard" subtitle={`Welcome back, ${user?.username}`} />
      <div className="p-8">
        {/* Stat Cards */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-5 mb-6">
          {statCards.map(card => (
            <div key={card.label} className="bg-surface rounded-[12px] border border-border p-5 shadow-card hover:shadow-hover hover:-translate-y-0.5 transition-all flex items-center gap-4">
              <div className="w-[52px] h-[52px] rounded-xl flex items-center justify-center text-white shrink-0" style={{ background: card.bg }}>
                <span className="material-icons-round text-[26px]">{card.icon}</span>
              </div>
              <div>
                <h4 className="text-[22px] font-bold text-text-main leading-none">{card.value}</h4>
                <p className="text-[13px] text-text-muted mt-1">{card.label}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Recent Tasks */}
        <div className="bg-surface rounded-[12px] border border-border shadow-card overflow-hidden">
          <div className="flex items-center justify-between px-6 py-5 border-b border-border">
            <h2 className="text-base font-semibold">Recent Tasks</h2>
            <Link to="/tasks" className="text-sm text-primary font-medium hover:underline">View all</Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-6 py-3 text-xs font-medium text-text-muted uppercase">Title</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-text-muted uppercase">Status</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-text-muted uppercase">Priority</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-text-muted uppercase">Created</th>
                </tr>
              </thead>
              <tbody>
                {recentTasks.map(task => (
                  <tr key={task.id} className="border-b border-border last:border-0 hover:bg-surface-alt transition-colors">
                    <td className="px-6 py-3">
                      <Link to={`/tasks/${task.id}`} className="text-sm font-medium text-primary hover:underline">
                        {task.title}
                      </Link>
                    </td>
                    <td className="px-6 py-3"><StatusBadge status={task.status} /></td>
                    <td className="px-6 py-3"><PriorityBadge priority={task.priority} /></td>
                    <td className="px-6 py-3 text-sm text-text-muted">
                      {new Date(task.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
                {recentTasks.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-6 py-8 text-center text-sm text-text-muted">
                      No tasks yet. Create your first task!
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}
