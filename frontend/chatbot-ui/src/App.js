import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import ChatWindow from './components/ChatWindow';
import Dashboard from './components/Dashboard';
import Login from './components/Login';
import Signup from './components/Signup';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app-container">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          
          <Route path="/" element={<Navigate to="/login" replace />} />
          
          <Route path="/chat" element={
            <>
              <ChatWindow />
            </>
          } />
          
          <Route path="/dashboard" element={
            <>
              <nav className="navbar glass-navbar">
                <div className="nav-brand">AI Assistant Hub</div>
                <div className="nav-links">
                  <Link to="/chat" className="nav-link">Chatbot</Link>
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