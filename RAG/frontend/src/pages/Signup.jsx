import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function Signup() {
  const [form, setForm] = useState({ email: '', password: '', confirm: '' });
  const [localError, setLocalError] = useState('');
  const navigate = useNavigate();
  const { register, loading, error } = useAuth();

  const passwordStrong = (p) =>
    p.length >= 8 && /[A-Z]/.test(p) && /[0-9]/.test(p) && /[^A-Za-z0-9]/.test(p);

  async function handleSubmit(e) {
    e.preventDefault();
    setLocalError('');

    if (!passwordStrong(form.password))
      return setLocalError('Password must be 8+ chars with uppercase, number, and symbol.');
    if (form.password !== form.confirm)
      return setLocalError('Passwords do not match.');

    const ok = await register(form.email, form.password);
    if (ok) navigate('/dashboard');
  }

  const displayError = localError || error;

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12" style={{ background: '#050508' }}>
      <div className="w-full max-w-sm">
        <h2 className="text-2xl font-bold text-white mb-6 text-center">Create account</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="email" placeholder="Email" required
            value={form.email}
            onChange={e => setForm({ ...form, email: e.target.value })}
            className="block w-full px-4 py-3 rounded-xl bg-white/[0.05] border border-white/[0.1] text-white placeholder-white/30 outline-none focus:border-white/30 transition-colors text-sm"
          />
          <input
            type="password" placeholder="Password (8+ chars, number, symbol)"
            required value={form.password}
            onChange={e => setForm({ ...form, password: e.target.value })}
            className="block w-full px-4 py-3 rounded-xl bg-white/[0.05] border border-white/[0.1] text-white placeholder-white/30 outline-none focus:border-white/30 transition-colors text-sm"
          />
          <input
            type="password" placeholder="Confirm password"
            required value={form.confirm}
            onChange={e => setForm({ ...form, confirm: e.target.value })}
            className="block w-full px-4 py-3 rounded-xl bg-white/[0.05] border border-white/[0.1] text-white placeholder-white/30 outline-none focus:border-white/30 transition-colors text-sm"
          />
          {displayError && <p className="text-rose-400 text-sm">{displayError}</p>}
          <button
            type="submit" disabled={loading}
            className="w-full py-3 rounded-xl bg-white text-black font-semibold text-sm hover:bg-white/90 disabled:opacity-50 transition-all"
          >
            {loading ? 'Creating account…' : 'Sign up'}
          </button>
        </form>
      </div>
    </div>
  );
}
