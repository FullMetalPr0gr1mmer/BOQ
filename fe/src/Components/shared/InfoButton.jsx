import React from 'react';
import './InfoButton.css';

/**
 * InfoButton Component
 *
 * A circular info button that opens a help modal. Typically used alongside page titles.
 *
 * @param {Object} props
 * @param {Function} onClick - Handler for button click
 * @param {string} title - Button tooltip text
 */
export function InfoButton({ onClick, title = 'How to use this component' }) {
  return (
    <button className="info-btn" onClick={onClick} title={title}>
      <span className="info-icon">i</span>
    </button>
  );
}

/**
 * TitleWithInfo Component
 *
 * A title row with centered title and left-positioned info button.
 *
 * @param {Object} props
 * @param {string} title - Page title text
 * @param {string} subtitle - Page subtitle text (optional)
 * @param {Function} onInfoClick - Handler for info button click
 * @param {string} infoTooltip - Tooltip text for info button
 */
export default function TitleWithInfo({
  title,
  subtitle,
  onInfoClick,
  infoTooltip = 'How to use this component'
}) {
  return (
    <div className="header-left">
      <div className="title-row">
        <InfoButton onClick={onInfoClick} title={infoTooltip} />
        <h1 className="page-title">{title}</h1>
      </div>
      {subtitle && <p className="page-subtitle">{subtitle}</p>}
    </div>
  );
}
