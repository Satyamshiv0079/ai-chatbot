import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Bot, User, Mail, Lock, AlertCircle, Loader, Eye, EyeOff } from 'lucide-react';
import { registerUser } from '../services/chatService';
import './Auth.css';

function Signup() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSignup = async (e) => {
    e.preventDefault();
    setError('');

    const trimmedUser = username.trim();
    if (!trimmedUser || !password) {
      setError('Username and password are required.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    setLoading(true);

    const attemptSignup = async (isRetry = false) => {
      try {
        const data = await registerUser(trimmedUser, password, email.trim() || undefined);
        localStorage.setItem('authToken', data.access_token);
        localStorage.setItem('chatUsername', data.user.username);
        navigate('/chat');
      } catch (err) {
        const isNetworkOrTimeout =
          err?.code === 'ECONNABORTED' ||
          err?.message?.includes('timeout') ||
          err?.message === 'Network Error' ||
          !err?.response;

        if (isNetworkOrTimeout && !isRetry) {
          setError('Server is waking up, retrying...');
          return attemptSignup(true);
        }

        if (isNetworkOrTimeout) {
          setError('The server is waking up. Please try again in a moment.');
        } else if (err?.response?.status === 409) {
          setError('Username already taken. Please choose another.');
        } else if (err?.response?.status === 429) {
          setError('Too many attempts. Please try again shortly.');
        } else {
          const serverError = err?.response?.data?.error;
          setError(typeof serverError === 'string' ? serverError : 'Registration failed. Please try again.');
        }
      } finally {
        if (!isRetry) {
          setLoading(false);
        }
      }
    };

    await attemptSignup(false);
  };

  // Password strength calculation
  const getPasswordStrength = () => {
    if (!password) return null;
    if (password.length < 6) return { level: 'weak', label: 'Weak (min. 6 characters)' };
    const hasLetters = /[a-zA-Z]/.test(password);
    const hasNumbers = /[0-9]/.test(password);
    const hasSpecial = /[^a-zA-Z0-9]/.test(password);
    if (password.length >= 10 && hasLetters && (hasNumbers || hasSpecial)) {
      return { level: 'strong', label: 'Strong password' };
    }
    return { level: 'medium', label: 'Medium strength' };
  };

  const strength = getPasswordStrength();

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <Link to="/" className="auth-logo-link" aria-label="Go to homepage">
            <div className="auth-icon">
              <Bot size={36} />
            </div>
          </Link>
          <h1>Create an account</h1>
          <p>Join your AI workspace to experience grounded knowledge retrieval.</p>
        </div>

        {error && (
          <div className="auth-error" role="alert" aria-live="assertive">
            <AlertCircle size={16} className="auth-error-icon" />
            <span>{error}</span>
          </div>
        )}

        <form className="auth-form" onSubmit={handleSignup} noValidate>
          <div className="auth-input-group">
            <label htmlFor="signup-username">Username</label>
            <div className="auth-input-wrapper">
              <User size={16} className="auth-input-icon" aria-hidden="true" />
              <input
                id="signup-username"
                name="username"
                type="text"
                autoComplete="username"
                className="auth-input"
                placeholder="Choose a username"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
                disabled={loading}
                autoFocus
              />
            </div>
          </div>

          <div className="auth-input-group">
            <label htmlFor="signup-email">
              Email <span className="label-optional">(optional)</span>
            </label>
            <div className="auth-input-wrapper">
              <Mail size={16} className="auth-input-icon" aria-hidden="true" />
              <input
                id="signup-email"
                name="email"
                type="email"
                autoComplete="email"
                className="auth-input"
                placeholder="you@example.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                disabled={loading}
              />
            </div>
          </div>

          <div className="auth-input-group">
            <label htmlFor="signup-password">Password</label>
            <div className="auth-input-wrapper">
              <Lock size={16} className="auth-input-icon" aria-hidden="true" />
              <input
                id="signup-password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                className="auth-input"
                placeholder="Min. 6 characters"
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

            {strength && (
              <div className={`password-strength ${strength.level}`} aria-live="polite">
                <div className="strength-bar-track">
                  <div className="strength-bar" />
                </div>
                <span className="strength-label">{strength.label}</span>
              </div>
            )}
          </div>

          <button type="submit" className="auth-button" disabled={loading}>
            {loading ? (
              <>
                <Loader size={16} className="spin" aria-hidden="true" />
                <span>Creating account...</span>
              </>
            ) : (
              <span>Create Account</span>
            )}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account?{' '}
          <Link to="/login" className="auth-link">Sign in</Link>
        </p>
      </div>
    </div>
  );
}

export default Signup;
