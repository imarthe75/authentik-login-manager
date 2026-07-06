import React, { useEffect, useState } from 'react';
import { authApi } from '../api/authApi';

export const AdminLoginGate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [checking, setChecking] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [adminKey, setAdminKey] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    authApi.status()
      .then(setAuthenticated)
      .finally(() => setChecking(false));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await authApi.login(adminKey);
      setAuthenticated(true);
    } catch (err: any) {
      setError(err?.message || 'Error de autenticación');
    } finally {
      setSubmitting(false);
      setAdminKey('');
    }
  };

  if (checking) {
    return (
      <div className="w-screen h-screen flex items-center justify-center bg-gray-100">
        <div className="text-gray-400 text-sm">Verificando sesión…</div>
      </div>
    );
  }

  if (!authenticated) {
    return (
      <div className="w-screen h-screen flex items-center justify-center bg-gray-100">
        <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-lg p-8 w-full max-w-sm">
          <h1 className="text-lg font-bold text-gray-800 mb-1">Authentik Login Manager</h1>
          <p className="text-xs text-gray-500 mb-4">Acceso administrativo requerido</p>
          <input
            type="password"
            autoFocus
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
            placeholder="Clave administrativa"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {error && <p className="text-red-600 text-xs mb-3">{error}</p>}
          <button
            type="submit"
            disabled={submitting || !adminKey}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold rounded-lg py-2 transition-colors"
          >
            {submitting ? 'Verificando…' : 'Entrar'}
          </button>
        </form>
      </div>
    );
  }

  return <>{children}</>;
};
