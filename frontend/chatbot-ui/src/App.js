import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import ChatWindow from './components/ChatWindow';
import Dashboard from './components/Dashboard';
import Login from './components/Login';
import Signup from './components/Signup';
import LandingPage from './components/LandingPage';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app-container">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          
          <Route path="/chat" element={
            <>
              <ChatWindow />
            </>
          } />
          
          <Route path="/dashboard" element={
            <>
              <nav className="navbar glass-navbar" aria-label="Dashboard Navigation">
                <Link to="/" className="nav-brand" style={{ textDecoration: 'none', color: 'inherit' }}>
                  NovaMind AI
                </Link>
                <div className="nav-links">
                  <Link to="/chat" className="nav-link">Workspace</Link>
                  <Link to="/dashboard" className="nav-link">Dashboard</Link>
                </div>
              </nav>
              <Dashboard />
            </>
          } />
        </Routes>
      </div>
    </Router>
  );
}

export default App;