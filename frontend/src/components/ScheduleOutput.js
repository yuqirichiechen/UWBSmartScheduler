import React, { useState } from 'react';
import '../styles/ScheduleOutput.css';
import ScheduleCalendar from './ScheduleCalendar';

const DAY_NAMES = { M: 'Mon', T: 'Tue', W: 'Wed', Th: 'Thu', F: 'Fri' };

function ScheduleOutput({ schedule }) {
  const [activeTab, setActiveTab] = useState('calendar');

  if (!schedule) return null;

  const {
    query,
    recommended_courses = [],
    recommendations,
    is_valid,
    issues = [],
  } = schedule;

  const totalCredits = recommended_courses.reduce(
    (sum, c) => sum + (c.credits || 0), 0
  );

  const hasResults = recommended_courses && recommended_courses.length > 0;

  return (
    <div className="schedule-output">
      {/* Header */}
      <header className="schedule-header">
        <div className="schedule-header-top">
          <div>
            <h2 className="schedule-title">Your schedule</h2>
            {query && <p className="query-echo">“{query}”</p>}
          </div>
          <div className="header-meta">
            {totalCredits > 0 && (
              <span className="credit-total">{totalCredits} credits</span>
            )}
            <span className={`status-badge ${is_valid ? 'valid' : 'invalid'}`}>
              {is_valid ? 'No Conflicts' : 'Has Issues'}
            </span>
          </div>
        </div>

        {recommendations && (
          <p className="schedule-summary">{recommendations}</p>
        )}
      </header>

      {/* Issues */}
      {issues && issues.length > 0 && (
        <section className="issues-section">
          <h3>Scheduling issues</h3>
          <ul className="issues-list">
            {issues.map((issue, i) => <li key={i}>{issue}</li>)}
          </ul>
        </section>
      )}

      {hasResults ? (
        <section className="schedule-tabs">
          <div className="tabs" role="tablist" aria-label="Schedule views">
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'calendar'}
              className={`tab ${activeTab === 'calendar' ? 'active' : ''}`}
              onClick={() => setActiveTab('calendar')}
            >
              <CalendarIcon /> Calendar
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'courses'}
              className={`tab ${activeTab === 'courses' ? 'active' : ''}`}
              onClick={() => setActiveTab('courses')}
            >
              <ListIcon /> Sections
              <span className="tab-count">{recommended_courses.length}</span>
            </button>
          </div>

          <div className="tab-panel" role="tabpanel">
            {activeTab === 'calendar' && (
              <ScheduleCalendar recommendedCourses={recommended_courses} />
            )}
            {activeTab === 'courses' && (
              <ul className="course-rows">
                {recommended_courses.map((course, idx) => (
                  <CourseRow key={idx} course={course} />
                ))}
              </ul>
            )}
          </div>
        </section>
      ) : (
        <div className="no-courses-message">
          <p>No courses could be recommended. Try relaxing a constraint.</p>
        </div>
      )}
    </div>
  );
}

function CourseRow({ course }) {
  const section = course.sections && course.sections[0];
  const meeting = section && section.meeting_times && section.meeting_times[0];

  return (
    <li className="course-row">
      <div className="course-row-left">
        <div className="course-code">{course.code}</div>
        <div className="course-row-title">{course.title}</div>
        {course.prerequisites && course.prerequisites.length > 0 && (
          <div className="course-row-prereqs">
            requires {course.prerequisites.join(', ')}
          </div>
        )}
      </div>

      <div className="course-row-meeting">
        {section && (
          <span className="section-pill">Sec {section.section_number}</span>
        )}
        {meeting && meeting.days && (
          <span className="meeting-days">
            {(Array.isArray(meeting.days) ? meeting.days : [meeting.days])
              .map(d => DAY_NAMES[d] || d).join(' · ')}
          </span>
        )}
        {meeting && (
          <span className="meeting-time">
            {formatTimeStr(meeting.start_time)} – {formatTimeStr(meeting.end_time)}
          </span>
        )}
      </div>

      <div className="course-row-right">
        <span className="course-credits">{course.credits} cr</span>
        <span className="course-instructor">
          {section ? (section.instructor || 'TBA') : 'TBA'}
        </span>
        <span className="course-location">
          {(meeting && meeting.location) || (section && section.location) || 'TBA'}
        </span>
      </div>
    </li>
  );
}

function formatTimeStr(timeStr) {
  if (!timeStr) return '';
  const match = timeStr.match(/(\d{1,2}):(\d{2})/);
  if (!match) return timeStr;
  let hour = parseInt(match[1]);
  const minute = match[2];
  const ampm = hour >= 12 ? 'pm' : 'am';
  if (hour > 12) hour -= 12;
  if (hour === 0) hour = 12;
  return `${hour}:${minute}${ampm}`;
}

/* tiny inline icons — keeps bundle small */
function CalendarIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="4" width="18" height="18" rx="2"></rect>
      <line x1="16" y1="2" x2="16" y2="6"></line>
      <line x1="8" y1="2" x2="8" y2="6"></line>
      <line x1="3" y1="10" x2="21" y2="10"></line>
    </svg>
  );
}
function ListIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="8" y1="6" x2="21" y2="6"></line>
      <line x1="8" y1="12" x2="21" y2="12"></line>
      <line x1="8" y1="18" x2="21" y2="18"></line>
      <line x1="3" y1="6" x2="3.01" y2="6"></line>
      <line x1="3" y1="12" x2="3.01" y2="12"></line>
      <line x1="3" y1="18" x2="3.01" y2="18"></line>
    </svg>
  );
}

export default ScheduleOutput;
