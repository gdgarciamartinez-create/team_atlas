// src/api.js

// Base de la API usando el proxy de Vite
export const API_BASE = "/api";

/**
 * Check de salud del backend
 */
export async function checkHealth() {
  const res = await fetch(`${API_BASE}/health`);

  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }

  return res.json();
}
