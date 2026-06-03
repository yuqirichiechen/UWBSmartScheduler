import React, { useState } from 'react';
import '../styles/CompletedCourses.css';

// The common CSS major sequence — quick toggles so students don't have to type.
const COMMON_COURSES = [
  'CSS 142', 'CSS 143', 'CSS 161', 'CSS 211', 'CSS 301',
  'CSS 342', 'CSS 343', 'CSS 360', 'CSS 370', 'CSS 382',
];

function CompletedCourses({ courses = [], onUpdate, compact = false }) {
  const [input, setInput] = useState('');

  const has = (code) => courses.includes(code);

  const toggle = (code) => {
    onUpdate(has(code) ? courses.filter((c) => c !== code) : [...courses, code]);
  };

  const addTyped = () => {
    const code = input.toUpperCase().trim().replace(/\s+/g, ' ');
    if (code && !courses.includes(code)) {
      onUpdate([...courses, code]);
    }
    setInput('');
  };

  const remove = (code) => onUpdate(courses.filter((c) => c !== code));

  return (
    <section className={`completed ${compact ? 'compact' : ''}`}>
      <div className="completed-head">
        <h3 className="completed-title">Courses you've already completed</h3>
        <p className="completed-help">
          Used to check prerequisites and avoid recommending classes you've taken.
        </p>
      </div>

      <div className="completed-quick">
        {COMMON_COURSES.map((code) => (
          <button
            key={code}
            type="button"
            className={`quick-chip ${has(code) ? 'on' : ''}`}
            onClick={() => toggle(code)}
            aria-pressed={has(code)}
          >
            {has(code) && <Check />}
            {code}
          </button>
        ))}
      </div>

      <div className="completed-add">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value.toUpperCase())}
          onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTyped())}
          placeholder="Add another course, e.g. CSS 225"
          className="completed-input"
        />
        <button
          type="button"
          className="completed-add-btn"
          onClick={addTyped}
          disabled={!input.trim()}
        >
          Add
        </button>
      </div>

      {courses.length > 0 && (
        <div className="completed-selected">
          {courses.map((code) => (
            <span key={code} className="selected-chip">
              {code}
              <button
                type="button"
                className="selected-remove"
                onClick={() => remove(code)}
                aria-label={`Remove ${code}`}
              >
                ×
              </button>
            </span>
          ))}
          <button type="button" className="clear-all" onClick={() => onUpdate([])}>
            Clear all
          </button>
        </div>
      )}
    </section>
  );
}

function Check() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="20 6 9 17 4 12"></polyline>
    </svg>
  );
}

export default CompletedCourses;
