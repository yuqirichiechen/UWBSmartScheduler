import React from 'react';
import '../styles/ScheduleOutput.css';
import ScheduleCalendar from './ScheduleCalendar';

const DAY_NAMES = { M: 'Mon', T: 'Tue', W: 'Wed', Th: 'Thu', F: 'Fri' };

function ScheduleOutput({ schedule }) {
  if (!schedule) return null;

  const {
    query,
    recommended_courses = [],
    is_valid,
    issues = [],
  } = schedule;

  const totalCredits = recommended_courses.reduce(
    (sum, c) => sum + (c.credits || 0), 0
  );

  return (
    <div className="schedule-output-container">
      <div className="output-header">
        <div className="header-content">
          <h2>Your Schedule</h2>
          <div className="header-meta">
            {totalCredits > 0 && (
              <span className="credit-total">{totalCredits} credits</span>
            )}
            <div className={`status-badge ${is_valid ? 'valid' : 'invalid'}`}>
              {is_valid ? 'No Conflicts' : 'Has Issues'}
            </div>
          </div>
        </div>
        <p className="query-echo">{query}</p>
      </div>

      {issues && issues.length > 0 && (
        <div className="issues-section">
          <h3>Scheduling Issues</h3>
          <ul className="issues-list">
            {issues.map((issue, index) => (
              <li key={index}>{issue}</li>
            ))}
          </ul>
        </div>
      )}

      {recommended_courses && recommended_courses.length > 0 && (
        <>
          <ScheduleCalendar recommendedCourses={recommended_courses} />

          <div className="course-details">
            <h3>Course Details</h3>
            <div className="courses-grid">
              {recommended_courses.map((course, idx) => (
                <div key={idx} className="course-card">
                  <div className="course-card-top">
                    <h4>{course.code}</h4>
                    <span className="credits">{course.credits} cr</span>
                  </div>
                  <p className="course-title">{course.title}</p>

                  {course.sections && course.sections.length > 0 && (
                    <div className="sections">
                      {course.sections.map((section, sidx) => (
                        <div key={sidx} className="section">
                          <div className="section-top">
                            <span className="section-num">Sec {section.section_number}</span>
                            <span className="instructor">{section.instructor || 'TBA'}</span>
                          </div>
                          {section.meeting_times && section.meeting_times.map((mt, mtidx) => (
                            <div key={mtidx} className="meeting-line">
                              <span className="meeting-days">
                                {(Array.isArray(mt.days) ? mt.days : [mt.days])
                                  .map(d => DAY_NAMES[d] || d).join(' / ')}
                              </span>
                              <span className="meeting-time">{formatTimeStr(mt.start_time)} - {formatTimeStr(mt.end_time)}</span>
                              <span className="meeting-loc">{mt.location || section.location || 'TBA'}</span>
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>
                  )}

                  {course.prerequisites && course.prerequisites.length > 0 && (
                    <div className="prerequisites">
                      Prereqs: {course.prerequisites.join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {(!recommended_courses || recommended_courses.length === 0) && (
        <div className="no-courses-message">
          <p>No courses could be recommended. Try adjusting your constraints.</p>
        </div>
      )}
    </div>
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
