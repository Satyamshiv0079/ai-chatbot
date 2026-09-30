import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Bot, Sparkles, ShieldCheck, Cpu,
  FileText, ArrowRight, CheckCircle2, Menu, X,
  MessageSquare, ExternalLink, Zap
} from 'lucide-react';
import { isAuthenticated, getUsername } from '../services/chatService';
import './LandingPage.css';

function LandingPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isAuth, setIsAuth] = useState(false);
  const [user, setUser] = useState('');

  useEffect(() => {
    const authenticated = isAuthenticated();
    setIsAuth(authenticated);
    if (authenticated) {
      setUser(getUsername() || 'User');
    }
  }, []);

  return (
    <div className="landing-root">
      {/* ── Navigation Bar ─────────────────────────────────────────────────── */}
      <header className="landing-header">
        <div className="landing-nav-container">
          <Link to="/" className="landing-brand">
            <div className="landing-logo-badge">
              <Bot size={22} className="brand-icon" />
            </div>
            <span className="brand-title">NovaMind <span className="brand-accent">AI</span></span>
          </Link>

          {/* Desktop Nav Links */}
          <nav className="landing-desktop-nav" aria-label="Main Navigation">
            <a href="#features" className="nav-anchor">Features</a>
            <a href="#how-it-works" className="nav-anchor">How It Works</a>
            <a href="#technology" className="nav-anchor">Technology</a>
          </nav>

          {/* Desktop Actions */}
          <div className="landing-nav-actions">
            {isAuth ? (
              <Link to="/chat" className="btn-primary-glow">
                <span>Open Workspace ({user})</span>
                <ArrowRight size={16} />
              </Link>
            ) : (
              <>
                <Link to="/login" className="btn-ghost">Sign In</Link>
                <Link to="/signup" className="btn-primary-glow">
                  <span>Get Started</span>
                  <ArrowRight size={16} />
                </Link>
              </>
            )}
          </div>

          {/* Mobile Menu Toggle */}
          <button
            type="button"
            className="mobile-menu-btn"
            aria-label="Toggle navigation menu"
            aria-expanded={mobileMenuOpen}
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>

        {/* Mobile Dropdown */}
        {mobileMenuOpen && (
          <div className="mobile-nav-panel">
            <a href="#features" className="mobile-nav-link" onClick={() => setMobileMenuOpen(false)}>Features</a>
            <a href="#how-it-works" className="mobile-nav-link" onClick={() => setMobileMenuOpen(false)}>How It Works</a>
            <a href="#technology" className="mobile-nav-link" onClick={() => setMobileMenuOpen(false)}>Technology</a>
            <div className="mobile-nav-divider" />
            {isAuth ? (
              <Link to="/chat" className="btn-primary-glow full-width" onClick={() => setMobileMenuOpen(false)}>
                <span>Open Workspace</span>
                <ArrowRight size={16} />
              </Link>
            ) : (
              <div className="mobile-auth-btns">
                <Link to="/login" className="btn-ghost full-width" onClick={() => setMobileMenuOpen(false)}>Sign In</Link>
                <Link to="/signup" className="btn-primary-glow full-width" onClick={() => setMobileMenuOpen(false)}>
                  <span>Get Started</span>
                  <ArrowRight size={16} />
                </Link>
              </div>
            )}
          </div>
        )}
      </header>

      {/* ── Hero Section ───────────────────────────────────────────────────── */}
      <section className="landing-hero" id="home">
        <div className="hero-badge">
          <Sparkles size={14} className="hero-badge-icon" />
          <span>AI-POWERED KNOWLEDGE WORKSPACE</span>
        </div>

        <h1 className="hero-headline">
          Chat with AI.<br />
          <span className="headline-gradient">Understand your documents.</span>
        </h1>

        <p className="hero-subtext">
          Ask questions, upload documents, and get grounded AI responses powered by
          modern Retrieval-Augmented Generation (RAG) and multi-model generation.
        </p>

        <div className="hero-cta-group">
          {isAuth ? (
            <Link to="/chat" className="btn-hero-primary">
              <span>Go to Workspace</span>
              <ArrowRight size={18} />
            </Link>
          ) : (
            <>
              <Link to="/signup" className="btn-hero-primary">
                <span>Get Started</span>
                <ArrowRight size={18} />
              </Link>
              <Link to="/login" className="btn-hero-secondary">
                <span>Sign In</span>
              </Link>
            </>
          )}
        </div>

        {/* ── Product Preview (Realistic Chat & RAG UI) ────────────────────── */}
        <div className="hero-preview-wrapper">
          <div className="preview-container glass-card">
            {/* Window Chrome Header */}
            <div className="preview-window-bar">
              <div className="window-dots">
                <span className="dot red" />
                <span className="dot yellow" />
                <span className="dot green" />
              </div>
              <div className="window-title">
                <FileText size={13} />
                <span>NovaMind Workspace &bull; Ask My Documents (RAG)</span>
              </div>
              <div className="window-pill">
                <Cpu size={12} />
                <span>GPT OSS 20B (Active)</span>
              </div>
            </div>

            {/* Simulated Live Interface */}
            <div className="preview-body">
              {/* User Message */}
              <div className="preview-msg user">
                <div className="preview-avatar user">U</div>
                <div className="preview-bubble user">
                  What is our company's remote work policy regarding home office equipment reimbursement?
                </div>
              </div>

              {/* Bot Grounded RAG Message */}
              <div className="preview-msg bot">
                <div className="preview-avatar bot">
                  <Bot size={16} />
                </div>
                <div className="preview-bubble bot">
                  <p>
                    Under the <strong>Remote Work & Equipment Policy</strong>, full-time employees are eligible
                    for a one-time reimbursement of up to <strong>$500</strong> for certified home office equipment
                    (monitors, ergonomic chairs, and keyboards).
                  </p>
                  <p>
                    Expense claims must be submitted within <strong>30 days of purchase</strong> via the expense portal
                    accompanied by itemized receipts.
                  </p>

                  {/* Grounded Citation Badges */}
                  <div className="preview-citations">
                    <div className="citation-header">
                      <CheckCircle2 size={13} className="text-emerald" />
                      <span>Verified Document Sources:</span>
                    </div>
                    <div className="citation-chip">
                      <FileText size={12} />
                      <span className="chip-name">Employee_Handbook_2026.pdf</span>
                      <span className="chip-page">Page 14</span>
                      <span className="chip-match">92% match</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Features Section ───────────────────────────────────────────────── */}
      <section className="landing-section" id="features">
        <div className="landing-section-header">
          <span className="landing-section-eyebrow">CORE CAPABILITIES</span>
          <h2 className="landing-section-title">Built for precision, grounding, and control</h2>
          <p className="landing-section-desc">
            A production architecture designed to give you instant intelligence across multi-turn conversations and personal documents.
          </p>
        </div>

        <div className="features-grid">
          {/* Card 1 */}
          <div className="feature-card glass-card">
            <div className="feature-icon-box">
              <Cpu size={24} />
            </div>
            <h3>Multi-Model AI</h3>
            <p>
              Switch dynamically between multiple active LLMs (GPT OSS 20B, GPT OSS 120B, Qwen 3.8 27B, and Groq Compound) with automated fallback routing.
            </p>
          </div>

          {/* Card 2 */}
          <div className="feature-card glass-card">
            <div className="feature-icon-box">
              <FileText size={24} />
            </div>
            <h3>RAG Document Q&A</h3>
            <p>
              Upload PDF, DOCX, and TXT files. Documents are parsed, split into semantic chunks, and embedded locally into dense 384-dimensional vectors for grounded Q&A.
            </p>
          </div>

          {/* Card 3 */}
          <div className="feature-card glass-card">
            <div className="feature-icon-box">
              <MessageSquare size={24} />
            </div>
            <h3>Persistent Conversations</h3>
            <p>
              Multi-turn chat sessions are permanently recorded and indexed. Search your session history, rename conversations, and resume discussions at any time.
            </p>
          </div>

          {/* Card 4 */}
          <div className="feature-card glass-card">
            <div className="feature-icon-box">
              <ShieldCheck size={24} />
            </div>
            <h3>Secure User Isolation</h3>
            <p>
              Multi-tenant architecture enforces strict boundaries. Each user's FAISS vector store, session history, and documents are strictly partitioned by authenticated JWT identity.
            </p>
          </div>
        </div>
      </section>

      {/* ── How It Works Section ───────────────────────────────────────────── */}
      <section className="landing-section how-section" id="how-it-works">
        <div className="landing-section-header">
          <span className="landing-section-eyebrow">RAG PIPELINE</span>
          <h2 className="landing-section-title">How Retrieval-Augmented Generation Works</h2>
          <p className="landing-section-desc">
            From raw document ingestion to verifiable grounded responses in milliseconds.
          </p>
        </div>

        <div className="pipeline-grid">
          {/* Step 1 */}
          <div className="pipeline-step glass-card">
            <div className="step-number">01</div>
            <h4>Upload</h4>
            <p>Upload documents (PDF, DOCX, TXT) with validation and page-level extraction.</p>
          </div>

          {/* Step 2 */}
          <div className="pipeline-step glass-card">
            <div className="step-number">02</div>
            <h4>Process</h4>
            <p>Recursive text splitting with chunk overlap and dense embeddings via SentenceTransformers.</p>
          </div>

          {/* Step 3 */}
          <div className="pipeline-step glass-card">
            <div className="step-number">03</div>
            <h4>Retrieve</h4>
            <p>Cosine similarity search retrieves the top relevant context passages from isolated FAISS indexes.</p>
          </div>

          {/* Step 4 */}
          <div className="pipeline-step glass-card">
            <div className="step-number">04</div>
            <h4>Generate</h4>
            <p>LLM synthesizes an accurate answer grounded strictly in retrieved context with source citations.</p>
          </div>
        </div>
      </section>

      {/* ── Technology Section ─────────────────────────────────────────────── */}
      <section className="landing-section" id="technology">
        <div className="landing-section-header">
          <span className="landing-section-eyebrow">TECH STACK</span>
          <h2 className="landing-section-title">Built with proven, modern technologies</h2>
          <p className="landing-section-desc">
            Production-grade stack engineered for high performance, memory efficiency, and accurate retrieval.
          </p>
        </div>

        <div className="tech-badges-grid">
          <div className="tech-badge-card glass-card">
            <span className="tech-name">React 19</span>
            <span className="tech-role">Frontend UI & Audio STT/TTS</span>
          </div>
          <div className="tech-badge-card glass-card">
            <span className="tech-name">Python & Flask 3.1</span>
            <span className="tech-role">REST API Gateway & Auth</span>
          </div>
          <div className="tech-badge-card glass-card">
            <span className="tech-name">LangChain</span>
            <span className="tech-role">RAG Orchestration & Prompting</span>
          </div>
          <div className="tech-badge-card glass-card">
            <span className="tech-name">FAISS (faiss-cpu)</span>
            <span className="tech-role">Dense Vector Similarity Store</span>
          </div>
          <div className="tech-badge-card glass-card">
            <span className="tech-name">SentenceTransformers</span>
            <span className="tech-role">all-MiniLM-L6-v2 Embeddings</span>
          </div>
          <div className="tech-badge-card glass-card">
            <span className="tech-name">Groq API</span>
            <span className="tech-role">Ultra-Low Latency Inference</span>
          </div>
          <div className="tech-badge-card glass-card">
            <span className="tech-name">PostgreSQL / Supabase</span>
            <span className="tech-role">SQLAlchemy Persistence</span>
          </div>
          <div className="tech-badge-card glass-card">
            <span className="tech-name">HuggingFace BERT</span>
            <span className="tech-role">Intent Classification Model</span>
          </div>
        </div>
      </section>

      {/* ── Final CTA Section ──────────────────────────────────────────────── */}
      <section className="landing-cta-banner">
        <div className="cta-card glass-card">
          <h2>Start exploring your AI workspace.</h2>
          <p>
            Experience multi-model intelligence and grounded document question answering today.
          </p>
          <div className="cta-buttons">
            <Link to="/signup" className="btn-hero-primary">
              <span>Get Started</span>
              <ArrowRight size={18} />
            </Link>
            <Link to="/login" className="btn-hero-secondary">
              <span>Sign In</span>
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────────────────── */}
      <footer className="landing-footer">
        <div className="footer-container">
          <div className="footer-col-main">
            <div className="footer-brand">
              <Bot size={20} className="footer-logo" />
              <span>NovaMind AI</span>
            </div>
            <p className="footer-tagline">
              Production RAG & Multi-Model Conversational Platform with verified document citations.
            </p>
          </div>

          <div className="footer-col">
            <h5>Navigation</h5>
            <Link to="/login">Sign In</Link>
            <Link to="/signup">Create Account</Link>
            <Link to="/chat">Workspace</Link>
            <Link to="/dashboard">System Dashboard</Link>
          </div>

          <div className="footer-col">
            <h5>Resources</h5>
            <a href="https://github.com/Satyamshiv0079/ai-chatbot" target="_blank" rel="noopener noreferrer" className="footer-ext-link">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
                <path d="M9 18c-4.51 2-5-2-7-2" />
              </svg>
              <span>GitHub Repository</span>
              <ExternalLink size={12} />
            </a>
            <a href="https://console.groq.com" target="_blank" rel="noopener noreferrer" className="footer-ext-link">
              <Zap size={14} />
              <span>Groq Cloud API</span>
              <ExternalLink size={12} />
            </a>
          </div>
        </div>

        <div className="footer-bottom">
          <p>&copy; {new Date().getFullYear()} NovaMind AI. Designed and built by Satyam.</p>
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;
