import React, { useState, useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import { createSession, sendMessage, isAuthenticated, getUsername, logout } from '../services/chatService';
import TextareaAutosize from 'react-textarea-autosize';
import { Mic, MicOff, Send, PlusCircle, Volume2, VolumeX, Bot, Moon, Sun, LogOut, Menu } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import './ChatWindow.css';

// ── Audio Context for UI sounds ────────────────────────────────────────────
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

const playTone = (freq, type, duration, vol) => {
  if (audioCtx.state === 'suspended') audioCtx.resume();
  const oscillator = audioCtx.createOscillator();
  const gainNode = audioCtx.createGain();
  oscillator.type = type;
  oscillator.frequency.setValueAtTime(freq, audioCtx.currentTime);
  gainNode.gain.setValueAtTime(vol, audioCtx.currentTime);
  gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
  oscillator.connect(gainNode);
  gainNode.connect(audioCtx.destination);
  oscillator.start();
  oscillator.stop(audioCtx.currentTime + duration);
};

const playSendSound = () => {
  playTone(400, 'sine', 0.1, 0.1);
  setTimeout(() => playTone(600, 'sine', 0.15, 0.1), 50);
};

const playReceiveSound = () => {
  playTone(800, 'sine', 0.1, 0.1);
  setTimeout(() => playTone(1200, 'sine', 0.2, 0.1), 50);
};

function ChatWindow() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('darkMode') === 'true');
  const [username, setUsername] = useState('User');

  const bottomRef = useRef(null);
  const recognitionRef = useRef(null);
  const navigate = useNavigate();

  // ── Auth guard ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isAuthenticated()) {
      navigate('/login');
      return;
    }
    const name = getUsername();
    if (name) setUsername(name);
  }, [navigate]);

  // ── Dark mode ──────────────────────────────────────────────────────────────
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
    localStorage.setItem('darkMode', darkMode);
  }, [darkMode]);

  // ── Speech Recognition ─────────────────────────────────────────────────────
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = 'en-US';
      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInput(prev => prev + (prev ? ' ' : '') + transcript);
        setIsListening(false);
      };
      recognitionRef.current.onerror = () => setIsListening(false);
      recognitionRef.current.onend = () => setIsListening(false);
    }
  }, []);

  // ── Session init ───────────────────────────────────────────────────────────
  useEffect(() => {
    const initSession = async () => {
      try {
        const id = await createSession();
        setSessionId(id);
        setIsConnected(true);
        const welcomeMessage = `Hello, ${username}! 👋 I'm your AI assistant. Ask me anything — coding, science, math, history, creative writing, and more!`;
        setMessages([{
          id: Date.now(),
          sender: 'bot',
          text: welcomeMessage,
          intent: 'greeting',
          confidence: 1.0
        }]);
        if (voiceEnabled) speakText(welcomeMessage);
      } catch {
        setMessages([{
          id: Date.now(),
          sender: 'bot',
          text: 'Could not connect to server. Please make sure the backend is running.',
        }]);
      }
    };
    if (!sessionId && isAuthenticated()) {
      initSession();
    }
  }, [voiceEnabled, sessionId, username]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const speakText = (text) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      window.speechSynthesis.speak(utterance);
    }
  };

  const toggleListening = () => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      recognitionRef.current?.start();
      setIsListening(true);
    }
  };

  const handleClearChat = () => {
    setMessages([]);
    setSessionId(null);
    setInput('');
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userText = input.trim();
    setMessages(prev => [...prev, { id: Date.now(), sender: 'user', text: userText }]);
    setInput('');
    setIsLoading(true);
    playSendSound();

    try {
      const result = await sendMessage(userText, sessionId);
      const botMessage = {
        id: Date.now() + 1,
        sender: 'bot',
        text: result.bot_response,
        intent: result.intent,
        confidence: result.confidence,
        isNew: true
      };
      setMessages(prev => prev.map(m => ({ ...m, isNew: false })).concat(botMessage));
      playReceiveSound();
      if (voiceEnabled) speakText(result.bot_response);
    } catch (err) {
      // If 401, token expired — redirect to login
      if (err?.response?.status === 401) {
        logout();
        navigate('/login');
        return;
      }
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'bot',
        text: 'Sorry, something went wrong. Please try again.'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className={`chat-layout has-sidebar ${darkMode ? 'dark' : ''}`}>

      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <aside className={`chat-sidebar ${isSidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <Bot size={24} />
            <span>AI Assistant</span>
          </div>
        </div>

        <div className="sidebar-content">
          <button className="new-chat-btn" onClick={handleClearChat}>
            <PlusCircle size={16} /> New Chat
          </button>
          <div className="recent-chats">
            <p className="section-title">Recent</p>
            <div className="chat-history-item active">Current Session</div>
          </div>
        </div>

        <div className="sidebar-footer">
          <div className="user-profile">
            <div className="user-avatar-small">{username.charAt(0).toUpperCase()}</div>
            <span>{username}</span>
          </div>
          <button className="logout-btn" onClick={handleLogout} title="Log out">
            <LogOut size={15} />
            Log Out
          </button>
        </div>
      </aside>

      {/* ── Main wrapper ──────────────────────────────────────────────────── */}
      <div className="chat-main-wrapper">

        {/* Header */}
        <header className="chat-header glass-effect">
          <div className="header-brand">
            <button className="toggle-sidebar-btn" onClick={() => setIsSidebarOpen(!isSidebarOpen)} title="Toggle sidebar">
              <Menu size={20} />
            </button>
            <div className="brand-text">
              <h2>AI Assistant</h2>
              <p className="status-indicator">
                <span className={`status-dot ${isConnected ? 'online' : 'offline'}`}></span>
                {isConnected ? 'Connected & Ready' : 'Connecting...'}
              </p>
            </div>
          </div>

          <div className="header-actions">
            <button
              className={`action-btn ${darkMode ? 'active' : ''}`}
              onClick={() => setDarkMode(!darkMode)}
              title="Toggle Dark Mode"
            >
              {darkMode ? <Sun size={18} /> : <Moon size={18} />}
              <span className="btn-text">{darkMode ? 'Light' : 'Dark'}</span>
            </button>
            <button
              className={`action-btn ${voiceEnabled ? 'active' : ''}`}
              onClick={() => setVoiceEnabled(!voiceEnabled)}
              title="Toggle Voice Responses"
            >
              {voiceEnabled ? <Volume2 size={18} /> : <VolumeX size={18} />}
              <span className="btn-text">Voice</span>
            </button>
          </div>
        </header>

        {/* Messages */}
        <main className="chat-main">
          <div className="messages-container">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}

            {isLoading && (
              <div className="message-wrapper bot-wrapper fade-in">
                <div className="avatar bot-avatar">
                  <Bot size={20} />
                </div>
                <div className="message-bubble bot-bubble typing-indicator-bubble">
                  <div className="typing-indicator">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} className="scroll-anchor" />
          </div>
        </main>

        {/* Input Footer */}
        <footer className="chat-footer glass-effect">
          <div className="input-container">
            <button
              className={`mic-btn ${isListening ? 'listening' : ''}`}
              onClick={toggleListening}
              title={isListening ? 'Stop listening' : 'Start speaking'}
            >
              {isListening ? <Mic size={20} /> : <MicOff size={20} />}
            </button>

            <TextareaAutosize
              className="chat-input"
              minRows={1}
              maxRows={6}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask me anything... (Shift+Enter for new line)"
            />

            <button
              className={`send-btn ${input.trim() ? 'active' : ''}`}
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              title="Send Message"
            >
              <Send size={20} />
            </button>
          </div>
          <p className="footer-disclaimer">AI can make mistakes. Verify important information.</p>
        </footer>
      </div>
    </div>
  );
}

export default ChatWindow;