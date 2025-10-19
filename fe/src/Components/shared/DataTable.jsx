import React from 'react';
import './DataTable.css';

/**
 * DataTable Component
 *
 * A reusable table component with customizable columns, data rows, and action buttons.
 * Supports loading state, empty state, and responsive design.
 *
 * @param {Object} props
 * @param {Array} columns - Array of column configurations:
 *   - key: string (data key to display)
 *   - label: string (column header text)
 *   - render: function (optional, custom render function for cell content)
 * @param {Array} data - Array of data objects to display
 * @param {Array} actions - Array of action button configurations:
 *   - icon: string (button icon/emoji)
 *   - onClick: function (click handler receiving row item)
 *   - title: string (button tooltip)
 *   - className: string (optional, additional CSS class)
 * @param {boolean} loading - Whether data is loading
 * @param {string} noDataMessage - Message to display when no data available
 * @param {string} className - Additional CSS class for table wrapper
 */
export default function DataTable({
  columns = [],
  data = [],
  actions = [],
  loading = false,
  noDataMessage = 'No data found',
  className = ''
}) {
  const hasActions = actions && actions.length > 0;
  const totalColumns = columns.length + (hasActions ? 1 : 0);

  return (
    <div className={`data-table-wrapper ${className}`}>
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col, idx) => (
              <th key={idx}>{col.label}</th>
            ))}
            {hasActions && <th>Actions</th>}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 && !loading ? (
            <tr>
              <td colSpan={totalColumns} className="no-data">
                {noDataMessage}
              </td>
            </tr>
          ) : (
            data.map((row, rowIdx) => (
              <tr key={rowIdx}>
                {columns.map((col, colIdx) => (
                  <td key={colIdx}>
                    {col.render ? col.render(row) : row[col.key]}
                  </td>
                ))}
                {hasActions && (
                  <td>
                    <div className="action-buttons">
                      {actions.map((action, actionIdx) => (
                        <button
                          key={actionIdx}
                          className={`btn-action ${action.className || ''}`}
                          onClick={() => action.onClick(row)}
                          title={action.title}
                        >
                          {action.icon}
                        </button>
                      ))}
                    </div>
                  </td>
                )}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
