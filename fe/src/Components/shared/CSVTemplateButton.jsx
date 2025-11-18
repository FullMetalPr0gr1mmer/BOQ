import React from 'react';
import '../../css/shared/DownloadButton.css';

/**
 * Reusable CSV Template Download Button Component
 *
 * @param {Object} props
 * @param {Function} props.onDownload - Function to call when button is clicked (usually a template downloader)
 * @param {string} props.label - Button label text (default: "Download CSV Template")
 * @param {string} props.icon - Button icon (default: "📥")
 * @param {string} props.variant - Button variant: 'primary' | 'success' | 'small' (default: 'primary')
 * @param {string} props.className - Additional CSS classes
 * @param {boolean} props.disabled - Disable the button
 *
 * @example
 * import CSVTemplateButton from './shared/CSVTemplateButton';
 * import { downloadSiteUploadTemplate } from '../utils/csvTemplateDownloader';
 *
 * <CSVTemplateButton
 *   onDownload={downloadSiteUploadTemplate}
 *   label="Download Site Template"
 * />
 */
export default function CSVTemplateButton({
  onDownload,
  label = 'Download CSV Template',
  icon = '📥',
  variant = 'primary',
  className = '',
  disabled = false
}) {
  const variantClass = variant === 'success' ? 'btn-success' : variant === 'small' ? 'btn-small' : '';

  return (
    <button
      className={`btn-download-template ${variantClass} ${className}`}
      onClick={onDownload}
      type="button"
      disabled={disabled}
    >
      {icon && <span className="btn-icon">{icon}</span>}
      {label}
    </button>
  );
}
