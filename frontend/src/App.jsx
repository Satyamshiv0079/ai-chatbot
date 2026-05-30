import { useState, useRef, useEffect } from 'react'
import './App.css'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'
const API_TOKEN = import.meta.env.VITE_API_AUTH_TOKEN || ''

const getHeaders = (extraHeaders = {}) => {
  const headers = { ...extraHeaders }
  if (API_TOKEN) {
    headers['Authorization'] = `Bearer ${API_TOKEN}`
  }
  return headers
}

const GROQ_MODELS = [
  { key: 'llama3-70b', label: 'Llama 3.3 70B', desc: 'Most Capable & Versatile' },
  { key: 'llama3-8b', label: 'Llama 3.1 8B', desc: 'Ultra-fast Response Time' },
]

export default function App() {
  const [messages, setMessages] = useState([
    { 
      role: 'bot', 
      text: 'Hello! I am NovaMind. How can I assist you today? I can track your orders, handle returns, or converse with you about anything!',
      engine: 'support_engine' 
    }
  ])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [backendStatus, setBackendStatus] = useState('checking')
  
  // UI states
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [groqModel, setGroqModel] = useState('llama3-70b')
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [sessionsList, setSessionsList] = useState([])
  const [chatMode, setChatMode] = useState('support_engine')
  
  const messagesEndRef = useRef(null)

  // Initialize and check status
  useEffect(() => {
    checkBackend()
    loadLocalSessions()
  }, [])

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const checkBackend = async () => {
    try {
      const res = await fetch(`${API_BASE}/health`)
      if (res.ok) {
        setBackendStatus('online')
        // Automatically start or resume session
        const storedActiveSession = localStorage.getItem('novamind_active_session')
        if (storedActiveSession) {
          resumeSession(storedActiveSession)
        } else {
          startNewSession()
        }
      } else {
        setBackendStatus('offline')
      }
    } catch {
      setBackendStatus('offline')
    }
  }

  // Session history helpers
  const loadLocalSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/sessions`, { headers: getHeaders() })
      if (res.ok) {
        const data = await res.json()
        if (data.sessions) {
          setSessionsList(data.sessions)
          localStorage.setItem('novamind_sessions', JSON.stringify(data.sessions))
          return data.sessions
        }
      }
    } catch (e) {
      console.error('Session history fetch error:', e)
    }

    // Fallback to localStorage
    const stored = localStorage.getItem('novamind_sessions')
    if (stored) {
      const parsed = JSON.parse(stored)
      setSessionsList(parsed)
      return parsed
    }
    return []
  }

  const startNewSession = async () => {
    if (loading) return
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/session/new`, { method: 'POST', headers: getHeaders() })
      const data = await res.json()
      const newId = data.session_id
      setSessionId(newId)
      localStorage.setItem('novamind_active_session', newId)
      
      setMessages([
        { 
          role: 'bot', 
          text: 'Hello! I am NovaMind. How can I assist you today? I can track your orders, handle returns, or converse with you about anything!',
          engine: 'support_engine' 
        }
      ])
      
      // Sync sessions with backend
      await loadLocalSessions()
    } catch (e) {
      console.error('Session creation error:', e)
    } finally {
      setLoading(false)
    }
  }

  const resumeSession = async (id) => {
    setSessionId(id)
    localStorage.setItem('novamind_active_session', id)
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/history/${id}`, { headers: getHeaders() })
      if (res.ok) {
        const data = await res.json()
        const history = data.history.map(turn => [
          { role: 'user', text: turn.user },
          { 
            role: 'bot', 
            text: turn.bot, 
            engine: turn.intent === 'generative_qa' ? 'generative_engine' : 'support_engine',
            intent: turn.intent !== 'generative_qa' ? turn.intent : null
          }
        ]).flat()
        
        if (history.length > 0) {
          setMessages(history)
        } else {
          setMessages([
            { 
              role: 'bot', 
              text: 'Hello! I am NovaMind. How can I assist you today? I can track your orders, handle returns, or converse with you about anything!',
              engine: 'support_engine' 
            }
          ])
        }
      } else {
        startNewSession()
      }
    } catch {
      startNewSession()
    } finally {
      setLoading(false)
    }
  }

  const selectSession = (id) => {
    if (id === sessionId) return
    resumeSession(id)
  }

  const sendMessage = async (messageText = null) => {
    const text = messageText ? messageText.trim() : input.trim()
    if (!text || loading) return

    const userMsg = { role: 'user', text }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    // Update active session title based on the first query
    const activeIndex = sessionsList.findIndex(s => s.id === sessionId)
    if (activeIndex !== -1 && sessionsList[activeIndex].title === 'New Conversation') {
      const updated = [...sessionsList]
      updated[activeIndex].title = text.length > 25 ? text.substring(0, 22) + '...' : text
      setSessionsList(updated)
      localStorage.setItem('novamind_sessions', JSON.stringify(updated))
    }

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: getHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ 
          message: text, 
          session_id: sessionId,
          model: groqModel,
          mode: chatMode
        })
      })
      const data = await res.json()
      if (data.error) {
        setMessages(prev => [...prev, { role: 'bot', text: `Error: ${data.error}`, engine: 'fallback_engine' }])
      } else {
        setMessages(prev => [...prev, {
          role: 'bot', 
          text: data.bot_response,
          intent: data.intent !== 'generative_qa' ? data.intent : null, 
          confidence: data.confidence,
          engine: data.engine,
          model: data.model
        }])
        
        // Sync sessions with backend to fetch correct database-backed titles and timestamps
        await loadLocalSessions()
      }
    } catch (e) {
      setMessages(prev => [...prev, { role: 'bot', text: 'Could not connect to the gateway. Please retry.', engine: 'fallback_engine' }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { 
      e.preventDefault()
      sendMessage() 
    }
  }

  // Copy code blocks helper
  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    alert('Code copied to clipboard! ✓')
  }

  // Custom regex markdown/code blocks parser
  const renderMessageText = (text) => {
    if (!text) return ''
    const parts = text.split(/(```[\s\S]*?```)/g)
    
    return parts.map((part, index) => {
      if (part.startsWith('```')) {
        const match = part.match(/```(\w*)\n([\s\S]*?)```/)
        const lang = match ? match[1] : 'code'
        const code = match ? match[2] : part.slice(3, -3)
        
        return (
          <div className="code-container" key={index}>
            <div className="code-header">
              <span className="code-lang">{lang}</span>
              <button className="copy-btn" onClick={() => copyToClipboard(code)}>
                📋 Copy
              </button>
            </div>
            <pre className="code-pre"><code>{code}</code></pre>
          </div>
        )
      }
      
      const boldParts = part.split(/(\*\*.*?\*\*)/g)
      return boldParts.map((subPart, subIndex) => {
        if (subPart.startsWith('**') && subPart.endsWith('**')) {
          return <strong key={subIndex}>{subPart.slice(2, -2)}</strong>
        }
        return subPart
      })
    })
  }

  // Interactive Grid Suggestions
  const dashboardSuggestions = [
    { text: 'Where is my order #12345?', cat: 'tracking' },
    { text: 'I want a refund for my purchase', cat: 'refunds' },
    { text: 'Explain quantum computing in simple terms', cat: 'ai brain' },
    { text: 'Write a Python function to sort numbers', cat: 'coding' },
  ]

  const quickPills = [
    'Cancel my order #67890',
    'Hello',
    'How do I cancel my order?',
    'Tell me a joke'
  ]

  return (
    <div className="app-layout">
      {/* Sessions Left Sidebar */}
      <div className={`sidebar ${sidebarOpen ? '' : 'collapsed'}`}>
        <div className="sidebar-header">
          <span style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-secondary)' }}>Chat History</span>
          <button className="sidebar-toggle" onClick={() => setSidebarOpen(false)}>◀</button>
        </div>
        <div style={{ padding: '15px' }}>
          <button className="new-chat-btn" onClick={startNewSession}>
            <span>+</span> New Session
          </button>
        </div>
        <div className="session-list">
          {sessionsList.map(s => (
            <button 
              key={s.id} 
              className={`session-item ${s.id === sessionId ? 'active' : ''}`}
              onClick={() => selectSession(s.id)}
            >
              <div className="session-title">{s.title}</div>
              <div className="session-meta">
                <span>ID: {s.id.substring(0, 8)}...</span>
                <span>{s.timestamp}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Main Chat Interface */}
      <div className="chat-main">
        {/* Header bar */}
        <div className="chat-header">
          <div className="header-left">
            {!sidebarOpen && (
              <button className="sidebar-toggle" onClick={() => setSidebarOpen(true)}>▶</button>
            )}
            <div className="avatar-container">
              <div className={`avatar ${chatMode}`}>
                {chatMode === 'support_engine' ? '🤖' : '⚡'}
              </div>
              <span className={`status-indicator ${backendStatus}`}></span>
            </div>
            <div className="header-info">
              <h1>{chatMode === 'support_engine' ? 'NovaMind Support' : 'NovaMind AI'}</h1>
              <span className="status-text">
                {backendStatus === 'online' 
                  ? (chatMode === 'support_engine' ? 'Automated Support Core Active' : 'NovaMind Conversational Core Active') 
                  : backendStatus === 'offline' ? 'Offline' : 'Connecting Core...'}
              </span>
            </div>
          </div>

          <div className="header-right">
            {/* Premium Segmented Mode Selector */}
            <div className="mode-segmented-control">
              <button 
                className={`mode-btn ${chatMode === 'support_engine' ? 'active' : ''}`}
                onClick={() => setChatMode('support_engine')}
              >
                🤖 Support
              </button>
              <button 
                className={`mode-btn ${chatMode === 'novamind_ai' ? 'active' : ''}`}
                onClick={() => setChatMode('novamind_ai')}
              >
                ⚡ NovaMind AI
              </button>
            </div>

            {/* Llama Model Dropdown */}
            <div className="model-dropdown-container">
              <button 
                className="model-dropdown-trigger" 
                onClick={() => setDropdownOpen(!dropdownOpen)}
              >
                ⚙️ {GROQ_MODELS.find(m => m.key === groqModel)?.label} ▾
              </button>
              {dropdownOpen && (
                <div className="model-dropdown-menu">
                  {GROQ_MODELS.map(m => (
                    <button
                      key={m.key}
                      className={`model-dropdown-item ${groqModel === m.key ? 'active' : ''}`}
                      onClick={() => {
                        setGroqModel(m.key)
                        setDropdownOpen(false)
                      }}
                    >
                      <div style={{ fontWeight: 600 }}>{m.label}</div>
                      <div style={{ fontSize: '10px', opacity: 0.7 }}>{m.desc}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Scrollable Message Feed */}
        <div className="messages-container">
          {messages.length === 1 && messages[0].role === 'bot' ? (
            /* Premium Welcome suggestions dashboard */
            <div className="suggestions-panel">
              <div className="welcome-icon">⚡</div>
              <h2 className="welcome-title">Welcome to NovaMind</h2>
              <p className="welcome-desc">
                Your high-performance hybrid AI. I parse transactional order flows using local BERT NLP, 
                and contextually answer general queries using state-of-the-art Llama 3.3.
              </p>
              <div className="suggestions-grid">
                {dashboardSuggestions.map((s, idx) => (
                  <button 
                    key={idx} 
                    className="suggestion-card"
                    onClick={() => sendMessage(s.text)}
                  >
                    <span className="suggestion-text">"{s.text}"</span>
                    <span className="suggestion-category">{s.cat}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Feed listing */
            messages.map((msg, i) => (
              <div key={i} className={`message-row ${msg.role}`}>
                <div className="msg-avatar">{msg.role === 'bot' ? '⚡' : '👤'}</div>
                <div className="bubble-wrapper">
                  <div className={`bubble ${msg.role} ${msg.engine || ''}`}>
                    {renderMessageText(msg.text)}
                  </div>
                  
                  {/* Glowing Engine Badges */}
                  {msg.role === 'bot' && msg.engine && (
                    <div className="engine-badge-wrap">
                      {msg.engine === 'support_engine' && (
                        <span className="engine-badge support">
                          🤖 Database Engine
                        </span>
                      )}
                      {msg.engine === 'generative_engine' && (
                        <span className="engine-badge generative">
                          ⚡ Generative AI ({msg.model ? msg.model.substring(6, 14) : 'Llama'})
                        </span>
                      )}
                      {msg.engine === 'fallback_engine' && (
                        <span className="engine-badge fallback">
                          ⚠️ Fallback Mode
                        </span>
                      )}
                      {msg.intent && (
                        <span className="meta-details">
                          Intent: <strong>{msg.intent}</strong>
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}

          {/* Typing Bouncing animation */}
          {loading && (
            <div className="message-row bot">
              <div className="msg-avatar">⚡</div>
              <div className="bubble bot typing-dots">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Footer/Input Panel */}
        <div className="input-panel">
          {/* Quick pills */}
          <div className="quick-pills">
            {quickPills.map((pill, idx) => (
              <button 
                key={idx} 
                className="quick-pill"
                onClick={() => sendMessage(pill)}
              >
                {pill}
              </button>
            ))}
          </div>

          {/* Text entry field */}
          <div className="input-row">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask me anything..."
              disabled={loading || backendStatus === 'offline'}
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || loading || backendStatus === 'offline'}
              className="send-btn-glowing"
            >
              ➔
            </button>
          </div>
          
          {backendStatus === 'offline' && (
            <div className="offline-banner">
              ⚠️ Unable to establish connection to core. Make sure server is active.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
