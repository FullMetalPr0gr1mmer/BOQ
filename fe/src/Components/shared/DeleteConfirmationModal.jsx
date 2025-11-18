import React from 'react';
import '../../css/DeleteConfirmationModal.css';

/**
 * Reusable Delete Confirmation Modal Component
 *
 * @param {Object} props
 * @param {boolean} props.show - Controls visibility of the modal
 * @param {Function} props.onConfirm - Callback when user confirms deletion
 * @param {Function} props.onCancel - Callback when user cancels deletion
 * @param {string} props.title - Modal title
 * @param {string} props.itemName - Name of the item being deleted (will be bolded)
 * @param {string} props.warningText - Main warning text before item name
 * @param {string} props.additionalInfo - Additional information text (optional)
 * @param {Array<string>} props.affectedItems - List of items that will be affected
 * @param {string} props.confirmButtonText - Text for confirm button (default: "Delete")
 * @param {boolean} props.loading - Shows loading state on confirm button
 */
export default function DeleteConfirmationModal({
  show,
  onConfirm,
  onCancel,
  title = "Confirm Deletion",
  itemName = "",
  warningText = "Are you sure you want to delete",
  additionalInfo = "This will also permanently delete all related:",
  affectedItems = [],
  confirmButtonText = "Delete",
  loading = false
}) {
  if (!show) return null;

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget && !loading) {
      onCancel();
    }
  };

  return (
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div className="modal-container delete-modal">
        <div className="modal-header-delete">
          <div className="warning-icon">⚠️</div>
          <h2 className="modal-title">{title}</h2>
        </div>

        <div className="modal-body-delete">
          <p className="delete-warning-text">
            {warningText} {itemName && <strong>"{itemName}"</strong>}?
          </p>

          {affectedItems && affectedItems.length > 0 && (
            <>
              <p className="delete-info-text">{additionalInfo}</p>
              <ul className="delete-items-list">
                {affectedItems.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </>
          )}

          <p className="delete-warning-note">
            ⚠️ This action cannot be undone.
          </p>
        </div>

        <div className="modal-footer-delete">
          <button
            type="button"
            className="btn-cancel"
            onClick={onCancel}
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn-delete-confirm"
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? 'Deleting...' : confirmButtonText}
          </button>
        </div>
      </div>
    </div>
  );
}
