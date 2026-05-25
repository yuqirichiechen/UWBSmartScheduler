import React, { useState } from 'react';
import '../styles/QueryInput.css';

function QueryInput({ onSubmit, loading }) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSubmit(query);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const exampleQueries = [
    "CSS core requirements, only Tue/Thu, max 14 credits",
    "Morning classes only, I work afternoons",
    "No Friday classes, can't drive to campus",
    "CSS 342 + CSS 385, keep it under 12 credits",
  ];

  return (
    <div className="query-input-container">
      <div className="input-section">
        <h2>What does your ideal schedule look like?</h2>
        <p className="subtitle">Describe your preferences in plain English</p>

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="e.g., I want CSS core requirements, mostly Tuesday and Thursday, max 14 credits..."
              className="query-textarea"
              disabled={loading}
              rows="3"
            />
          </div>

          <button
            type="submit"
            className="submit-button"
            disabled={loading || !query.trim()}
          >
            {loading ? 'Generating...' : 'Generate Schedule'}
          </button>
        </form>

        <div className="examples">
          <p className="examples-title">Try an example</p>
          <div className="example-buttons">
            {exampleQueries.map((example, idx) => (
              <button
                key={idx}
                onClick={() => setQuery(example)}
                className="example-button"
                disabled={loading}
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="tips-section">
        <h3>Tips</h3>
        <ul>
          <li><strong>Be specific</strong> &mdash; name courses or departments</li>
          <li><strong>Set constraints</strong> &mdash; days, times, credit limits</li>
          <li><strong>Add completed courses</strong> &mdash; for prerequisite checks</li>
          <li><strong>State preferences</strong> &mdash; morning, afternoon, in-person</li>
        </ul>
      </div>
    </div>
  );
}

export default QueryInput;
