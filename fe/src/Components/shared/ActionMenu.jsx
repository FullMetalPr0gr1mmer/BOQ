import React, { useState, useRef, useEffect } from 'react';
import './ActionMenu.css';

/**
 * ActionMenu Component
 *
 * A dropdown menu component that displays action buttons in a compact menu.
 * Solves the issue of too many action buttons overflowing at different zoom levels.
 *
 * @param {Array} actions - Array of action configurations:
 *   - icon: string (button icon/emoji)
 *   - onClick: function (click handler)
 *   - title: string (action label)
 *   - className: string (optional, for styling)
 * @param {Object} row - The data row object
 */
export default function ActionMenu({ actions = [], row }) {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0, maxHeight: 400 });
  const menuRef = useRef(null);
  const triggerRef = useRef(null);

  // Calculate dropdown position
  const calculatePosition = () => {
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      const dropdownWidth = 220;
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      const estimatedDropdownHeight = actions.length * 50 + 16; // Approximate height per item
      const maxDropdownHeight = 400; // Maximum height before scrolling

      let top = rect.bottom + 4;
      let left = rect.right - dropdownWidth;
      let maxHeight = maxDropdownHeight;

      // Check if dropdown would go below viewport
      const spaceBelow = viewportHeight - rect.bottom - 10;
      const spaceAbove = rect.top - 10;

      if (spaceBelow < Math.min(estimatedDropdownHeight, maxDropdownHeight)) {
        // Not enough space below, check if there's more space above
        if (spaceAbove > spaceBelow && spaceAbove > 250) {
          // Position above the button if there's good space
          top = rect.top - Math.min(estimatedDropdownHeight, spaceAbove, maxDropdownHeight) - 4;
          maxHeight = Math.min(spaceAbove - 4, maxDropdownHeight);
        } else {
          // Keep below but limit height to available space
          maxHeight = Math.max(spaceBelow - 4, 250);
        }
      }

      // Adjust if dropdown would go off-screen to the left
      if (left < 10) {
        left = rect.left;
      }

      // Adjust if dropdown would go off-screen to the right
      if (left + dropdownWidth > viewportWidth - 10) {
        left = viewportWidth - dropdownWidth - 10;
      }

      setPosition({ top, left, maxHeight });
    }
  };

  // Toggle menu and calculate position
  const handleToggle = () => {
    if (!isOpen) {
      calculatePosition();
    }
    setIsOpen(!isOpen);
  };

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  // Recalculate position on scroll or resize
  useEffect(() => {
    if (isOpen) {
      const handleRepositon = () => {
        calculatePosition();
      };

      window.addEventListener('scroll', handleRepositon, true);
      window.addEventListener('resize', handleRepositon);

      return () => {
        window.removeEventListener('scroll', handleRepositon, true);
        window.removeEventListener('resize', handleRepositon);
      };
    }
  }, [isOpen]);

  const handleActionClick = (action) => {
    action.onClick(row);
    setIsOpen(false);
  };

  return (
    <div className="action-menu" ref={menuRef}>
      <button
        ref={triggerRef}
        className="action-menu-trigger"
        onClick={handleToggle}
        title="Actions"
      >
        <span className="action-menu-icon">⋮</span>
      </button>

      {isOpen && (
        <div
          className="action-menu-dropdown"
          style={{
            top: `${position.top}px`,
            left: `${position.left}px`,
            maxHeight: `${position.maxHeight}px`
          }}
        >
          {actions.map((action, idx) => (
            <button
              key={idx}
              className={`action-menu-item ${action.className || ''}`}
              onClick={() => handleActionClick(action)}
              title={action.title}
            >
              <span className="action-menu-item-icon">{action.icon}</span>
              <span className="action-menu-item-text">{action.title}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
