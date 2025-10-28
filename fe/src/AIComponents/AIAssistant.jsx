import React, { useState, useEffect } from 'react';
import { Bot } from 'react-icons/fi';
import ChatSidebar from './ChatSidebar';
import api from '../api';

/**
 * AI Assistant Wrapper Component
 *
 * This component handles:
 * 1. Role-based access control (only Senior_admins can see AI)
 * 2. Sidebar toggle button in navigation
 * 3. Project context management
 *
 * Usage:
 * <AIAssistant projectContext={{ type: 'boq', id: 123 }} />
 */
const AIAssistant = ({ projectContext = null }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [userRole, setUserRole] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkUserRole();
  }, []);

  const checkUserRole = async () => {
    try {
      // Get current user's role from localStorage or API
      const storedUser = localStorage.getItem('user');

      if (storedUser) {
        const user = JSON.parse(storedUser);
        setUserRole(user.role);
      } else {
        // Fetch user details from API if not in localStorage
        const response = await api.get('/me'); // Adjust endpoint as needed
        if (response.data && response.data.role) {
          setUserRole(response.data.role);
          localStorage.setItem('user', JSON.stringify(response.data));
        }
      }
    } catch (error) {
      console.error('Error checking user role:', error);
      // If error, don't show AI assistant
      setUserRole(null);
    } finally {
      setIsLoading(false);
    }
  };

  // Only show to Senior_admins
  const canAccessAI = () => {
    if (!userRole) return false;

    // Check if role is senior_admin (case-insensitive)
    const roleStr = typeof userRole === 'string'
      ? userRole.toLowerCase()
      : userRole.role_name?.toLowerCase();

    return roleStr === 'senior_admin';
  };

  if (isLoading) {
    return null; // Don't show anything while checking
  }

  if (!canAccessAI()) {
    return null; // Hide completely if not authorized
  }

  return (
    <>
      {/* Toggle Button for Sidebar */}
      <button
        className="ai-assistant-toggle"
        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
        title="AI Assistant (Senior Admin)"
      >
        <Bot size={20} />
        <span>AI Assistant</span>
      </button>

      {/* Sidebar */}
      <ChatSidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        projectContext={projectContext}
      />

      {/* CSS for toggle button */}
      <style jsx>{`
        .ai-assistant-toggle {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 16px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border: none;
          border-radius: 8px;
          font-size: 14px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
          box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
        }

        .ai-assistant-toggle:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .ai-assistant-toggle:active {
          transform: translateY(0);
        }

        /* For navigation/sidebar integration */
        .ai-assistant-toggle.nav-item {
          width: 100%;
          justify-content: flex-start;
          border-radius: 0;
          background: transparent;
          box-shadow: none;
        }

        .ai-assistant-toggle.nav-item:hover {
          background: rgba(102, 126, 234, 0.1);
          transform: none;
        }
      `}</style>
    </>
  );
};

export default AIAssistant;
