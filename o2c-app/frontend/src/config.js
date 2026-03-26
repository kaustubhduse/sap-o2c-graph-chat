/**
 * Backend API base URL. Set VITE_API_URL in .env (e.g. Render URL).
 * Vite only exposes env vars prefixed with VITE_.
 */
export const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(
  /\/$/,
  ''
);
