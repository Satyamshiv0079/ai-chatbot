import React, { useState, useEffect, useRef, useCallback } from 'react';
import MessageBubble from './MessageBubble';
import {
  createSession, sendMessage, getSessions, getSessionMessages,
  deleteSession, renameSession, getModels, isAuthenticated, getUsername, logout
} from '../services/chatService';
import TextareaAutosize from 'react-textarea-autosize';
import {
  Mic, MicOff, Send, PlusCircle, Volume2, VolumeX, Bot,
  Moon, Sun, LogOut, Menu, Trash2, ChevronDown, Cpu, X,
  Paperclip, FileText, Download, Search, Edit2, Check
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import './ChatWindow.css';

// ── Audio Feedback Synthesizer ───────────────────────────────────────────────
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
const playTone = (freq, type, dur, vol) => {
  if (audioCtx.state === 'suspended') audioCtx.resume();
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
  gain.gain.setValueAtTime(vol, audioCtx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + dur);
  osc.connect(gain); gain.connect(audioCtx.destination);
  osc.start(); osc.stop(audioCtx.currentTime + dur);
};
const playSendSound    = () => { playTone(400,'sine',0.1,0.1); setTimeout(()=>playTone(600,'sine',0.15,0.1),50); };
const playReceiveSound = () => { playTone(800,'sine',0.1,0.1); setTimeout(()=>playTone(1200,'sine',0.2,0.1),50); };

function ChatWindow() {
  const [messages, setMessages]         = useState([]);
  const [input, setInput]               = useState('');
  const [sessionId, setSessionId]       = useState(null);
  const [isLoading, setIsLoading]       = useState(false);
  const [isConnected, setIsConnected]   = useState(false);
  const [isListening, setIsListening]   = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [darkMode, setDarkMode]         = useState(() => localStorage.getItem('darkMode') === 'true');
  const [username, setUsername]         = useState('User');

  // Document attachment
  const [attachment, setAttachment]     = useState(null);
  const fileInputRef                    = useRef(null);

  // Chat history sidebar & Search Filter
  const [sessions, setSessions]         = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [searchQuery, setSearchQuery]   = useState('');

  // Inline rename session
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editTitleInput, setEditTitleInput]     = useState('');

  // Model switcher
  const [models, setModels]             = useState([]);
  const [selectedModel, setSelectedModel] = useState('llama-3.3-70b-versatile');
  const [showModelMenu, setShowModelMenu] = useState(false);

  const bottomRef      = useRef(null);
  const recognitionRef = useRef(null);
  const navigate       = useNavigate();

  // ── Auth guard ───────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isAuthenticated()) { navigate('/login'); return; }
    setUsername(getUsername() || 'User');
  }, [navigate]);

  // ── Dark mode ────────────────────────────────────────────────────────────────
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
    localStorage.setItem('darkMode', darkMode);
  }, [darkMode]);

  // ── Speech recognition ───────────────────────────────────────────────────────
  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SR) {
      const r = new SR();
      r.continuous = false; r.interimResults = false; r.lang = 'en-US';
      r.onresult = e => { setInput(p => p + (p ? ' ' : '') + e.results[0][0].transcript); setIsListening(false); };
      r.onerror = () => setIsListening(false);
      r.onend   = () => setIsListening(false);
      recognitionRef.current = r;
    }
  }, []);

  // ── Load past sessions ───────────────────────────────────────────────────────
  const loadSessions = useCallback(async () => {
    setLoadingSessions(true);
    try { setSessions(await getSessions()); }
    catch {} finally { setLoadingSessions(false); }
  }, []);

  // ── Load available models ────────────────────────────────────────────────────
  useEffect(() => {
    getModels().then(setModels).catch(() =>
      setModels([
        { id: 'llama-3.3-70b-versatile', name: 'Llama 3.3 70B' },
        { id: 'llama-3.1-8b-instant',    name: 'Llama 3.1 8B (Fast)' },
        { id: 'mixtral-8x7b-32768',      name: 'Mixtral 8x7B' },
        { id: 'gemma2-9b-it',            name: 'Gemma 2 9B' },
      ])
    );
  }, []);

  // ── Init new session ─────────────────────────────────────────────────────────
  const initNewSession = useCallback(async () => {
    try {
      const id = await createSession();
      setSessionId(id);
      setActiveSessionId(id);
      setIsConnected(true);
      setMessages([{
        id: Date.now(), sender: 'bot', isNew: false,
        text: `Hello, ${getUsername() || 'there'}! 👋 Welcome to NovaMind. Ask me anything, or attach files/documents to analyze!`,
      }]);
      loadSessions();
    } catch {
      setMessages([{ id: Date.now(), sender: 'bot', text: 'Could not connect. Make sure the backend is running.' }]);
    }
  }, [loadSessions]);

  useEffect(() => {
    if (isAuthenticated()) { initNewSession(); }
  }, []); // eslint-disable-line

  // ── Auto-scroll ──────────────────────────────────────────────────────────────
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, isLoading]);

  // ── Load past session ────────────────────────────────────────────────────────
  const loadPastSession = async (sess) => {
    try {
      const data = await getSessionMessages(sess.session_id);
      setSessionId(data.session_id);
      setActiveSessionId(data.session_id);
      setIsConnected(true);
      setMessages(data.messages.map((m, i) => ({ ...m, id: i, isNew: false })));
    } catch {}
  };

  // ── File Selection & Parsing ─────────────────────────────────────────────────
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      setAttachment({
        name: file.name,
        size: (file.size / 1024).toFixed(1) + ' KB',
        content: evt.target.result
      });
    };
    reader.readAsText(file);
    e.target.value = null;
  };

  // ── Session Rename ───────────────────────────────────────────────────────────
  const handleStartRename = (e, sess) => {
    e.stopPropagation();
    setEditingSessionId(sess.session_id);
    setEditTitleInput(sess.title || 'Untitled');
  };

  const handleSaveRename = async (e, sessId) => {
    e.stopPropagation();
    if (!editTitleInput.trim()) return;
    try {
      await renameSession(sessId, editTitleInput.trim());
      setSessions(prev => prev.map(s => s.session_id === sessId ? { ...s, title: editTitleInput.trim() } : s));
      setEditingSessionId(null);
    } catch {}
  };

  // ── Delete Session ───────────────────────────────────────────────────────────
  const handleDeleteSession = async (e, sessId) => {
    e.stopPropagation();
    try {
      await deleteSession(sessId);
      setSessions(prev => prev.filter(s => s.session_id !== sessId));
      if (sessId === sessionId) initNewSession();
    } catch {}
  };

  // ── Export Chat ──────────────────────────────────────────────────────────────
  const handleExportChat = () => {
    if (messages.length === 0) return;
    const exportText = messages.map(m => `### ${m.sender === 'user' ? 'User' : 'NovaMind'}:\n${m.text}\n`).join('\n---\n\n');
    const blob = new Blob([exportText], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `NovaMind-Chat-${sessionId || 'export'}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ── New Chat ─────────────────────────────────────────────────────────────────
  const handleNewChat = () => { setMessages([]); setSessionId(null); setInput(''); setAttachment(null); initNewSession(); };

  // ── Logout ───────────────────────────────────────────────────────────────────
  const handleLogout = () => { logout(); navigate('/login'); };

  // ── Speech Synthesis ────────────────────────────────────────────────────────
  const speakText = t => { if ('speechSynthesis' in window) { window.speechSynthesis.cancel(); window.speechSynthesis.speak(new SpeechSynthesisUtterance(t)); } };

  // ── Speech Recognition ───────────────────────────────────────────────────────
  const toggleListening = () => {
    if (isListening) { recognitionRef.current?.stop(); setIsListening(false); }
    else             { recognitionRef.current?.start(); setIsListening(true); }
  };

  // ── Send Message ─────────────────────────────────────────────────────────────
  const handleSend = async () => {
    if ((!input.trim() && !attachment) || isLoading) return;

    let fullPrompt = input.trim();
    if (attachment) {
      fullPrompt = `[Attached Document: ${attachment.name}]\n\`\`\`\n${attachment.content.slice(0, 3000)}\n\`\`\`\n\n${fullPrompt || 'Please summarize or analyze this document.'}`;
    }

    const userDisplayText = attachment ? `📄 [${attachment.name}]\n${input.trim()}` : input.trim();
    setMessages(prev => [...prev, { id: Date.now(), sender: 'user', text: userDisplayText }]);
    
    setInput('');
    setAttachment(null);
    setIsLoading(true);
    playSendSound();

    try {
      const result = await sendMessage(fullPrompt, sessionId, selectedModel);
      const botMsg = {
        id: Date.now() + 1, sender: 'bot', isNew: true,
        text: result.bot_response, intent: result.intent, confidence: result.confidence,
      };
      setMessages(prev => prev.map(m => ({ ...m, isNew: false })).concat(botMsg));
      playReceiveSound();
      if (voiceEnabled) speakText(result.bot_response);

      if (result.session_id && result.session_id !== sessionId) {
        setSessionId(result.session_id);
        setActiveSessionId(result.session_id);
      }
      loadSessions();
    } catch (err) {
      if (err?.response?.status === 401) { logout(); navigate('/login'); return; }
      setMessages(prev => [...prev, { id: Date.now()+1, sender: 'bot', text: 'Something went wrong. Please try again.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const currentModelName = models.find(m => m.id === selectedModel)?.name || 'Llama 3.3 70B';
  const filteredSessions = sessions.filter(s => (s.title || '').toLowerCase().includes(searchQuery.toLowerCase()));

  return (
    <div className={`chat-layout has-sidebar ${darkMode ? 'dark' : ''}`}>

      {/* Mobile/Tablet Backdrop */}
      {isSidebarOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setIsSidebarOpen(false)}
          aria-label="Close sidebar"
        />
      )}

      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <aside className={`chat-sidebar ${isSidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <Bot size={20} />
            <span>NovaMind</span>
          </div>
        </div>

        <div className="sidebar-content">
          <button className="new-chat-btn" onClick={handleNewChat}>
            <PlusCircle size={15} /> New Chat
          </button>

          {/* Search Filter */}
          <div className="search-box">
            <Search size={13} className="search-icon" />
            <input
              type="text"
              placeholder="Search chats…"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="recent-chats">
            <p className="section-title">
              {loadingSessions ? 'Loading…' : `Recent (${filteredSessions.length})`}
            </p>

            {filteredSessions.length === 0 && !loadingSessions && (
              <p className="empty-history">No chats found</p>
            )}

            {filteredSessions.map(s => (
              <div
                key={s.session_id}
                className={`chat-history-item ${s.session_id === activeSessionId ? 'active' : ''}`}
                onClick={() => loadPastSession(s)}
                title={s.title}
              >
                {editingSessionId === s.session_id ? (
                  <div className="rename-input-wrapper" onClick={e => e.stopPropagation()}>
                    <input
                      type="text"
                      className="rename-input"
                      value={editTitleInput}
                      onChange={e => setEditTitleInput(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter') handleSaveRename(e, s.session_id); }}
                      autoFocus
                    />
                    <button className="icon-action-btn" onClick={e => handleSaveRename(e, s.session_id)}>
                      <Check size={12} />
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="history-item-inner">
                      <span className="history-title">{s.title || 'Untitled'}</span>
                      <span className="history-meta">{s.message_count} msgs</span>
                    </div>
                    <div className="item-actions">
                      <button className="rename-session-btn" onClick={e => handleStartRename(e, s)} title="Rename chat">
                        <Edit2 size={12} />
                      </button>
                      <button className="delete-session-btn" onClick={e => handleDeleteSession(e, s.session_id)} title="Delete chat">
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="sidebar-footer">
          <div className="user-profile">
            <div className="user-avatar-small">{username.charAt(0).toUpperCase()}</div>
            <span>{username}</span>
          </div>
          <button className="logout-btn" onClick={handleLogout}>
            <LogOut size={14} /> Log Out
          </button>
        </div>
      </aside>

      {/* ── Main Workspace ───────────────────────────────────────────────── */}
      <div className="chat-main-wrapper">

        {/* Header */}
        <header className="chat-header glass-effect">
          <div className="header-brand">
            <button className="toggle-sidebar-btn" onClick={() => setIsSidebarOpen(o => !o)}>
              <Menu size={20} />
            </button>
            <div className="brand-text">
              <h2>NovaMind</h2>
              <p className="status-indicator">
                <span className={`status-dot ${isConnected ? 'online' : 'offline'}`} />
                {isConnected ? 'Connected' : 'Connecting…'}
              </p>
            </div>
          </div>

          <div className="header-actions">
            {/* Model Switcher */}
            <div className="model-switcher-wrapper">
              <button className="model-switcher-btn" onClick={() => setShowModelMenu(o => !o)}>
                <Cpu size={14} />
                <span className="btn-text">{currentModelName}</span>
                <ChevronDown size={13} className={showModelMenu ? 'rotated' : ''} />
              </button>
              {showModelMenu && (
                <div className="model-menu">
                  <div className="model-menu-header">
                    <span>Choose Model</span>
                    <button onClick={() => setShowModelMenu(false)}><X size={14}/></button>
                  </div>
                  {models.map(m => (
                    <button
                      key={m.id}
                      className={`model-menu-item ${m.id === selectedModel ? 'active' : ''}`}
                      onClick={() => { setSelectedModel(m.id); setShowModelMenu(false); }}
                    >
                      <span className="model-name">{m.name}</span>
                      {m.id === selectedModel && <span className="model-check">✓</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Export Chat */}
            <button className="action-btn" onClick={handleExportChat} title="Export Chat Markdown">
              <Download size={15} />
              <span className="btn-text">Export</span>
            </button>

            {/* Dark Mode Toggle */}
            <button className="action-btn" onClick={() => setDarkMode(d => !d)} title="Toggle Dark Mode">
              {darkMode ? <Sun size={16} /> : <Moon size={16} />}
              <span className="btn-text">{darkMode ? 'Light' : 'Dark'}</span>
            </button>

            {/* Voice Mode Toggle */}
            <button className={`action-btn ${voiceEnabled ? 'active' : ''}`} onClick={() => setVoiceEnabled(v => !v)}>
              {voiceEnabled ? <Volume2 size={16}/> : <VolumeX size={16}/>}
              <span className="btn-text">Voice</span>
            </button>
          </div>
        </header>

        {/* Messages */}
        <main className="chat-main">
          <div className="messages-container">
            {messages.map(msg => <MessageBubble key={msg.id} message={msg} />)}

            {isLoading && (
              <div className="message-wrapper bot-wrapper fade-in">
                <div className="avatar bot-avatar spatial-avatar"><Bot size={18} /></div>
                <div className="message-bubble bot-bubble spatial-card typing-indicator-bubble">
                  <div className="typing-indicator">
                    <span /><span /><span />
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} className="scroll-anchor" />
          </div>
        </main>

        {/* Input Footer */}
        <footer className="chat-footer glass-effect">
          {/* Attachment Preview Badge */}
          {attachment && (
            <div className="attachment-badge">
              <FileText size={14} />
              <span className="badge-name">{attachment.name}</span>
              <span className="badge-size">({attachment.size})</span>
              <button className="remove-attachment" onClick={() => setAttachment(null)}>
                <X size={13} />
              </button>
            </div>
          )}

          <div className="input-container">
            {/* Attachment Pin */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              style={{ display: 'none' }}
              accept=".txt,.pdf,.md,.json,.csv,.js,.py,.html,.css"
            />
            <button
              className="attach-btn"
              onClick={() => fileInputRef.current?.click()}
              title="Attach File/Document"
            >
              <Paperclip size={18} />
            </button>

            {/* Mic Speech Button */}
            <button className={`mic-btn ${isListening ? 'listening' : ''}`} onClick={toggleListening} title="Voice Input">
              {isListening ? <Mic size={18} /> : <MicOff size={18} />}
            </button>

            <TextareaAutosize
              className="chat-input"
              minRows={1} maxRows={6}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={attachment ? "Ask a question about this document…" : "Ask me anything… (Shift+Enter for new line)"}
            />

            <button
              className={`send-btn ${(input.trim() || attachment) ? 'active' : ''}`}
              onClick={handleSend}
              disabled={isLoading || (!input.trim() && !attachment)}
            >
              <Send size={18} />
            </button>
          </div>
          <p className="footer-disclaimer">
            Using <strong>{currentModelName}</strong> · NovaMind PWA ready · Verify important info.
          </p>
        </footer>
      </div>
    </div>
  );
}

export default ChatWindow;