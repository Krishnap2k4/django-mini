import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';
import Topbar from '../components/layout/Topbar';

export default function TaskCreate() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [managers, setManagers] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    title: '', description: '', priority: 'MEDIUM', due_date: '', assignees: [], reviewer: '',
  });

  // Fetch users for assignees and reviewer dropdowns
  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const res = await api.get('/auth/users/');
        const allUsers = res.data.results || res.data;
        setManagers(allUsers.filter(u => u.role === 'MANAGER' || u.role === 'SUPERADMIN'));
        setUsers(allUsers);
      } catch (err) {
        console.error('Failed to fetch users:', err);
      }
    };
    fetchUsers();
  }, []);

  const handleChange = (e) => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const payload = {
        title: form.title,
        description: form.description,
        priority: form.priority,
      };
      if (form.due_date) payload.due_date = form.due_date;
      if (form.reviewer) payload.reviewer = parseInt(form.reviewer);
      if (form.assignees && form.assignees.length > 0) {
        payload.assignees = form.assignees.map(id => parseInt(id));
      }

      const res = await api.post('/tasks/', payload);
      navigate(`/tasks/${res.data.id}`);
    } catch (err) {
      const data = err.response?.data;
      if (data) {
        const messages = Object.entries(data).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`).join('. ');
        setError(messages);
      } else {
        setError('Failed to create task.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Topbar title="Create Task" subtitle="Add a new task to the system" />
      <div className="p-8 max-w-2xl">
        <div className="bg-surface rounded-[12px] border border-border shadow-card p-6">
          {error && (
            <div className="mb-4 px-3 py-2 bg-danger/10 text-danger text-sm rounded-lg">{error}</div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-text-main mb-1.5">Title *</label>
              <input name="title" value={form.title} onChange={handleChange} required
                className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-text-main text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none transition"
                placeholder="Task title" />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-main mb-1.5">Description</label>
              <textarea name="description" value={form.description} onChange={handleChange} rows={4}
                className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-text-main text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none transition resize-none"
                placeholder="Describe the task..." />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-text-main mb-1.5">Priority</label>
                <select name="priority" value={form.priority} onChange={handleChange}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-text-main text-sm focus:border-primary outline-none cursor-pointer">
                  <option value="LOW">Low</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HIGH">High</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-text-main mb-1.5">Due Date</label>
                <input name="due_date" type="date" value={form.due_date} onChange={handleChange}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-text-main text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none transition" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-main mb-1.5">Assignees</label>
              <select name="assignees" multiple value={form.assignees} 
                onChange={e => setForm(prev => ({ ...prev, assignees: Array.from(e.target.selectedOptions, option => option.value) }))}
                className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-text-main text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none transition cursor-pointer"
                size={3}>
                {users.map(u => (
                  <option key={u.id} value={u.id}>{u.username} ({u.role})</option>
                ))}
              </select>
              <p className="text-xs text-text-muted mt-1">Hold Ctrl/Cmd to select multiple staff members.</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-main mb-1.5">Reviewer (Manager)</label>
              <select name="reviewer" value={form.reviewer} onChange={handleChange}
                className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-text-main text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none transition cursor-pointer">
                <option value="">-- Unassigned --</option>
                {managers.map(m => (
                  <option key={m.id} value={m.id}>{m.username} ({m.role})</option>
                ))}
              </select>
              <p className="text-xs text-text-muted mt-1">Assign a manager to review this task.</p>
            </div>

            <div className="flex items-center gap-3 pt-2">
              <button type="submit" disabled={loading}
                className="px-5 py-2.5 bg-primary text-white text-sm font-semibold rounded-lg hover:bg-primary-dark transition-colors disabled:opacity-50 cursor-pointer">
                {loading ? 'Creating...' : 'Create Task'}
              </button>
              <button type="button" onClick={() => navigate('/tasks')}
                className="px-5 py-2.5 border border-border text-sm font-medium text-text-muted rounded-lg hover:bg-surface-alt transition-colors cursor-pointer">
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
