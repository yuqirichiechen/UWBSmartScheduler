import React from 'react';
import '../styles/ClarifyingQuestions.css';
import CompletedCourses from './CompletedCourses';

/**
 * Shown before generating when the student's request is open-ended
 * ("what should I take?") and we don't yet know what they've completed.
 * Mirrors the way an advisor (or Claude) asks a clarifying question first.
 */
function ClarifyingQuestions({ query, completedCourses, onUpdateCompleted, onContinue, onSkip }) {
  return (
    <section className="clarify" role="dialog" aria-label="A quick question first">
      <div className="clarify-bubble">
        <div className="clarify-avatar">SS</div>
        <div className="clarify-text">
          <p className="clarify-lead">
            Happy to help you figure out what to take. First — <strong>which courses
            have you already finished?</strong>
          </p>
          <p className="clarify-sub">
            That lets me skip what you've done and only suggest classes you're
            actually eligible for. Tap the ones you've completed:
          </p>
        </div>
      </div>

      <div className="clarify-picker">
        <CompletedCourses
          courses={completedCourses}
          onUpdate={onUpdateCompleted}
          compact
        />
      </div>

      <div className="clarify-actions">
        <button type="button" className="clarify-primary" onClick={onContinue}>
          {completedCourses.length > 0
            ? `Build my schedule (${completedCourses.length} completed)`
            : 'Build my schedule'}
        </button>
        <button type="button" className="clarify-skip" onClick={onSkip}>
          I'm a new student — skip
        </button>
      </div>
    </section>
  );
}

export default ClarifyingQuestions;
