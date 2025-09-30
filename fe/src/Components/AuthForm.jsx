import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiCall, setTransient } from '../api.js';

// Changed 'handleLogin' to 'onLogin' to avoid prop name conflict
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

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const data = await apiCall('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`,
        skipAuth: true  // Skip auth header for login
      });
      if (data.access_token) {
        // Now calling the prop passed from the parent component
        onLogin({ token: data.access_token, user: { role: data.role, username } });
        navigate('/*');
      } else {
        setTransient(setError, data.detail || 'Login failed');
      }
    } catch (err) {
      setTransient(setError, err.message || 'Login error');
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setRegError('');
    setRegSuccess('');
    try {
      await apiCall('/register', {
        method: 'POST',
        body: JSON.stringify({
          username: regUsername,
          email: regEmail,
          password: regPassword,
        }),
        skipAuth: true  // Skip auth header for registration
      });
      setTransient(setRegSuccess, 'Registration successful! You can now log in.');
    } catch (err) {
      setTransient(setRegError, err.message || 'Registration failed');
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