import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Loader, X, Minimize2, Maximize2 } from 'react-icons/react-icons/fi';
import api from '../api';
import '../css/ChatInterface.css';

const ChatInterface = ({ isOpen, onClose, projectContext }) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [isMinimized, setIsMinimized] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load conversation history on mount
  useEffect(() => {
    if (isOpen && !conversationId) {
      // Initialize with a welcome message
      setMessages([
        {
          role: 'assistant',
          content: `Hello! I'm your BOQ AI assistant. I can help you with:
• Creating and managing projects (BOQ, RAN, ROP)
• Searching for sites and inventory
• Analyzing project data
• Answering questions about uploaded documents

What would you like to do today?`,
          timestamp: new Date().toISOString()
        }
      ]);
    }
  }, [isOpen]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    // Add user message to chat
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await api.post('/ai/chat', {
        message: inputMessage,
        conversation_id: conversationId,
        project_context: projectContext
      });

      const assistantMessage = {
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date().toISOString(),
        actions: response.data.actions_taken,
        data: response.data.data,
        sources: response.data.sources
      };

      setMessages(prev => [...prev, assistantMessage]);
      setConversationId(response.data.conversation_id);

    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const QuickAction = ({ text, onClick }) => (
    <button className="quick-action-btn" onClick={onClick}>
      {text}
    </button>
  );

  const suggestQuickActions = () => {
    const actions = [];

    if (projectContext) {
      actions.push(
        <QuickAction
          key="summarize"
          text="Summarize this project"
          onClick={() => setInputMessage(`Summarize project ${projectContext.type} #${projectContext.id}`)}
        />
      );
    }

    actions.push(
      <QuickAction
        key="create"
        text="Create new project"
        onClick={() => setInputMessage("I want to create a new project")}
      />,
      <QuickAction
        key="search"
        text="Search inventory"
        onClick={() => setInputMessage("Search inventory for")}
      />
    );

    return actions;
  };

  if (!isOpen) return null;

  return (
    <div className={`chat-container ${isMinimized ? 'minimized' : ''}`}>
      <div className="chat-header">
        <div className="chat-header-left">
          <Bot size={20} />
          <span className="chat-title">AI Assistant</span>
          {projectContext && (
            <span className="context-badge">
              {projectContext.type.toUpperCase()} #{projectContext.id}
            </span>
          )}
        </div>
        <div className="chat-header-actions">
          <button
            className="header-btn"
            onClick={() => setIsMinimized(!isMinimized)}
            title={isMinimized ? "Maximize" : "Minimize"}
          >
            {isMinimized ? <Maximize2 size={16} /> : <Minimize2 size={16} />}
          </button>
          <button className="header-btn" onClick={onClose} title="Close">
            <X size={16} />
          </button>
        </div>
      </div>

      {!isMinimized && (
        <>
          <div className="chat-messages">
            {messages.map((message, index) => (
              <div key={index} className={`message ${message.role}`}>
                <div className="message-icon">
                  {message.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                </div>
                <div className="message-content">
                  <div className="message-text">{message.content}</div>

                  {message.actions && message.actions.length > 0 && (
                    <div className="message-actions">
                      <strong>Actions performed:</strong>
                      <ul>
                        {message.actions.map((action, i) => (
                          <li key={i}>{action}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {message.data && (
                    <div className="message-data">
                      <pre>{JSON.stringify(message.data, null, 2)}</pre>
                    </div>
                  )}

                  {message.sources && message.sources.length > 0 && (
                    <div className="message-sources">
                      <strong>Sources:</strong>
                      {message.sources.map((source, i) => (
                        <div key={i} className="source-item">
                          <span className="source-filename">{source.filename}</span>
                          {source.page_number && <span> (Page {source.page_number})</span>}
                          <div className="source-snippet">{source.chunk_text}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="message-timestamp">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="message assistant">
                <div className="message-icon">
                  <Bot size={16} />
                </div>
                <div className="message-content">
                  <Loader className="spinner" size={16} />
                  <span className="typing-indicator">Thinking...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {messages.length === 1 && (
            <div className="quick-actions">
              {suggestQuickActions()}
            </div>
          )}

          <div className="chat-input-container">
            <textarea
              className="chat-input"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me anything about your projects..."
              rows={1}
              disabled={isLoading}
            />
            <button
              className="send-button"
              onClick={handleSendMessage}
              disabled={isLoading || !inputMessage.trim()}
            >
              <Send size={18} />
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default ChatInterface;
