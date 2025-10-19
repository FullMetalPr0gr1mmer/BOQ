import React from 'react';
import './FilterBar.css';

/**
 * FilterBar Component
 *
 * A flexible filter bar component that displays search input, dropdown filters,
 * and conditional clear button. Supports customizable filter configurations.
 *
 * @param {Object} props
 * @param {string} searchTerm - Current search value
 * @param {Function} onSearchChange - Handler for search input changes
 * @param {string} searchPlaceholder - Placeholder text for search input (default: "Search...")
 * @param {Array} dropdowns - Array of dropdown filter configurations:
 *   - label: string (dropdown label)
 *   - value: string (current selected value)
 *   - onChange: function (change handler)
 *   - options: array of { value, label } objects
 *   - placeholder: string (optional, default option text)
 * @param {boolean} showClearButton - Whether to show clear search button
 * @param {Function} onClearSearch - Handler for clear button click
 * @param {string} clearButtonText - Text for clear button (default: "Clear Search")
 */
export default function FilterBar({
  searchTerm = '',
  onSearchChange,
  searchPlaceholder = 'Search...',
  dropdowns = [],
  showClearButton = false,
  onClearSearch,
  clearButtonText = 'Clear Search'
}) {
  return (
    <div className="filter-bar">
      {/* Search Input */}
      {onSearchChange && (
        <div className="filter-group">
          <label className="filter-label">Search</label>
          <input
            type="text"
            placeholder={searchPlaceholder}
            value={searchTerm}
            onChange={onSearchChange}
            className="filter-input"
          />
        </div>
      )}

      {/* Dynamic Dropdowns */}
      {dropdowns.map((dropdown, idx) => (
        <div key={idx} className="filter-group">
          <label className="filter-label">{dropdown.label}</label>
          <select
            className="filter-select"
            value={dropdown.value}
            onChange={dropdown.onChange}
          >
            {dropdown.placeholder && (
              <option value="">{dropdown.placeholder}</option>
            )}
            {dropdown.options.map((option, optIdx) => (
              <option key={optIdx} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      ))}

      {/* Clear Search Button */}
      {showClearButton && onClearSearch && (
        <button onClick={onClearSearch} className="btn-clear">
          {clearButtonText}
        </button>
      )}
    </div>
  );
}
