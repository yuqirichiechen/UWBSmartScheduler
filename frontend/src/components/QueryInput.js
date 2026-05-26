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
      <form onSubmit={handleSubmit} className="query-card">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. CSS core requirements, only Tuesday and Thursday, max 14 credits…"
          className="query-textarea"
          disabled={loading}
          rows="3"
        />

        <div className="query-card-footer">
          <span className="query-hint">Press <kbd>↵</kbd> to submit · <kbd>⇧↵</kbd> for newline</span>
          <button
            type="submit"
            className="submit-button"
            disabled={loading || !query.trim()}
          >
            {loading ? 'Generating…' : 'Generate Schedule'}
          </button>
        </div>
      </form>

      <div className="examples">
        <span className="examples-label">Try</span>
        {exampleQueries.map((example, idx) => (
          <button
            key={idx}
            onClick={() => setQuery(example)}
            className="example-chip"
            disabled={loading}
            title={example}
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
}

export default QueryInput;
