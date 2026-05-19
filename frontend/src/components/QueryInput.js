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

  const exampleQueries = [
    "I want CSS core requirements, only Tuesday and Thursday, max 14 credits",
    "Schedule me for morning classes only, I have work in the afternoon",
    "No Friday classes, I can't drive to campus that day",
    "I need CSS 342, CSS 385, and one elective. Keep it under 12 credits",
  ];

  const fillExample = (example) => {
    setQuery(example);
  };

  return (
    <div className="query-input-container">
      <div className="input-section">
        <h2>Describe Your Schedule</h2>
        <p className="subtitle">Enter your scheduling preferences in plain English</p>

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., I want CSS core requirements, mostly Tuesday and Thursday, max 14 credits"
              className="query-textarea"
              disabled={loading}
              rows="4"
            />
          </div>

          <button
            type="submit"
            className="submit-button"
            disabled={loading || !query.trim()}
          >
            {loading ? 'Generating schedule...' : 'Generate Schedule'}
          </button>
        </form>

        <div className="examples">
          <p className="examples-title">💡 Example queries:</p>
          <div className="example-buttons">
            {exampleQueries.map((example, idx) => (
              <button
                key={idx}
                onClick={() => fillExample(example)}
                className="example-button"
                disabled={loading}
                title={example}
              >
                {example.substring(0, 50)}...
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="tips-section">
        <h3>💬 Tips for better results:</h3>
        <ul>
          <li><strong>Be specific:</strong> Mention exact courses or departments</li>
          <li><strong>Mention constraints:</strong> Days, times, credit limits</li>
          <li><strong>List completed courses:</strong> Use the form to add them</li>
          <li><strong>Include preferences:</strong> Morning/afternoon, online/in-person</li>
        </ul>
      </div>
    </div>
  );
}

export default QueryInput;
