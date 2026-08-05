import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Bot, User, Mail, Lock, AlertCircle, CheckCircle, Loader } from 'lucide-react';
import { registerUser } from '../services/chatService';
import './Auth.css';

function Signup() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSignup = async (e) => {
    e.preventDefault();
    setError('');

    if (!username.trim() || !password.trim()) {
      setError('Username and password are required.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    setLoading(true);
    try {
      const data = await registerUser(username.trim(), password, email.trim() || undefined);
      // Store JWT token and username
      localStorage.setItem('authToken', data.access_token);
      localStorage.setItem('chatUsername', data.user.username);
      navigate('/chat');
    } catch (err) {
      const msg = err?.response?.data?.error || 'Registration failed. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const passwordStrength = password.length === 0 ? null : password.length < 6 ? 'weak' : password.length < 10 ? 'medium' : 'strong';

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-logo">
          <div className="auth-icon">
            <Bot size={32} />
          </div>
        </div>
        <h1>Create an Account</h1>
        <p>Join to experience next-gen AI assistance</p>

        {error && (
          <div className="auth-error">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form className="auth-form" onSubmit={handleSignup}>
          <div className="auth-input-group">
            <label>Username</label>
            <div className="auth-input-wrapper">
              <User size={16} className="auth-input-icon" />
              <input
                type="text"
                className="auth-input"
                placeholder="Choose a username"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
                disabled={loading}
              />
            </div>
          </div>

          <div className="auth-input-group">
            <label>Email <span style={{color:'#94a3b8', fontSize:'12px'}}>(optional)</span></label>
            <div className="auth-input-wrapper">
              <Mail size={16} className="auth-input-icon" />
              <input
                type="email"
                className="auth-input"
                placeholder="you@example.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                disabled={loading}
              />
            </div>
          </div>

          <div className="auth-input-group">
            <label>Password</label>
            <div className="auth-input-wrapper">
              <Lock size={16} className="auth-input-icon" />
              <input
                type="password"
                className="auth-input"
                placeholder="Min. 6 characters"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                disabled={loading}
              />
            </div>
            {passwordStrength && (
              <div className={`password-strength ${passwordStrength}`}>
                <div className="strength-bar" />
                <span>{passwordStrength === 'weak' ? 'Weak' : passwordStrength === 'medium' ? 'Medium' : 'Strong'}</span>
              </div>
            )}
          </div>

          <button type="submit" className="auth-button" disabled={loading}>
            {loading ? <><Loader size={16} className="spin" /> Creating account...</> : 'Create Account'}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account?{' '}
          <Link to="/login" className="auth-link">Log in</Link>
        </p>
      </div>
    </div>
  );
}

export default Signup;
