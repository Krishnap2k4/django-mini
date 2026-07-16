import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';
import Topbar from '../components/layout/Topbar';
import StatusBadge from '../components/ui/StatusBadge';
import PriorityBadge from '../components/ui/PriorityBadge';
import Modal from '../components/ui/Modal';
import LoadingSpinner from '../components/ui/LoadingSpinner';

export default function TaskDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [task, setTask] = useState(null);
  const [comments, setComments] = useState([]);
  const [attachments, setAttachments] = useState([]);
  const [history, setHistory] = useState([]);
  const [activeTab, setActiveTab] = useState('comments');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState('');
  const [error, setError] = useState('');
  const [managers, setManagers] = useState([]);

  // Comment form
  const [commentText, setCommentText] = useState('');

  // Approve/Reject modal
  const [modalType, setModalType] = useState(null); // 'approve' | 'reject'
  const [remarks, setRemarks] = useState('');

  // Assign reviewer
  const [reviewerId, setReviewerId] = useState('');
  const [showAssignForm, setShowAssignForm] = useState(false);

  const fetchTask = async () => {
    try {
      const [taskRes, commentsRes, attachmentsRes, historyRes, usersRes] = await Promise.all([
        api.get(`/tasks/${id}/`),
        api.get(`/tasks/${id}/comments/`),
        api.get(`/tasks/${id}/attachments/`),
        api.get(`/tasks/${id}/history/`),
        api.get('/auth/users/?role=MANAGER'),
      ]);
      setTask(taskRes.data);
      setComments(commentsRes.data.results || commentsRes.data || []);
      setAttachments(attachmentsRes.data.results || attachmentsRes.data || []);
      setHistory(historyRes.data.results || historyRes.data || []);
      setManagers(usersRes.data.results || usersRes.data || []);
    } catch (err) {
      setError('Failed to load task data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTask(); }, [id]);

  const isCreator = task && task.creator === user?.id;
  const isAssignee = task && task.assignees?.includes(user?.id);
  const isReviewer = task && task.reviewer === user?.id;

  // Workflow actions
  const handleSubmitTask = async () => {
    setActionLoading('submit');
    try {
      await api.post(`/tasks/${id}/submit/`);
      await fetchTask();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit task.');
    }
    setActionLoading('');
  };

  const handleApproveReject = async () => {
    setActionLoading(modalType);
    try {
      await api.post(`/tasks/${id}/${modalType}/`, { remarks });
      setModalType(null);
      setRemarks('');
      await fetchTask();
    } catch (err) {
      setError(err.response?.data?.detail || `Failed to ${modalType} task.`);
    }
    setActionLoading('');
  };

  const handleRevert = async () => {
    setActionLoading('revert');
    try {
      await api.post(`/tasks/${id}/revert/`);
      await fetchTask();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to revert task.');
    }
    setActionLoading('');
  };

  const handleAssignReviewer = async (e) => {
    e.preventDefault();
    setActionLoading('assign');
    try {
      await api.post(`/tasks/${id}/assign_reviewer/`, { reviewer: parseInt(reviewerId) });
      setShowAssignForm(false);
      setReviewerId('');
      await fetchTask();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to assign reviewer.');
    }
    setActionLoading('');
  };

  // Comments
  const handleAddComment = async (e) => {
    e.preventDefault();
    if (!commentText.trim()) return;
    try {
      await api.post(`/tasks/${id}/comments/`, { content: commentText });
      setCommentText('');
      const res = await api.get(`/tasks/${id}/comments/`);
      setComments(res.data.results || res.data || []);
    } catch (err) {
      setError('Failed to add comment.');
    }
  };

  // Attachments
  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      await api.post(`/tasks/${id}/attachments/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const res = await api.get(`/tasks/${id}/attachments/`);
      setAttachments(res.data.results || res.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || err.response?.data?.file?.[0] || 'Failed to upload file.');
    }
    e.target.value = '';
  };

  if (loading) return (
    <>
      <Topbar title="Task Detail" />
      <LoadingSpinner />
    </>
  );

  if (!task) return (
    <>
      <Topbar title="Task Detail" />
      <div className="p-8 text-center text-text-muted">{error || 'Task not found.'}</div>
    </>
  );

  const isTerminal = task.status === 'APPROVED';

  return (
    <>
      <Topbar title={task.title} subtitle={`Task #${task.id}`} />
      <div className="p-8">
        {error && (
          <div className="mb-4 px-4 py-2 bg-danger/10 text-danger text-sm rounded-lg">{error}</div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Description Card */}
            <div className="bg-surface rounded-[12px] border border-border shadow-card p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <StatusBadge status={task.status} />
                  <PriorityBadge priority={task.priority} />
                </div>
                {isCreator && task.status === 'DRAFT' && (
                  <Link to={`/tasks/${id}/edit`}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium border border-border rounded-lg text-text-muted hover:text-text-main hover:bg-surface-alt transition-colors">
                    <span className="material-icons-round text-[16px]">edit</span> Edit
                  </Link>
                )}
              </div>
              <p className="text-sm text-text-main whitespace-pre-wrap leading-relaxed">
                {task.description || 'No description provided.'}
              </p>
            </div>

            {/* Workflow Actions */}
            {!isTerminal && (
              <div className="bg-surface rounded-[12px] border border-border shadow-card p-6">
                <h3 className="text-sm font-semibold text-text-main mb-4">Workflow Actions</h3>
                <div className="flex items-center gap-3 flex-wrap">
                  {/* Submit: Creator/Assignee when DRAFT */}
                  {task.status === 'DRAFT' && (isCreator || isAssignee) && (
                    <button onClick={handleSubmitTask} disabled={actionLoading === 'submit'}
                      className="inline-flex items-center gap-1.5 px-4 py-2 bg-info text-white text-sm font-semibold rounded-lg hover:bg-info/90 transition-colors disabled:opacity-50 cursor-pointer">
                      <span className="material-icons-round text-[16px]">send</span>
                      {actionLoading === 'submit' ? 'Submitting...' : 'Submit for Review'}
                    </button>
                  )}

                  {/* Approve/Reject: Reviewer when SUBMITTED */}
                  {task.status === 'SUBMITTED' && (isReviewer || user?.role === 'SUPERADMIN') && (
                    <>
                      <button onClick={() => setModalType('approve')}
                        className="inline-flex items-center gap-1.5 px-4 py-2 bg-accent text-white text-sm font-semibold rounded-lg hover:bg-accent/90 transition-colors cursor-pointer">
                        <span className="material-icons-round text-[16px]">check_circle</span> Approve
                      </button>
                      <button onClick={() => setModalType('reject')}
                        className="inline-flex items-center gap-1.5 px-4 py-2 bg-danger text-white text-sm font-semibold rounded-lg hover:bg-danger/90 transition-colors cursor-pointer">
                        <span className="material-icons-round text-[16px]">cancel</span> Reject
                      </button>
                    </>
                  )}

                  {/* Revert: Creator/Assignee when REJECTED */}
                  {task.status === 'REJECTED' && (isCreator || isAssignee) && (
                    <button onClick={handleRevert} disabled={actionLoading === 'revert'}
                      className="inline-flex items-center gap-1.5 px-4 py-2 bg-warning text-white text-sm font-semibold rounded-lg hover:bg-warning/90 transition-colors disabled:opacity-50 cursor-pointer">
                      <span className="material-icons-round text-[16px]">replay</span>
                      {actionLoading === 'revert' ? 'Reverting...' : 'Revert to Draft'}
                    </button>
                  )}

                  {/* Assign Reviewer: Creator when DRAFT/SUBMITTED */}
                  {(task.status === 'DRAFT' || task.status === 'SUBMITTED') && isCreator && (
                    <button onClick={() => setShowAssignForm(!showAssignForm)}
                      className="inline-flex items-center gap-1.5 px-4 py-2 border border-border text-sm font-medium text-text-muted rounded-lg hover:bg-surface-alt transition-colors cursor-pointer">
                      <span className="material-icons-round text-[16px]">person_add</span>
                      {task.reviewer ? 'Change Reviewer' : 'Assign Reviewer'}
                    </button>
                  )}
                </div>

                {/* Assign Reviewer Form */}
                {showAssignForm && (
                  <form onSubmit={handleAssignReviewer} className="mt-4 flex items-center gap-3">
                    <select value={reviewerId} onChange={e => setReviewerId(e.target.value)} required
                      className="px-3 py-2 rounded-lg border border-border bg-surface text-sm text-text-main w-[180px] focus:border-primary outline-none cursor-pointer">
                      <option value="">Select Reviewer...</option>
                      {managers.map(m => (
                        <option key={m.id} value={m.id}>{m.username}</option>
                      ))}
                    </select>
                    <button type="submit" disabled={actionLoading === 'assign' || !reviewerId}
                      className="px-4 py-2 bg-primary text-white text-sm font-semibold rounded-lg hover:bg-primary-dark transition-colors disabled:opacity-50 cursor-pointer">
                      {actionLoading === 'assign' ? 'Assigning...' : 'Assign'}
                    </button>
                  </form>
                )}
              </div>
            )}

            {/* Tabs: Comments / Attachments / History */}
            <div className="bg-surface rounded-[12px] border border-border shadow-card overflow-hidden">
              <div className="flex border-b border-border">
                {['comments', 'attachments', 'history'].map(tab => (
                  <button key={tab} onClick={() => setActiveTab(tab)}
                    className={`px-5 py-3 text-sm font-medium capitalize cursor-pointer transition-colors ${
                      activeTab === tab ? 'text-primary border-b-2 border-primary' : 'text-text-muted hover:text-text-main'
                    }`}>
                    {tab} {tab === 'comments' ? `(${comments.length})` : tab === 'attachments' ? `(${attachments.length})` : `(${history.length})`}
                  </button>
                ))}
              </div>

              <div className="p-5">
                {/* Comments Tab */}
                {activeTab === 'comments' && (
                  <div className="space-y-4">
                    {!isTerminal && (
                      <form onSubmit={handleAddComment} className="flex gap-3">
                        <input value={commentText} onChange={e => setCommentText(e.target.value)}
                          placeholder="Write a comment..." required
                          className="flex-1 px-3 py-2 rounded-lg border border-border bg-surface text-sm text-text-main focus:border-primary outline-none" />
                        <button type="submit"
                          className="px-4 py-2 bg-primary text-white text-sm font-semibold rounded-lg hover:bg-primary-dark transition-colors cursor-pointer">
                          Post
                        </button>
                      </form>
                    )}
                    {comments.length === 0 ? (
                      <p className="text-sm text-text-muted py-4 text-center">No comments yet.</p>
                    ) : (
                      comments.map(c => (
                        <div key={c.id} className="flex gap-3">
                          <div className="w-7 h-7 rounded-full bg-primary-light/20 text-primary text-xs font-semibold flex items-center justify-center shrink-0 mt-0.5">
                            {c.author_name?.[0]?.toUpperCase() || '?'}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium text-text-main">{c.author_name}</span>
                              <span className="text-xs text-text-muted">{new Date(c.created_at).toLocaleString()}</span>
                            </div>
                            <p className="text-sm text-text-main mt-1">{c.content}</p>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {/* Attachments Tab */}
                {activeTab === 'attachments' && (
                  <div className="space-y-4">
                    {!isTerminal && (isCreator || isAssignee) && (
                      <label className="inline-flex items-center gap-2 px-4 py-2 border border-border text-sm font-medium text-text-muted rounded-lg hover:bg-surface-alt transition-colors cursor-pointer">
                        <span className="material-icons-round text-[16px]">upload_file</span>
                        Upload File
                        <input type="file" className="hidden" onChange={handleUpload} />
                      </label>
                    )}
                    {attachments.length === 0 ? (
                      <p className="text-sm text-text-muted py-4 text-center">No attachments yet.</p>
                    ) : (
                      attachments.map(a => (
                        <div key={a.id} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                          <div className="flex items-center gap-2">
                            <span className="material-icons-round text-text-muted text-[18px]">attach_file</span>
                            <div>
                              <p className="text-sm font-medium text-text-main">{a.original_filename}</p>
                              <p className="text-xs text-text-muted">{(a.file_size / 1024).toFixed(1)} KB</p>
                            </div>
                          </div>
                          <a href={a.file} target="_blank" rel="noopener noreferrer"
                            className="text-primary text-sm font-medium hover:underline">Download</a>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {/* History Tab */}
                {activeTab === 'history' && (
                  <div className="space-y-3">
                    {history.length === 0 ? (
                      <p className="text-sm text-text-muted py-4 text-center">No status changes yet.</p>
                    ) : (
                      history.map(h => (
                        <div key={h.id} className="flex items-start gap-3 py-2 border-b border-border last:border-0">
                          <span className="material-icons-round text-info text-[18px] mt-0.5">history</span>
                          <div>
                            <p className="text-sm text-text-main">
                              <span className="font-medium">{h.changed_by_name}</span> changed status from{' '}
                              <StatusBadge status={h.from_status || 'DRAFT'} /> to <StatusBadge status={h.to_status} />
                            </p>
                            {h.remarks && <p className="text-xs text-text-muted mt-1">"{h.remarks}"</p>}
                            <p className="text-xs text-text-muted mt-0.5">{new Date(h.changed_at).toLocaleString()}</p>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Sidebar Info */}
          <div className="space-y-6">
            <div className="bg-surface rounded-[12px] border border-border shadow-card p-5 space-y-4">
              <h3 className="text-sm font-semibold text-text-main">Details</h3>
              <div className="space-y-3">
                <div>
                  <p className="text-xs text-text-muted">Creator</p>
                  <p className="text-sm font-medium text-text-main">{task.creator_name}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted">Reviewer</p>
                  <p className="text-sm font-medium text-text-main">{task.reviewer_name || 'Not assigned'}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted">Assignees</p>
                  <p className="text-sm font-medium text-text-main">
                    {task.assignees_names?.length > 0 ? task.assignees_names.join(', ') : 'None'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-text-muted">Due Date</p>
                  <p className="text-sm font-medium text-text-main">{task.due_date || 'No due date'}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted">Created</p>
                  <p className="text-sm font-medium text-text-main">{new Date(task.created_at).toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted">Last Updated</p>
                  <p className="text-sm font-medium text-text-main">{new Date(task.updated_at).toLocaleString()}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Approve/Reject Modal */}
      <Modal isOpen={!!modalType} onClose={() => { setModalType(null); setRemarks(''); }}
        title={modalType === 'approve' ? 'Approve Task' : 'Reject Task'}>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-main mb-1.5">Remarks (optional)</label>
            <textarea value={remarks} onChange={e => setRemarks(e.target.value)} rows={3}
              className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-text-main text-sm focus:border-primary outline-none resize-none"
              placeholder={`Reason for ${modalType}...`} />
          </div>
          <div className="flex justify-end gap-3">
            <button onClick={() => { setModalType(null); setRemarks(''); }}
              className="px-4 py-2 border border-border text-sm font-medium text-text-muted rounded-lg hover:bg-surface-alt transition-colors cursor-pointer">
              Cancel
            </button>
            <button onClick={handleApproveReject} disabled={!!actionLoading}
              className={`px-4 py-2 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50 cursor-pointer ${
                modalType === 'approve' ? 'bg-accent hover:bg-accent/90' : 'bg-danger hover:bg-danger/90'
              }`}>
              {actionLoading ? 'Processing...' : modalType === 'approve' ? 'Approve' : 'Reject'}
            </button>
          </div>
        </div>
      </Modal>
    </>
  );
}
