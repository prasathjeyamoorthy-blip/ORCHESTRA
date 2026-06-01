const BASE = 'http://localhost:4000/api/auth';

export async function apiPost(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include', // sends/receives cookies
    body: JSON.stringify(body),
  });
  return res.json();
}