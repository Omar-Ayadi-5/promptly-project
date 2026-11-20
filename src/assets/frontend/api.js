// Vite variables are public. Provider credentials belong in the backend only.
export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? 'http://localhost:5000' : '')
).replace(/\/+$/, '');
