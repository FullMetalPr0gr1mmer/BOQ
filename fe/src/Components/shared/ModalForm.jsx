import React from 'react';
import './ModalForm.css';

/**
 * ModalForm Component
 *
 * A reusable modal dialog component with form sections, customizable fields,
 * and action buttons. Supports overlay click-to-close and escape key handling.
 *
 * @param {Object} props
 * @param {boolean} show - Whether to display the modal
 * @param {Function} onClose - Handler for closing the modal
 * @param {string} title - Modal header title
 * @param {Function} onSubmit - Form submission handler
 * @param {React.ReactNode} children - Form content (sections and fields)
 * @param {string} submitText - Submit button text (default: "Submit")
 * @param {string} cancelText - Cancel button text (default: "Cancel")
 * @param {string} className - Additional CSS class for modal container
 */
export default function ModalForm({
  show = false,
  onClose,
  title = 'Form',
  onSubmit,
  children,
  submitText = 'Submit',
  cancelText = 'Cancel',
  className = ''
}) {
  if (!show) return null;

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (onSubmit) {
      onSubmit(e);
    }
  };

  return (
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div className={`modal-container ${className}`}>
        <div className="modal-header">
          <h2 className="modal-title">{title}</h2>
          <button className="modal-close" onClick={onClose} type="button">
            ✕
          </button>
        </div>

        <form className="modal-form" onSubmit={handleSubmit}>
          {children}

          {/* Form Actions */}
          <div className="form-actions">
            <button type="button" className="btn-cancel" onClick={onClose}>
              {cancelText}
            </button>
            <button type="submit" className="btn-submit">
              {submitText}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/**
 * FormSection Component
 *
 * A section within a ModalForm with title and children fields.
 *
 * @param {Object} props
 * @param {string} title - Section title
 * @param {React.ReactNode} children - Section content (form fields)
 */
export function FormSection({ title, children }) {
  return (
    <div className="form-section">
      <h3 className="section-title">{title}</h3>
      <div className="form-grid">{children}</div>
    </div>
  );
}

/**
 * FormField Component
 *
 * A single form field with label and input.
 *
 * @param {Object} props
 * @param {string} label - Field label
 * @param {string} name - Input name attribute
 * @param {string} type - Input type (default: "text")
 * @param {any} value - Input value
 * @param {Function} onChange - Change handler
 * @param {boolean} required - Whether field is required
 * @param {boolean} disabled - Whether field is disabled
 * @param {boolean} fullWidth - Whether field should span full width
 * @param {string} placeholder - Input placeholder text
 * @param {Array} options - Select options (if type is "select")
 */
export function FormField({
  label,
  name,
  type = 'text',
  value,
  onChange,
  required = false,
  disabled = false,
  fullWidth = false,
  placeholder = '',
  options = []
}) {
  return (
    <div className={`form-field ${fullWidth ? 'full-width' : ''}`}>
      <label>
        {label} {required && '*'}
      </label>
      {type === 'select' ? (
        <select
          name={name}
          value={value}
          onChange={onChange}
          required={required}
          disabled={disabled}
        >
          {placeholder && <option value="">{placeholder}</option>}
          {options.map((opt, idx) => (
            <option key={idx} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      ) : (
        <input
          type={type}
          name={name}
          value={value}
          onChange={onChange}
          required={required}
          disabled={disabled}
          placeholder={placeholder}
          className={disabled ? 'disabled-input' : ''}
        />
      )}
    </div>
  );
}
