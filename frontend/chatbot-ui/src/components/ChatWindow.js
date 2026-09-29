import React, { useState, useEffect, useRef, useCallback } from 'react';
import MessageBubble from './MessageBubble';
import {
  createSession, sendMessage, getSessions, getSessionMessages,
  deleteSession, renameSession, getModels, isAuthenticated, getUsername, logout,
  uploadDocument, getDocuments, deleteDocument, sendRAGQuery
} from '../services/chatService';
import TextareaAutosize from 'react-textarea-autosize';
import {
  Mic, MicOff, Send, PlusCircle, Volume2, VolumeX, Bot,
  Moon, Sun, LogOut, Menu, Trash2, ChevronDown, Cpu, X,
  Paperclip, Download, Search, Edit2, Check,
  FolderOpen, Upload, Layers, MessageSquare, Database, AlertCircle, CheckCircle
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

  // Mode: 'chat' (General AI) | 'rag' (Ask My Documents)
  const [chatMode, setChatMode]         = useState('chat');

  // Document Management & Knowledge Base
  const [documents, setDocuments]       = useState([]);
  const [isDocPanelOpen, setIsDocPanelOpen] = useState(false);
  const [isUploading, setIsUploading]   = useState(false);
  const [uploadFeedback, setUploadFeedback] = useState(null);
  const [selectedDocIds, setSelectedDocIds] = useState([]);

  // File upload input ref
  const fileInputRef                    = useRef(null);
  const panelFileInputRef               = useRef(null);

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
  const [selectedModel, setSelectedModel] = useState('openai/gpt-oss-20b');
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

  // ── Load user documents ──────────────────────────────────────────────────────
  const loadDocs = useCallback(async () => {
    try {
      const docs = await getDocuments();
      setDocuments(docs || []);
    } catch {}
  }, []);

  useEffect(() => {
    if (isAuthenticated()) {
      loadDocs();
    }
  }, [loadDocs]);

  // ── Load available models ────────────────────────────────────────────────────
  useEffect(() => {
    getModels().then(loadedModels => {
      if (Array.isArray(loadedModels) && loadedModels.length > 0) {
        setModels(loadedModels);
        setSelectedModel(prev => loadedModels.some(m => m.id === prev) ? prev : loadedModels[0].id);
      }
    }).catch(() =>
      setModels([
        { id: 'openai/gpt-oss-20b',   name: 'GPT OSS 20B (Fast)' },
        { id: 'openai/gpt-oss-120b',  name: 'GPT OSS 120B' },
        { id: 'qwen/qwen3.8-27b',     name: 'Qwen 3.8 27B' },
        { id: 'groq/compound-mini',   name: 'Groq Compound Mini' },
      ])
    );
  }, []);

  // ── Init new session ─────────────────────────────────────────────────────────
  const initNewSession = useCallback(async (mode = chatMode) => {
    try {
      const id = await createSession();
      setSessionId(id);
      setActiveSessionId(id);
      setIsConnected(true);
      const greeting = mode === 'rag'
        ? `Hello, ${getUsername() || 'there'}! 📚 You are in **Ask My Documents (RAG)** mode. Ask questions and get answers grounded strictly in your indexed documents, complete with source citations!`
        : `Hello, ${getUsername() || 'there'}! 👋 Welcome to AI Chatbot. Ask me anything, or switch to **Ask My Documents** mode to query your files!`;

      setMessages([{
        id: Date.now(), sender: 'bot', isNew: false, text: greeting,
      }]);
      loadSessions();
    } catch {
      setMessages([{ id: Date.now(), sender: 'bot', text: 'Could not connect. Make sure the backend is running.' }]);
    }
  }, [loadSessions, chatMode]);

  useEffect(() => {
    if (isAuthenticated()) { initNewSession(chatMode); }
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

  // ── Upload Document to Knowledge Base (RAG) ──────────────────────────────────
  const handleUploadFile = async (file) => {
    if (!file) return;
    setIsUploading(true);
    setUploadFeedback(null);
    try {
      const res = await uploadDocument(file);
      setUploadFeedback({ type: 'success', message: res.message || `Indexed ${file.name}` });
      await loadDocs();
      // Add system announcement in chat
      setMessages(prev => [
        ...prev,
        {
          id: Date.now(),
          sender: 'bot',
          isNew: false,
          text: `📄 **Document Indexed**: \`${file.name}\` (${res.document?.chunk_count || 0} chunks, ${res.document?.page_count || 1} pages). You can now ask questions about this document in RAG mode!`
        }
      ]);
    } catch (err) {
      const msg = err?.response?.data?.error || `Failed to index ${file.name}`;
      setUploadFeedback({ type: 'error', message: msg });
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      handleUploadFile(file);
    }
    e.target.value = null;
  };

  // ── Delete Document from Knowledge Base ──────────────────────────────────────
  const handleDeleteDoc = async (docId, filename) => {
    if (!window.confirm(`Delete "${filename}" and remove its embeddings from your knowledge base?`)) return;
    try {
      await deleteDocument(docId);
      await loadDocs();
      setMessages(prev => [
        ...prev,
        {
          id: Date.now(),
          sender: 'bot',
          isNew: false,
          text: `🗑️ Removed document \`${filename}\` from your knowledge base.`
        }
      ]);
    } catch {}
  };

  // ── Toggle Document Selection Filter ─────────────────────────────────────────
  const handleToggleDocFilter = (docId) => {
    setSelectedDocIds(prev =>
      prev.includes(docId) ? prev.filter(id => id !== docId) : [...prev, docId]
    );
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
    const exportText = messages.map(m => `### ${m.sender === 'user' ? 'User' : 'AI Chatbot'}:\n${m.text}\n${m.sources ? '\n**Sources:** ' + m.sources.map(s => `[${s.document_name}, Page ${s.page_number}]`).join(', ') : ''}`).join('\n---\n\n');
    const blob = new Blob([exportText], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `AI-Chatbot-${chatMode.toUpperCase()}-${sessionId || 'export'}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ── New Chat ─────────────────────────────────────────────────────────────────
  const handleNewChat = () => {
    setMessages([]);
    setSessionId(null);
    setInput('');
    initNewSession(chatMode);
  };

  // ── Mode Switch ──────────────────────────────────────────────────────────────
  const handleModeChange = (newMode) => {
    if (newMode === chatMode) return;
    setChatMode(newMode);
    setMessages(prev => [
      ...prev,
      {
        id: Date.now(),
        sender: 'bot',
        isNew: false,
        text: newMode === 'rag'
          ? `🔄 Switched to **Ask My Documents (RAG)** mode. Queries are now grounded strictly on your ${documents.length} uploaded document(s).`
          : `🔄 Switched to **General AI Chat** mode. Multi-turn conversation with active Groq models.`
      }
    ]);
  };

  // ── Logout ───────────────────────────────────────────────────────────────────
  const handleLogout = () => { logout(); navigate('/login'); };

  // ── Speech Synthesis ────────────────────────────────────────────────────────
  const speakText = t => { if ('speechSynthesis' in window) { window.speechSynthesis.cancel(); window.speechSynthesis.speak(new SpeechSynthesisUtterance(t)); } };

  // ── Speech Recognition ───────────────────────────────────────────────────────
  const toggleListening = () => {
    if (isListening) { recognitionRef.current?.stop(); setIsListening(false); }
    else             { recognitionRef.current?.start(); setIsListening(true); }
  };

  // ── Send Message (Handles Mode A: Chat & Mode B: RAG) ────────────────────────
  const handleSend = async () => {
    const userText = input.trim();
    if (!userText || isLoading) return;

    setMessages(prev => [...prev, { id: Date.now(), sender: 'user', text: userText }]);
    setInput('');
    setIsLoading(true);
    playSendSound();

    try {
      if (chatMode === 'rag') {
        // Mode B: RAG Query
        const activeDocFilter = selectedDocIds.length > 0 ? selectedDocIds : null;
        const result = await sendRAGQuery(userText, selectedModel, activeDocFilter);

        const botMsg = {
          id: Date.now() + 1,
          sender: 'bot',
          isNew: true,
          text: result.answer,
          sources: result.sources || [],
          model: result.model
        };
        setMessages(prev => prev.map(m => ({ ...m, isNew: false })).concat(botMsg));
        playReceiveSound();
        if (voiceEnabled) speakText(result.answer);
      } else {
        // Mode A: General AI Chat
        const result = await sendMessage(userText, sessionId, selectedModel);
        const botMsg = {
          id: Date.now() + 1,
          sender: 'bot',
          isNew: true,
          text: result.bot_response,
          intent: result.intent,
          confidence: result.confidence,
        };
        setMessages(prev => prev.map(m => ({ ...m, isNew: false })).concat(botMsg));
        playReceiveSound();
        if (voiceEnabled) speakText(result.bot_response);

        if (result.session_id && result.session_id !== sessionId) {
          setSessionId(result.session_id);
          setActiveSessionId(result.session_id);
        }
        loadSessions();
      }
    } catch (err) {
      if (err?.response?.status === 401) { logout(); navigate('/login'); return; }
      setMessages(prev => [...prev, { id: Date.now()+1, sender: 'bot', text: 'Something went wrong. Please check your connection and try again.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const currentModelName = models.find(m => m.id === selectedModel)?.name || 'GPT OSS 20B (Fast)';
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
            <span>AI Chatbot</span>
          </div>
        </div>

        <div className="sidebar-content">
          <button className="new-chat-btn" onClick={handleNewChat}>
            <PlusCircle size={15} /> New Chat
          </button>

          {/* Quick Access to Documents */}
          <button
            className={`doc-panel-toggle-btn ${isDocPanelOpen ? 'active' : ''}`}
            onClick={() => setIsDocPanelOpen(o => !o)}
          >
            <FolderOpen size={15} />
            <span>Knowledge Base ({documents.length})</span>
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
              <h2>AI Chatbot</h2>
              <p className="status-indicator">
                <span className={`status-dot ${isConnected ? 'online' : 'offline'}`} />
                {isConnected ? 'Connected' : 'Connecting…'}
              </p>
            </div>
          </div>

          {/* Mode Switcher Tabs */}
          <div className="mode-switcher-container">
            <button
              className={`mode-tab ${chatMode === 'chat' ? 'active' : ''}`}
              onClick={() => handleModeChange('chat')}
              title="General AI Conversational Chat"
            >
              <MessageSquare size={14} />
              <span>General AI</span>
            </button>
            <button
              className={`mode-tab ${chatMode === 'rag' ? 'active' : ''}`}
              onClick={() => handleModeChange('rag')}
              title="Ask My Documents: Grounded Q&A with Vector Search"
            >
              <Database size={14} />
              <span>Ask My Documents (RAG)</span>
              {documents.length > 0 && (
                <span className="mode-doc-count">{documents.length}</span>
              )}
            </button>
          </div>

          <div className="header-actions">
            {/* Knowledge Base Drawer Button */}
            <button
              className={`action-btn ${isDocPanelOpen ? 'active' : ''}`}
              onClick={() => setIsDocPanelOpen(o => !o)}
              title="Manage Documents & Knowledge Base"
            >
              <Layers size={15} />
              <span className="btn-text">Documents ({documents.length})</span>
            </button>

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

        {/* ── Document Management Drawer ─────────────────────────────────── */}
        {isDocPanelOpen && (
          <div className="doc-panel-overlay" onClick={() => setIsDocPanelOpen(false)}>
            <div className="doc-panel-content glass-effect" onClick={e => e.stopPropagation()}>
              <div className="doc-panel-header">
                <div className="doc-panel-title">
                  <FolderOpen size={18} />
                  <h3>Knowledge Base Documents</h3>
                </div>
                <button className="icon-action-btn" onClick={() => setIsDocPanelOpen(false)}>
                  <X size={16} />
                </button>
              </div>

              <div className="doc-upload-box">
                <input
                  type="file"
                  ref={panelFileInputRef}
                  onChange={handleFileSelect}
                  style={{ display: 'none' }}
                  accept=".pdf,.docx,.doc,.txt,.md,.csv,.json"
                />
                <button
                  className="upload-dropzone-btn"
                  onClick={() => panelFileInputRef.current?.click()}
                  disabled={isUploading}
                >
                  <Upload size={20} />
                  <span>{isUploading ? 'Chunking & Embedding...' : 'Click to Upload PDF, DOCX, or TXT'}</span>
                  <small>Files are automatically chunked & indexed into your isolated vector store</small>
                </button>
              </div>

              {uploadFeedback && (
                <div className={`upload-alert ${uploadFeedback.type}`}>
                  {uploadFeedback.type === 'success' ? <CheckCircle size={15} /> : <AlertCircle size={15} />}
                  <span>{uploadFeedback.message}</span>
                </div>
              )}

              <div className="doc-list-section">
                <div className="doc-list-header">
                  <span>Uploaded Documents ({documents.length})</span>
                  {selectedDocIds.length > 0 && (
                    <button
                      className="clear-filter-btn"
                      onClick={() => setSelectedDocIds([])}
                    >
                      Clear Selection ({selectedDocIds.length})
                    </button>
                  )}
                </div>

                {documents.length === 0 ? (
                  <div className="empty-docs-state">
                    <p>No documents uploaded yet.</p>
                    <small>Upload PDF, DOCX, or TXT documents to enable grounded RAG answering.</small>
                  </div>
                ) : (
                  <div className="doc-items-list">
                    {documents.map(doc => {
                      const isFiltered = selectedDocIds.includes(doc.id);
                      return (
                        <div key={doc.id} className={`doc-item-row ${isFiltered ? 'selected' : ''}`}>
                          <label className="doc-checkbox-wrapper" title="Filter queries to this document">
                            <input
                              type="checkbox"
                              checked={isFiltered}
                              onChange={() => handleToggleDocFilter(doc.id)}
                            />
                          </label>
                          <div className="doc-info">
                            <span className="doc-name" title={doc.filename}>{doc.filename}</span>
                            <div className="doc-submeta">
                              <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                              <span>·</span>
                              <span>{doc.chunk_count} chunks</span>
                              <span>·</span>
                              <span>{doc.page_count} page(s)</span>
                            </div>
                          </div>
                          <button
                            className="doc-delete-btn"
                            onClick={() => handleDeleteDoc(doc.id, doc.filename)}
                            title="Delete document and remove embeddings"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

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
                  <small style={{ display: 'block', marginTop: '6px', fontSize: '0.75rem', opacity: 0.7 }}>
                    {chatMode === 'rag' ? 'Retrieving vector context & generating grounded answer...' : 'Thinking...'}
                  </small>
                </div>
              </div>
            )}
            <div ref={bottomRef} className="scroll-anchor" />
          </div>
        </main>

        {/* Input Footer */}
        <footer className="chat-footer glass-effect">
          <div className="input-container">
            {/* Direct Upload / Pin */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              style={{ display: 'none' }}
              accept=".pdf,.docx,.doc,.txt,.md,.csv,.json"
            />
            <button
              className={`attach-btn ${isUploading ? 'uploading' : ''}`}
              onClick={() => fileInputRef.current?.click()}
              title="Upload & Index Document (PDF, DOCX, TXT)"
              disabled={isUploading}
            >
              {isUploading ? <Upload size={18} className="spin" /> : <Paperclip size={18} />}
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
              placeholder={
                chatMode === 'rag'
                  ? selectedDocIds.length > 0
                    ? `Ask about ${selectedDocIds.length} selected document(s)…`
                    : documents.length > 0
                      ? `Ask questions across your ${documents.length} document(s)…`
                      : "Upload a document first, then ask questions about it…"
                  : "Ask me anything… (Shift+Enter for new line)"
              }
            />

            <button
              className={`send-btn ${input.trim() ? 'active' : ''}`}
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
            >
              <Send size={18} />
            </button>
          </div>
          <p className="footer-disclaimer">
            Mode: <strong>{chatMode === 'rag' ? 'Ask My Documents (RAG)' : 'General AI Chat'}</strong> · Using <strong>{currentModelName}</strong> · Production RAG with FAISS & Groq.
          </p>
        </footer>
      </div>
    </div>
  );
}

export default ChatWindow;