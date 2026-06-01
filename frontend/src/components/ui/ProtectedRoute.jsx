/**
 * ProtectedRoute.jsx
 *
 * Wraps any route that requires authentication.
 * Redirects unauthenticated users to /login.
 *
 * Usage (in your router):
 *   <Route path="/dashboard" element={
 *     <ProtectedRoute user={user} loading={loading}>
 *       <Dashboard />
 *     </ProtectedRoute>
 *   } />
 *
 * Props:
 *   user     — the Supabase user object (null if not logged in)
 *   loading  — true while auth state is being determined
 *   children — the protected page/component to render
 *   redirectTo — (optional) path to redirect to, defaults to "/login"
 */
import { Navigate } from 'react-router-dom'

export function ProtectedRoute({ user, loading, children, redirectTo = '/login' }) {
  // Still determining auth state — render nothing to avoid flash
  if (loading) return null

  // Not authenticated — redirect to login
  if (!user) return <Navigate to={redirectTo} replace />

  // Authenticated — render the protected content
  return children
}
