import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Register() {
  const [form, setForm] = useState({ username: '', email: '', password: '', password2: '', department: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (form.password !== form.password2) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      await register(form);
      navigate('/');
    } catch (err) {
      const data = err.response?.data;
      if (data) {
        const messages = Object.values(data).flat().join(' ');
        setError(messages || 'Registration failed.');
      } else {
        setError('Registration failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-alt px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-text-main">
            <span className="text-primary">Task</span> Approval
          </h1>
          <p className="text-sm text-text-muted mt-2">Create your staff account</p>
        </div>

        <div className="bg-surface rounded-[12px] border border-border p-6 shadow-card">
          {error && (
            <div className="mb-4 px-3 py-2 bg-danger/10 text-danger text-sm rounded-lg">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-main mb-1.5">Username</label>
              <input name="username" value={form.username} onChange={handleChange} required
                className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-text-main text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none transition"
                placeholder="Choose a username" />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-main mb-1.5">Email</label>
              <input name="email" type="email" value={form.email} onChange={handleChange} required
                className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-text-main text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none transition"
                placeholder="your@email.com" />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-main mb-1.5">Department</label>
              <input name="department" value={form.department} onChange={handleChange}
                className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-text-main text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none transition"
                placeholder="e.g. Engineering" />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-main mb-1.5">Password</label>
              <input name="password" type="password" value={form.password} onChange={handleChange} required
                className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-text-main text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none transition"
                placeholder="Create a password" />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-main mb-1.5">Confirm Password</label>
              <input name="password2" type="password" value={form.password2} onChange={handleChange} required
                className="w-full px-3 py-2 rounded-lg border border-border bg-surface text-text-main text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none transition"
                placeholder="Confirm password" />
            </div>
            <button type="submit" disabled={loading}
              className="w-full py-2.5 bg-primary text-white text-sm font-semibold rounded-lg hover:bg-primary-dark transition-colors disabled:opacity-50 cursor-pointer">
              {loading ? 'Creating account...' : 'Create Account'}
            </button>
          </form>

          <p className="text-center text-sm text-text-muted mt-5">
            Already have an account?{' '}
            <Link to="/login" className="text-primary font-medium hover:underline">Sign In</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
