import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Bot, User, Lock, AlertCircle, Loader, Eye, EyeOff } from 'lucide-react';
import { loginUser } from '../services/chatService';
import './Auth.css';

function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');

    const trimmedUser = username.trim();
    if (!trimmedUser || !password) {
      setError('Please enter your username and password.');
      return;
    }

    setLoading(true);

    const attemptLogin = async (isRetry = false) => {
      try {
        const data = await loginUser(trimmedUser, password);
        localStorage.setItem('authToken', data.access_token);
        localStorage.setItem('chatUsername', data.user.username);
        navigate('/chat');
      } catch (err) {
        const isNetworkOrTimeout =
          err?.code === 'ECONNABORTED' ||
          err?.message?.includes('timeout') ||
          err?.message === 'Network Error' ||
          !err?.response;

        // Perform a single automatic retry on cold-start/network failure
        if (isNetworkOrTimeout && !isRetry) {
          setError('Server is waking up, retrying...');
          return attemptLogin(true);
        }

        if (isNetworkOrTimeout) {
          setError('The server is waking up. Please try again in a moment.');
        } else if (err?.response?.status === 401) {
          setError('Invalid username or password.');
        } else if (err?.response?.status === 429) {
          setError('Too many login attempts. Please wait a moment and try again.');
        } else {
          const serverError = err?.response?.data?.error;
          setError(typeof serverError === 'string' ? serverError : 'Unable to connect to the server. Please try again.');
        }
      } finally {
        if (!isRetry) {
          setLoading(false);
        }
      }
    };

    await attemptLogin(false);
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <Link to="/" className="auth-logo-link" aria-label="Go to homepage">
            <div className="auth-icon">
              <Bot size={36} />
            </div>
          </Link>
          <h1>Welcome back</h1>
          <p>Continue to your AI workspace.</p>
        </div>

        {error && (
          <div className="auth-error" role="alert" aria-live="assertive">
            <AlertCircle size={16} className="auth-error-icon" />
            <span>{error}</span>
          </div>
        )}

        <form className="auth-form" onSubmit={handleLogin} noValidate>
          <div className="auth-input-group">
            <label htmlFor="login-username">Username</label>
            <div className="auth-input-wrapper">
              <User size={16} className="auth-input-icon" aria-hidden="true" />
              <input
                id="login-username"
                name="username"
                type="text"
                autoComplete="username"
                className="auth-input"
                placeholder="Enter your username"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
                disabled={loading}
                autoFocus
              />
            </div>
          </div>

          <div className="auth-input-group">
            <label htmlFor="login-password">Password</label>
            <div className="auth-input-wrapper">
              <Lock size={16} className="auth-input-icon" aria-hidden="true" />
              <input
                id="login-password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                className="auth-input"
                placeholder="••••••••"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                disabled={loading}
              />
              <button
                type="button"
                className="password-toggle-btn"
                aria-label={showPassword ? "Hide password" : "Show password"}
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={0}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button type="submit" className="auth-button" disabled={loading}>
            {loading ? (
              <>
                <Loader size={16} className="spin" aria-hidden="true" />
                <span>Signing in...</span>
              </>
            ) : (
              <span>Sign In</span>
            )}
          </button>
        </form>

        <p className="auth-switch">
          Don't have an account?{' '}
          <Link to="/signup" className="auth-link">Sign up</Link>
        </p>
      </div>
    </div>
  );
}

export default Login;
