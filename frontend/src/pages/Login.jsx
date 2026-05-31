import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function Login() {
  const [form, setForm]   = useState({ email: '', password: '' });
  const navigate          = useNavigate();
  const { login, loading, error } = useAuth();

  async function handleSubmit(e) {
    e.preventDefault();
    const ok = await login(form.email, form.password);
    if (ok) navigate('/dashboard');
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12" style={{ background: '#050508' }}>
      <div className="w-full max-w-sm">
        <h2 className="text-2xl font-bold text-white mb-6 text-center">Sign in</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="email" placeholder="Email" required
            value={form.email}
            onChange={e => setForm({ ...form, email: e.target.value })}
            className="block w-full px-4 py-3 rounded-xl bg-white/[0.05] border border-white/[0.1] text-white placeholder-white/30 outline-none focus:border-white/30 transition-colors text-sm"
          />
          <input
            type="password" placeholder="Password" required
            value={form.password}
            onChange={e => setForm({ ...form, password: e.target.value })}
            className="block w-full px-4 py-3 rounded-xl bg-white/[0.05] border border-white/[0.1] text-white placeholder-white/30 outline-none focus:border-white/30 transition-colors text-sm"
          />
          {error && <p className="text-rose-400 text-sm">{error}</p>}
          <button
            type="submit" disabled={loading}
            className="w-full py-3 rounded-xl bg-white text-black font-semibold text-sm hover:bg-white/90 disabled:opacity-50 transition-all"
          >
            {loading ? 'Signing in…' : 'Login'}
          </button>
        </form>
      </div>
    </div>
  );
}
