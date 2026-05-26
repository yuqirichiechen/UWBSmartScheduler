import React from 'react';
import '../styles/ScheduleOutput.css';
import ScheduleCalendar from './ScheduleCalendar';

const DAY_NAMES = { M: 'Mon', T: 'Tue', W: 'Wed', Th: 'Thu', F: 'Fri' };

function ScheduleOutput({ schedule }) {
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

      {recommended_courses && recommended_courses.length > 0 ? (
        <>
          <ScheduleCalendar recommendedCourses={recommended_courses} />

          <section className="course-list">
            <h3 className="section-eyebrow">Selected sections</h3>
            <ul className="course-rows">
              {recommended_courses.map((course, idx) => (
                <CourseRow key={idx} course={course} />
              ))}
            </ul>
          </section>
        </>
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

export default ScheduleOutput;
