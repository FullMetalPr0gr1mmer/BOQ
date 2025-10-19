import React from 'react';
import './HelpModal.css';

/**
 * HelpModal Component
 *
 * A reusable help/documentation modal with customizable sections and content.
 * Displays user guide information with organized sections.
 *
 * @param {Object} props
 * @param {boolean} show - Whether to display the modal
 * @param {Function} onClose - Handler for closing the modal
 * @param {string} title - Modal title
 * @param {Array} sections - Array of help section objects:
 *   - icon: string (section icon/emoji)
 *   - title: string (section title)
 *   - content: React.ReactNode (section content - can be text, lists, or custom components)
 * @param {string} closeButtonText - Close button text (default: "Got it!")
 */
export default function HelpModal({
  show = false,
  onClose,
  title = 'User Guide',
  sections = [],
  closeButtonText = 'Got it!'
}) {
  if (!show) return null;

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div className="modal-container help-modal">
        <div className="modal-header">
          <h2 className="modal-title">{title}</h2>
          <button className="modal-close" onClick={onClose} type="button">
            ✕
          </button>
        </div>

        <div className="help-content">
          {sections.map((section, idx) => (
            <div key={idx} className="help-section">
              <h3 className="help-section-title">
                {section.icon && <span>{section.icon} </span>}
                {section.title}
              </h3>
              <div className="help-section-content">{section.content}</div>
            </div>
          ))}
        </div>

        <div className="help-footer">
          <button className="btn-submit" onClick={onClose}>
            {closeButtonText}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * HelpList Component
 *
 * A styled list for help content.
 *
 * @param {Object} props
 * @param {Array} items - Array of list items (strings or objects with { label, text })
 */
export function HelpList({ items = [] }) {
  return (
    <ul className="help-list">
      {items.map((item, idx) => (
        <li key={idx}>
          {typeof item === 'string' ? (
            item
          ) : (
            <>
              <strong>{item.label}:</strong> {item.text}
            </>
          )}
        </li>
      ))}
    </ul>
  );
}

/**
 * HelpText Component
 *
 * A styled text paragraph for help content.
 *
 * @param {Object} props
 * @param {React.ReactNode} children - Text content
 * @param {boolean} isNote - Whether to style as a note/warning
 */
export function HelpText({ children, isNote = false }) {
  return <p className={`help-text ${isNote ? 'help-note' : ''}`}>{children}</p>;
}

/**
 * CodeBlock Component
 *
 * A styled code block for displaying CSV headers or other code snippets.
 *
 * @param {Object} props
 * @param {Array} items - Array of code items to display
 */
export function CodeBlock({ items = [] }) {
  return (
    <div className="csv-headers">
      {items.map((item, idx) => (
        <React.Fragment key={idx}>
          <code>{item}</code>
          {idx < items.length - 1 && ', '}
        </React.Fragment>
      ))}
    </div>
  );
}
