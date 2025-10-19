import React, { useState } from 'react';
import './StatsCarousel.css';

/**
 * StatsCarousel Component
 *
 * A carousel-style statistics display that shows a limited number of stat cards
 * with navigation arrows to cycle through all available cards.
 *
 * @param {Array} cards - Array of stat card objects with structure:
 *   - label: string (card title)
 *   - value: string|number (displayed value, if not editable)
 *   - isEditable: boolean (optional, marks card as interactive)
 *   - component: React element (optional, custom component for editable cards)
 * @param {number} visibleCount - Number of cards to display at once (default: 3)
 */
export default function StatsCarousel({ cards = [], visibleCount = 3 }) {
  const [visibleCardStart, setVisibleCardStart] = useState(0);

  const handlePrevCard = () => {
    setVisibleCardStart((prev) => (prev > 0 ? prev - 1 : cards.length - 1));
  };

  const handleNextCard = () => {
    setVisibleCardStart((prev) => (prev < cards.length - 1 ? prev + 1 : 0));
  };

  const getVisibleCards = () => {
    const visible = [];
    for (let i = 0; i < visibleCount; i++) {
      const index = (visibleCardStart + i) % cards.length;
      visible.push(cards[index]);
    }
    return visible;
  };

  // Don't render if no cards provided
  if (!cards || cards.length === 0) {
    return null;
  }

  return (
    <div className="stats-bar-container">
      <button
        className="stats-nav-btn stats-nav-left"
        onClick={handlePrevCard}
        title="Previous card"
      >
        ‹
      </button>
      <div
        className="stats-bar"
        style={{ gridTemplateColumns: `repeat(${visibleCount}, 1fr)` }}
      >
        {getVisibleCards().map((card, idx) => (
          <div
            key={`${card.label}-${idx}`}
            className={`stat-item ${card.isEditable ? 'stat-item-editable' : ''}`}
          >
            <span className="stat-label">{card.label}</span>
            {card.isEditable ? (
              card.component
            ) : (
              <span className="stat-value">{card.value}</span>
            )}
          </div>
        ))}
      </div>
      <button
        className="stats-nav-btn stats-nav-right"
        onClick={handleNextCard}
        title="Next card"
      >
        ›
      </button>
    </div>
  );
}
