import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check, User, Bot } from 'lucide-react';
import './ChatWindow.css';

function MessageBubble({ message }) {
  const isBot = message.sender === 'bot';
  const [copied, setCopied] = useState(false);

  const handleCopy = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const [displayedText, setDisplayedText] = useState(isBot && message.isNew ? '' : message.text);
  
  useEffect(() => {
    if (!isBot || !message.isNew) return;
    
    let currentIndex = 0;
    const speed = 2; // characters per tick
    
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

  return (
    <div className={`message-wrapper ${isBot ? 'bot-wrapper' : 'user-wrapper'}`}>
      {isBot && (
        <div className="avatar bot-avatar">
          <Bot size={20} />
        </div>
      )}

      <div className={`message-bubble ${isBot ? 'bot-bubble' : 'user-bubble'}`}>
        {isBot ? (
          <div className="markdown-content">
            <ReactMarkdown
              components={{
                code({ node, inline, className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '');
                  const codeString = String(children).replace(/\n$/, '');
                  return !inline && match ? (
                    <div className="code-block-container">
                      <div className="code-block-header">
                        <span className="code-language">{match[1]}</span>
                        <button 
                          className="copy-button"
                          onClick={() => handleCopy(codeString)}
                          title="Copy Code"
                        >
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
                        customStyle={{ margin: 0, borderRadius: '0 0 6px 6px' }}
                      />
                    </div>
                  ) : (
                    <code {...props} className={className ? className : 'inline-code'}>
                      {children}
                    </code>
                  );
                }
              }}
            >
              {displayedText}
            </ReactMarkdown>
            
            <div className="message-actions">
               <button 
                  className="icon-action-btn"
                  onClick={() => handleCopy(message.text)}
                  title="Copy message"
                >
                  {copied ? <Check size={14} /> : <Copy size={14} />}
                </button>
            </div>
          </div>
        ) : (
          <p className="message-text">{message.text}</p>
        )}

        {isBot && message.intent && (
          <p className="intent-label">
            Intent: {message.intent} ({(message.confidence * 100).toFixed(1)}%)
          </p>
        )}
      </div>

      {!isBot && (
        <div className="avatar user-avatar">
          <User size={20} />
        </div>
      )}
    </div>
  );
}

export default MessageBubble;