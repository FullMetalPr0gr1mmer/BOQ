// src/components/LoginForm.jsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function AuthForm({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showRegister, setShowRegister] = useState(false);
  const [regUsername, setRegUsername] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [error, setError] = useState('');
  const [regError, setRegError] = useState('');
  const [regSuccess, setRegSuccess] = useState('');

  const navigate = useNavigate();
  const VITE_API_URL = import.meta.env.VITE_API_URL;

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const res = await fetch(`${VITE_API_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
      });
      const data = await res.json();
      if (data.access_token) {
        onLogin({ token: data.access_token, user: { role: data.role, username } });
        navigate('/*');
      } else {
        setError(data.detail || 'Login failed');
      }
    } catch (err) {
      setError('Login error');
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setRegError('');
    setRegSuccess('');
    try {
      const res = await fetch(`${VITE_API_URL}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: regUsername,
          email: regEmail,
          password: regPassword,
        })
      });
      const data = await res.json();
      if (res.ok) {
        setRegSuccess('Registration successful! You can now log in.');
      } else {
        setRegError(data.detail || 'Registration failed');
      }
    } catch (err) {
      setRegError('Registration error');
    }
  };

  return (
    <div className="auth-container">
      <h1 className="title">Project Managment</h1>
      <form onSubmit={showRegister ? handleRegister : handleLogin} className="auth-form">
        <h2 style={{ float: 'left' }}>{showRegister ? 'Register' : 'Login'}</h2>
        {error && <div className="error">{error}</div>}
        {regError && <div className="error">{regError}</div>}
        {regSuccess && <div className="success">{regSuccess}</div>}
        {showRegister ? (
          <>
            <input type="text" placeholder="Username" value={regUsername} onChange={e => setRegUsername(e.target.value)} required />
            <input type="email" placeholder="Email" value={regEmail} onChange={e => setRegEmail(e.target.value)} required />
            <input type="password" placeholder="Password" value={regPassword} onChange={e => setRegPassword(e.target.value)} required />
          </>
        ) : (
          <>
            <input type="text" placeholder="Username" value={username} onChange={e => setUsername(e.target.value)} required />
            <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} required />
          </>
        )}
        <button type="submit">{showRegister ? 'Register' : 'Login'}</button>
        <p className="switch-link" onClick={() => setShowRegister(!showRegister)}>
          {showRegister ? 'Already have an account? Login' : 'No account? Register'}
        </p>
      </form>
    </div>
  );
}