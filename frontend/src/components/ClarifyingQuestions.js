import React, { useState } from 'react';
import '../styles/ClarifyingQuestions.css';

/**
 * Advisor-style clarifying step shown before generating when a request is vague.
 * Presents an AI-generated multiple-choice question (3 options) plus an "Other"
 * free-text choice — mirroring the way Claude asks a clarifying question.
 */
function ClarifyingQuestions({
  query,
  question,
  options = [],
  loadingQuestion,
  onAnswer,
  onSkip,
}) {
  const [otherOpen, setOtherOpen] = useState(false);
  const [otherText, setOtherText] = useState('');

  const submitOther = () => {
    const t = otherText.trim();
    if (t) onAnswer(t);
  };

  return (
    <section className="clarify" role="dialog" aria-label="A quick question first">
      <div className="clarify-bubble">
        <div className="clarify-avatar">SS</div>
        <div className="clarify-text">
          {query && <div className="clarify-echo">“{query}”</div>}
          {loadingQuestion ? (
            <p className="clarify-lead clarify-loading">
              <span className="dot" /> <span className="dot" /> <span className="dot" />
            </p>
          ) : (
            <p className="clarify-lead">{question}</p>
          )}
          <p className="clarify-sub">
            Pick the closest option so I can tailor your schedule — or write your own.
          </p>
        </div>
      </div>

      {!loadingQuestion && (
        <div className="clarify-options">
          {options.map((opt, i) => (
            <button
              key={i}
              type="button"
              className="clarify-option"
              onClick={() => onAnswer(opt)}
            >
              <span className="clarify-option-key">{String.fromCharCode(65 + i)}</span>
              <span className="clarify-option-label">{opt}</span>
            </button>
          ))}

          {/* Other / free-text */}
          {!otherOpen ? (
            <button
              type="button"
              className="clarify-option other"
              onClick={() => setOtherOpen(true)}
            >
              <span className="clarify-option-key">＋</span>
              <span className="clarify-option-label">Other — let me explain…</span>
            </button>
          ) : (
            <div className="clarify-other-row">
              <input
                autoFocus
                type="text"
                className="clarify-other-input"
                placeholder="Type your answer…"
                value={otherText}
                onChange={(e) => setOtherText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && submitOther()}
              />
              <button
                type="button"
                className="clarify-other-send"
                onClick={submitOther}
                disabled={!otherText.trim()}
              >
                Send
              </button>
            </div>
          )}
        </div>
      )}

      <button type="button" className="clarify-skip" onClick={onSkip}>
        Skip — just build something
      </button>
    </section>
  );
}

export default ClarifyingQuestions;
