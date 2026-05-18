const API = 'http://localhost:5050';

export async function fetchScenarios() {
  const r = await fetch(`${API}/scenarios`);
  return r.json();
}

export async function fetchSolve(config) {
  const r = await fetch(`${API}/solve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  return r.json();
}
