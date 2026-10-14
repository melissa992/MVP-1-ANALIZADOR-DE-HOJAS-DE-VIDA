import { useState } from 'react';
import './Login.css';

export default function Login({ onLogin, loading, error }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (event) => {
    event.preventDefault();
    onLogin(email.trim(), password);
  };

  return (
    <main className="login-shell">
      <section className="login-card" aria-labelledby="login-title">
        <a className="login-brand" href="#login" aria-label="CV-Match AI">
          <span className="login-brand-mark" aria-hidden="true">CV</span>
          <span>
            <strong>CV-Match</strong>
            <small>Talent intelligence</small>
          </span>
        </a>
        <p className="login-eyebrow">PLATAFORMA DE SELECCIÓN</p>
        <h1 id="login-title">Inicia sesión</h1>
        <p className="login-description">Accede de forma segura a tu espacio de gestión de talento.</p>

        <form className="login-form" onSubmit={handleSubmit}>
          <label htmlFor="login-email">Correo electrónico</label>
          <input
            id="login-email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="nombre@empresa.com"
            required
            maxLength={254}
          />

          <label htmlFor="login-password">Contraseña</label>
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Ingresa tu contraseña"
            required
            maxLength={72}
          />

          {error && <p className="login-error" role="alert">{error}</p>}

          <button type="submit" disabled={loading}>
            {loading ? 'Validando acceso...' : 'Ingresar'}
          </button>
        </form>
        <p className="login-security-note">
          <span aria-hidden="true">●</span>
          Acceso privado para usuarios autorizados
        </p>
      </section>
    </main>
  );
}
