import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import api from '../api/axios';
import Topbar from '../components/layout/Topbar';
import StatusBadge from '../components/ui/StatusBadge';
import PriorityBadge from '../components/ui/PriorityBadge';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import EmptyState from '../components/ui/EmptyState';
import { useAuth } from '../context/AuthContext';

export default function TaskList() {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [nextCursor, setNextCursor] = useState(null);
  const [prevCursor, setPrevCursor] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth();

  const search = searchParams.get('search') || '';
  const status = searchParams.get('status') || '';
  const priority = searchParams.get('priority') || '';
  const view = searchParams.get('view') || '';

  const fetchTasks = async (cursorUrl = null) => {
    setLoading(true);
    try {
      let url = cursorUrl || '/tasks/?';
      if (!cursorUrl) {
        const params = new URLSearchParams();
        if (search) params.set('search', search);
        if (status) params.set('status', status);
        if (priority) params.set('priority', priority);
        
        // Map view to backend filter fields using user.id
        if (view === 'creator') params.set('creator', user?.id);
        else if (view === 'reviewer') params.set('reviewer', user?.id);
        else if (view === 'assignee') params.set('assignees', user?.id);

        url = `/tasks/?${params.toString()}`;
      }
      const res = await api.get(url);
      setTasks(res.data.results || []);
      setNextCursor(res.data.next);
      setPrevCursor(res.data.previous);
    } catch (err) {
      console.error('Failed to fetch tasks:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTasks(); }, [search, status, priority, view, user?.id]);

  const updateFilter = (key, value) => {
    const params = new URLSearchParams(searchParams);
    if (value) params.set(key, value);
    else params.delete(key);
    setSearchParams(params);
  };

  return (
    <>
      <Topbar title="Tasks" subtitle="Manage your tasks" />
      <div className="p-8">
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
          <div className="flex items-center gap-3 flex-wrap">
            {/* Search */}
            <div className="relative">
              <span className="material-icons-round absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-[18px]">search</span>
              <input
                type="text"
                defaultValue={search}
                onKeyDown={e => { if (e.key === 'Enter') updateFilter('search', e.target.value); }}
                placeholder="Search tasks..."
                className="pl-9 pr-3 py-2 rounded-lg border border-border bg-surface text-sm text-text-main w-[220px] focus:border-primary focus:ring-1 focus:ring-primary outline-none transition"
              />
            </div>

            {/* View Filter */}
            <select
              value={view}
              onChange={e => updateFilter('view', e.target.value)}
              className="px-3 py-2 rounded-lg border border-border bg-surface text-sm text-text-main focus:border-primary outline-none cursor-pointer"
            >
              <option value="">All My Tasks</option>
              <option value="creator">Created by Me</option>
              <option value="assignee">Assigned to Me</option>
              {(user?.role === 'MANAGER' || user?.role === 'SUPERADMIN') && (
                <option value="reviewer">Review Queue</option>
              )}
            </select>

            {/* Status Filter */}
            <select
              value={status}
              onChange={e => updateFilter('status', e.target.value)}
              className="px-3 py-2 rounded-lg border border-border bg-surface text-sm text-text-main focus:border-primary outline-none cursor-pointer"
            >
              <option value="">All Status</option>
              <option value="DRAFT">Draft</option>
              <option value="SUBMITTED">Submitted</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
            </select>

            {/* Priority Filter */}
            <select
              value={priority}
              onChange={e => updateFilter('priority', e.target.value)}
              className="px-3 py-2 rounded-lg border border-border bg-surface text-sm text-text-main focus:border-primary outline-none cursor-pointer"
            >
              <option value="">All Priority</option>
              <option value="LOW">Low</option>
              <option value="MEDIUM">Medium</option>
              <option value="HIGH">High</option>
            </select>
          </div>

          <Link
            to="/tasks/new"
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white text-sm font-semibold rounded-lg hover:bg-primary-dark transition-colors"
          >
            <span className="material-icons-round text-[18px]">add</span>
            New Task
          </Link>
        </div>

        {/* Table */}
        {loading ? <LoadingSpinner /> : tasks.length === 0 ? (
          <EmptyState icon="task_alt" message="No tasks found" />
        ) : (
          <div className="bg-surface rounded-[12px] border border-border overflow-hidden shadow-card">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-surface-alt">
                  <th className="text-left px-6 py-3 text-xs font-medium text-text-muted uppercase">Title</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-text-muted uppercase">Creator</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-text-muted uppercase">Status</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-text-muted uppercase">Priority</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-text-muted uppercase">Due Date</th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-text-muted uppercase">Created</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map(task => (
                  <tr key={task.id} className="border-b border-border last:border-0 hover:bg-surface-alt transition-colors">
                    <td className="px-6 py-3">
                      <Link to={`/tasks/${task.id}`} className="text-sm font-medium text-primary hover:underline">
                        {task.title}
                      </Link>
                    </td>
                    <td className="px-6 py-3 text-sm text-text-muted">{task.creator_name}</td>
                    <td className="px-6 py-3"><StatusBadge status={task.status} /></td>
                    <td className="px-6 py-3"><PriorityBadge priority={task.priority} /></td>
                    <td className="px-6 py-3 text-sm text-text-muted">
                      {task.due_date || '—'}
                    </td>
                    <td className="px-6 py-3 text-sm text-text-muted">
                      {new Date(task.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            <div className="flex items-center justify-between px-6 py-3 border-t border-border">
              <button
                onClick={() => prevCursor && fetchTasks(prevCursor)}
                disabled={!prevCursor}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg border border-border text-text-muted hover:text-text-main disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed transition-colors"
              >
                <span className="material-icons-round text-[16px]">chevron_left</span> Previous
              </button>
              <button
                onClick={() => nextCursor && fetchTasks(nextCursor)}
                disabled={!nextCursor}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg border border-border text-text-muted hover:text-text-main disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed transition-colors"
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
