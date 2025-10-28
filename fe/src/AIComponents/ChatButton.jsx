import React, { useState } from 'react';
import { MessageCircle } from 'react-icons/fi';
import ChatInterface from './ChatInterface';
import '../css/ChatInterface.css';

const ChatButton = ({ projectContext }) => {
  const [isChatOpen, setIsChatOpen] = useState(false);

  return (
    <>
      {!isChatOpen && (
        <button
          className="chat-toggle-btn"
          onClick={() => setIsChatOpen(true)}
          title="Open AI Assistant"
        >
          <MessageCircle size={28} />
        </button>
      )}

      <ChatInterface
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        projectContext={projectContext}
      />
    </>
  );
};

export default ChatButton;
