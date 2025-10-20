import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiCall, setTransient } from '../api.js';
import './AuthForm.css';

export default function AuthForm({ onLogin }) {
  const [activeTab, setActiveTab] = useState('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [regUsername, setRegUsername] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [error, setError] = useState('');
  const [regError, setRegError] = useState('');
  const [regSuccess, setRegSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      const data = await apiCall('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`,
        skipAuth: true
      });
      if (data.access_token) {
        onLogin({ token: data.access_token, user: { role: data.role, username } });
        navigate('/*');
      } else {
        setTransient(setError, data.detail || 'Login failed');
      }
    } catch (err) {
      setTransient(setError, err.message || 'Login error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setRegError('');
    setRegSuccess('');
    setIsLoading(true);
    try {
      await apiCall('/register', {
        method: 'POST',
        body: JSON.stringify({
          username: regUsername,
          email: regEmail,
          password: regPassword,
        }),
        skipAuth: true
      });
      setTransient(setRegSuccess, 'Registration successful! You can now log in.');
      // Switch to login tab after successful registration
      setTimeout(() => {
        setActiveTab('login');
        setUsername(regUsername);
      }, 2000);
    } catch (err) {
      setTransient(setRegError, err.message || 'Registration failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-logo">
            <span className="auth-logo-text">NOKIA</span>
          </div>
          <h1 className="auth-title">Project Management</h1>
          <p className="auth-subtitle">Welcome back! Please enter your details.</p>
        </div>

        <div className="auth-body">
          <div className="auth-tabs">
            <button
              type="button"
              className={`auth-tab ${activeTab === 'login' ? 'active' : ''}`}
              onClick={() => setActiveTab('login')}
            >
              Login
            </button>
            <button
              type="button"
              className={`auth-tab ${activeTab === 'register' ? 'active' : ''}`}
              onClick={() => setActiveTab('register')}
            >
              Register
            </button>
          </div>

          {activeTab === 'login' ? (
            <form onSubmit={handleLogin} className="auth-form">
              {error && <div className="message-box error">{error}</div>}

              <div className="input-group">
                <label htmlFor="login-username">Username</label>
                <input
                  id="login-username"
                  type="text"
                  placeholder="Enter your username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  disabled={isLoading}
                />
              </div>

              <div className="input-group">
                <label htmlFor="login-password">Password</label>
                <input
                  id="login-password"
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={isLoading}
                />
              </div>

              <button
                type="submit"
                className={`auth-button ${isLoading ? 'loading' : ''}`}
                disabled={isLoading}
              >
                {isLoading ? '' : 'Sign In'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="auth-form">
              {regError && <div className="message-box error">{regError}</div>}
              {regSuccess && <div className="message-box success">{regSuccess}</div>}

              <div className="input-group">
                <label htmlFor="reg-username">Username</label>
                <input
                  id="reg-username"
                  type="text"
                  placeholder="Choose a username"
                  value={regUsername}
                  onChange={(e) => setRegUsername(e.target.value)}
                  required
                  disabled={isLoading}
                />
              </div>

              <div className="input-group">
                <label htmlFor="reg-email">Email</label>
                <input
                  id="reg-email"
                  type="email"
                  placeholder="Enter your email"
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  required
                  disabled={isLoading}
                />
              </div>

              <div className="input-group">
                <label htmlFor="reg-password">Password</label>
                <input
                  id="reg-password"
                  type="password"
                  placeholder="Create a password"
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  required
                  disabled={isLoading}
                />
              </div>

              <button
                type="submit"
                className={`auth-button ${isLoading ? 'loading' : ''}`}
                disabled={isLoading}
              >
                {isLoading ? '' : 'Create Account'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}