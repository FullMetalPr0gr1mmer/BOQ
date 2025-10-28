import React, { useState, useEffect, useRef } from 'react';
import { FiSend, FiMessageSquare, FiUser, FiLoader, FiX, FiFileText, FiStar, FiPaperclip, FiUpload, FiTrash2 } from 'react-icons/fi';
import { apiCall } from '../api';
import '../css/ChatSidebar.css';

const ChatSidebar = ({ isOpen, onClose, projectContext }) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' or 'documents'
  const [attachedFile, setAttachedFile] = useState(null);
  const [uploadedDocuments, setUploadedDocuments] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize welcome message
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setMessages([
        {
          role: 'assistant',
          content: getWelcomeMessage(),
          timestamp: new Date().toISOString()
        }
      ]);
    }
  }, [isOpen]);

  const getWelcomeMessage = () => {
    const baseMessage = `Hello! I'm Alfred and I'll be your assisstant for today.

I can help you with:
• Creating and managing projects (BOQ, RAN, ROP)
• Searching for sites and inventory
• Analyzing project data and pricing
• Answering questions about uploaded documents

What would you like to do today?`;

    if (projectContext) {
      return `You're currently viewing ${projectContext.type.toUpperCase()} project #${projectContext.id}.\n\n${baseMessage}`;
    }

    return baseMessage;
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      // Validate file type
      const allowedTypes = ['.pdf', '.docx', '.doc', '.txt'];
      const fileExt = '.' + file.name.split('.').pop().toLowerCase();

      if (!allowedTypes.includes(fileExt)) {
        alert(`Unsupported file type. Allowed: ${allowedTypes.join(', ')}`);
        return;
      }

      // Validate file size (max 50MB)
      if (file.size > 50 * 1024 * 1024) {
        alert('File size must be less than 50MB');
        return;
      }

      setAttachedFile(file);
    }
  };

  const handleRemoveAttachment = () => {
    setAttachedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleUploadFile = async () => {
    if (!attachedFile) return;

    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', attachedFile);
      formData.append('auto_process', 'true');
      formData.append('extract_tags', 'true');

      if (projectContext) {
        formData.append('project_type', projectContext.type);
        formData.append('project_id', projectContext.id);
      }

      const token = localStorage.getItem('token');
      console.log('Uploading file:', attachedFile.name, 'Token available:', !!token);

      const response = await fetch('http://localhost:8003/ai/documents/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      console.log('Upload response status:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Upload error response:', errorText);
        throw new Error(`Upload failed: ${response.status} - ${errorText}`);
      }

      const result = await response.json();
      console.log('Upload successful:', result);

      // Add system message about upload
      const uploadMessage = {
        role: 'assistant',
        content: `✅ Successfully uploaded "${attachedFile.name}". The document is being processed and will be available for questions shortly.`,
        timestamp: new Date().toISOString(),
        uploadedDocument: {
          id: result.document_id,
          filename: result.filename,
          status: result.processing_status
        }
      };

      setMessages(prev => [...prev, uploadMessage]);
      setUploadedDocuments(prev => [...prev, result]);
      setAttachedFile(null);

      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }

      // Auto-suggest asking about the document
      setTimeout(() => {
        setInputMessage(`What is this document about?`);
      }, 500);

    } catch (error) {
      console.error('Upload error:', error);
      const errorMessage = {
        role: 'assistant',
        content: `❌ Failed to upload "${attachedFile.name}". Please try again.`,
        timestamp: new Date().toISOString(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsUploading(false);
    }
  };

  const handleSendMessage = async () => {
    if ((!inputMessage.trim() && !attachedFile) || isLoading) return;

    // If there's an attached file, upload it first
    if (attachedFile) {
      await handleUploadFile();
      return;
    }

    const userMessage = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await apiCall('/ai/chat', {
        method: 'POST',
        body: JSON.stringify({
          message: inputMessage,
          conversation_id: conversationId,
          project_context: projectContext
        })
      });

      const assistantMessage = {
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString(),
        actions: response.actions_taken,
        data: response.data,
        sources: response.sources
      };

      setMessages(prev => [...prev, assistantMessage]);
      setConversationId(response.conversation_id);

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

  const QuickAction = ({ icon: Icon, text, onClick }) => (
    <button className="sidebar-quick-action" onClick={onClick}>
      <Icon size={16} />
      <span>{text}</span>
    </button>
  );

  const getQuickActions = () => {
    const actions = [];

    if (projectContext) {
      actions.push({
        icon: FiStar,
        text: "Summarize this project",
        action: () => setInputMessage(`Give me a summary of ${projectContext.type} project #${projectContext.id}`)
      });
      actions.push({
        icon: FiFileText,
        text: "Analyze pricing",
        action: () => setInputMessage(`Analyze pricing for ${projectContext.type} project #${projectContext.id}`)
      });
    }

    actions.push(
      {
        icon: FiStar,
        text: "Create new project",
        action: () => setInputMessage("I want to create a new project")
      },
      {
        icon: FiFileText,
        text: "Search projects",
        action: () => setInputMessage("Search for projects")
      }
    );

    return actions;
  };

  if (!isOpen) return null;

  return (
    <div className="chat-sidebar">
      <div className="sidebar-header">
        <div className="sidebar-header-content">
          <FiMessageSquare size={24} />
          <div className="sidebar-title">
            <h2>AI Assistant</h2>
            {projectContext && (
              <span className="sidebar-context">
                {projectContext.type.toUpperCase()} #{projectContext.id}
              </span>
            )}
          </div>
        </div>
        <button className="sidebar-close-btn" onClick={onClose}>
          <FiX size={20} />
        </button>
      </div>

      <div className="sidebar-tabs">
        <button
          className={`sidebar-tab ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          <FiMessageSquare size={16} />
          Chat
        </button>
        <button
          className={`sidebar-tab ${activeTab === 'documents' ? 'active' : ''}`}
          onClick={() => setActiveTab('documents')}
        >
          <FiFileText size={16} />
          Documents
        </button>
      </div>

      {activeTab === 'chat' && (
        <>
          <div className="sidebar-messages">
            {messages.map((message, index) => (
              <div key={index} className={`sidebar-message ${message.role}`}>
                <div className="message-avatar">
                  {message.role === 'user' ? <FiUser size={16} /> : <FiMessageSquare size={16} />}
                </div>
                <div className="message-bubble">
                  <div className="message-text">{message.content}</div>

                  {message.actions && message.actions.length > 0 && (
                    <div className="message-actions-list">
                      <strong>Actions:</strong>
                      <ul>
                        {message.actions.map((action, i) => (
                          <li key={i}>{action.replace(/_/g, ' ')}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {message.data && (
                    <div className="message-data-block">
                      <pre>{JSON.stringify(message.data, null, 2)}</pre>
                    </div>
                  )}

                  {message.sources && message.sources.length > 0 && (
                    <div className="message-sources-list">
                      <strong>Sources:</strong>
                      {message.sources.map((source, i) => (
                        <div key={i} className="source-card">
                          <div className="source-filename">{source.filename}</div>
                          {source.page_number && (
                            <div className="source-page">Page {source.page_number}</div>
                          )}
                          <div className="source-text">{source.chunk_text}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="message-time">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="sidebar-message assistant">
                <div className="message-avatar">
                  <FiMessageSquare size={16} />
                </div>
                <div className="message-bubble">
                  <FiLoader className="spinner" size={16} />
                  <span className="typing-text">Thinking...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {messages.length === 1 && (
            <div className="sidebar-quick-actions">
              <div className="quick-actions-title">Quick Actions</div>
              <div className="quick-actions-grid">
                {getQuickActions().map((action, index) => (
                  <QuickAction
                    key={index}
                    icon={action.icon}
                    text={action.text}
                    onClick={action.action}
                  />
                ))}
              </div>
            </div>
          )}

          <div className="sidebar-input-area">
            {attachedFile && (
              <div className="attached-file-preview">
                <div className="attached-file-info">
                  <FiFileText size={16} />
                  <span className="attached-file-name">{attachedFile.name}</span>
                  <span className="attached-file-size">
                    ({(attachedFile.size / 1024).toFixed(1)} KB)
                  </span>
                </div>
                <button
                  className="remove-attachment-btn"
                  onClick={handleRemoveAttachment}
                  title="Remove attachment"
                >
                  <FiX size={16} />
                </button>
              </div>
            )}

            <div className="input-controls">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileSelect}
                accept=".pdf,.doc,.docx,.txt"
                style={{ display: 'none' }}
              />
              <button
                className="attach-file-btn"
                onClick={() => fileInputRef.current?.click()}
                disabled={isLoading || isUploading}
                title="Attach document (PDF, DOC, DOCX, TXT)"
              >
                <FiPaperclip size={18} />
              </button>

              <textarea
                className="sidebar-input"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={attachedFile ? "Press Send to upload..." : "Ask me anything or attach a document..."}
                rows={2}
                disabled={isLoading || isUploading}
              />

              <button
                className="sidebar-send-btn"
                onClick={handleSendMessage}
                disabled={isLoading || isUploading || (!inputMessage.trim() && !attachedFile)}
                title={attachedFile ? "Upload file" : "Send message"}
              >
                {isUploading ? (
                  <FiLoader className="spinner" size={18} />
                ) : attachedFile ? (
                  <FiUpload size={18} />
                ) : (
                  <FiSend size={18} />
                )}
              </button>
            </div>
          </div>
        </>
      )}

      {activeTab === 'documents' && (
        <div className="sidebar-documents-tab">
          <div className="documents-placeholder">
            <FiFileText size={48} />
            <h3>Document Management</h3>
            <p>Upload and manage your project documents here.</p>
            <p className="coming-soon">Document upload interface coming soon...</p>
            <button
              className="switch-to-chat-btn"
              onClick={() => setActiveTab('chat')}
            >
              Go to Chat
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatSidebar;
