import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check, User, Bot } from 'lucide-react';
import './ChatWindow.css';

function MessageBubble({ message }) {
  const isBot = message.sender === 'bot';
  const [copied, setCopied] = useState(false);
  const bubbleRef = useRef(null);

  const handleCopy = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const [displayedText, setDisplayedText] = useState(isBot && message.isNew ? '' : message.text);

  useEffect(() => {
    if (!isBot || !message.isNew) return;
    let currentIndex = 0;
    const speed = 3;
    const interval = setInterval(() => {
      if (currentIndex <= message.text.length) {
        setDisplayedText(message.text.slice(0, currentIndex));
        currentIndex += speed;
      } else {
        setDisplayedText(message.text);
        clearInterval(interval);
      }
    }, 10);
    return () => clearInterval(interval);
  }, [message.text, isBot, message.isNew]);

  // 3D tilt on mouse move
  const handleMouseMove = (e) => {
    const el = bubbleRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const cx = rect.width / 2;
    const cy = rect.height / 2;
    const rotateX = ((y - cy) / cy) * -4;
    const rotateY = ((x - cx) / cx) * 4;
    el.style.transform = `perspective(800px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(4px)`;
  };

  const handleMouseLeave = () => {
    if (bubbleRef.current) {
      bubbleRef.current.style.transform = 'perspective(800px) rotateX(0deg) rotateY(0deg) translateZ(0px)';
    }
  };

  return (
    <div className={`message-wrapper ${isBot ? 'bot-wrapper' : 'user-wrapper'} spatial-entry`}>
      {isBot && (
        <div className="avatar bot-avatar spatial-avatar">
          <Bot size={18} />
        </div>
      )}

      <div
        ref={bubbleRef}
        className={`message-bubble ${isBot ? 'bot-bubble spatial-card' : 'user-bubble spatial-user-card'}`}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        {isBot ? (
          <div className="markdown-content">
            <ReactMarkdown
              components={{
                code({ node, inline, className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '');
                  const codeString = String(children).replace(/\n$/, '');
                  return !inline && match ? (
                    <div className="code-block-container spatial-code">
                      <div className="code-block-header">
                        <span className="code-language">{match[1]}</span>
                        <button className="copy-button" onClick={() => handleCopy(codeString)}>
                          {copied ? <Check size={14} /> : <Copy size={14} />}
                          <span>{copied ? 'Copied!' : 'Copy'}</span>
                        </button>
                      </div>
                      <SyntaxHighlighter
                        {...props}
                        children={codeString}
                        style={vscDarkPlus}
                        language={match[1]}
                        PreTag="div"
                        customStyle={{ margin: 0, borderRadius: '0 0 8px 8px' }}
                      />
                    </div>
                  ) : (
                    <code {...props} className={className || 'inline-code'}>{children}</code>
                  );
                }
              }}
            >
              {displayedText}
            </ReactMarkdown>

            <div className="message-actions">
              <button className="icon-action-btn" onClick={() => handleCopy(message.text)} title="Copy">
                {copied ? <Check size={13} /> : <Copy size={13} />}
              </button>
            </div>
          </div>
        ) : (
          <p className="message-text">{message.text}</p>
        )}
      </div>

      {!isBot && (
        <div className="avatar user-avatar spatial-avatar">
          <User size={18} />
        </div>
      )}
    </div>
  );
}

export default MessageBubble;