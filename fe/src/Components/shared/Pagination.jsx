import React from 'react';
import './Pagination.css';

/**
 * Pagination Component
 *
 * A reusable pagination control with previous/next buttons and page information.
 *
 * @param {Object} props
 * @param {number} currentPage - Current page number (1-indexed)
 * @param {number} totalPages - Total number of pages
 * @param {Function} onPageChange - Handler for page changes, receives new page number
 * @param {string} previousText - Text for previous button (default: "← Previous")
 * @param {string} nextText - Text for next button (default: "Next →")
 */
export default function Pagination({
  currentPage = 1,
  totalPages = 1,
  onPageChange,
  previousText = '← Previous',
  nextText = 'Next →'
}) {
  // Don't render if there's only one page
  if (totalPages <= 1) {
    return null;
  }

  const handlePrevious = () => {
    if (currentPage > 1) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNext = () => {
    if (currentPage < totalPages) {
      onPageChange(currentPage + 1);
    }
  };

  return (
    <div className="pagination">
      <button
        className="pagination-btn"
        disabled={currentPage === 1}
        onClick={handlePrevious}
      >
        {previousText}
      </button>
      <span className="pagination-info">
        Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong>
      </span>
      <button
        className="pagination-btn"
        disabled={currentPage === totalPages}
        onClick={handleNext}
      >
        {nextText}
      </button>
    </div>
  );
}
