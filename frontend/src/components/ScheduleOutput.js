import React from 'react';
import '../styles/ScheduleOutput.css';
import ScheduleCalendar from './ScheduleCalendar';

function ScheduleOutput({ schedule }) {
  if (!schedule) {
    return null;
  }

  const {
    query,
    recommendations,
    recommended_courses = [],
    is_valid,
    issues = [],
  } = schedule;

  return (
    <div className="schedule-output-container">
      <div className="output-header">
        <div className="header-content">
          <h2>Schedule Recommendations</h2>
          <div className={`status-badge ${is_valid ? 'valid' : 'invalid'}`}>
            {is_valid ? '✓ Valid Schedule' : '✗ Has Issues'}
          </div>
        </div>
      </div>

      <div className="query-recap">
        <h3>Your Request:</h3>
        <p>{query}</p>
      </div>

      <div className="recommendations-section">
        <h3>AI Recommendations:</h3>
        <div className="recommendations-text">
          {recommendations}
        </div>
      </div>

      {issues && issues.length > 0 && (
        <div className="issues-section">
          <h3>⚠️ Scheduling Issues:</h3>
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
            <h3>Recommended Courses</h3>
            <div className="courses-grid">
              {recommended_courses.map((course, idx) => (
                <div key={idx} className="course-card">
                  <div className="course-header">
                    <h4>{course.code}</h4>
                    <span className="credits">{course.credits} credits</span>
                  </div>
                  <p className="course-title">{course.title}</p>

                  {course.sections && course.sections.length > 0 && (
                    <div className="sections">
                      {course.sections.map((section, sidx) => (
                        <div key={sidx} className="section">
                          <div className="section-header">
                            <span className="section-num">Section {section.section_number}</span>
                            <span className="instructor">{section.instructor || 'TBA'}</span>
                          </div>
                          {section.meeting_times && section.meeting_times.length > 0 && (
                            <div className="meeting-times">
                              {section.meeting_times.map((mt, mtidx) => (
                                <div key={mtidx} className="meeting-time">
                                  <strong>
                                    {Array.isArray(mt.days) ? mt.days.join(' ') : mt.days}
                                  </strong>
                                  {' '}
                                  {mt.start_time} - {mt.end_time}
                                </div>
                              ))}
                            </div>
                          )}
                          <div className="section-meta">
                            📍 {section.location || 'TBA'} | 👥 {section.enrollment || 'N/A'}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {course.prerequisites && course.prerequisites.length > 0 && (
                    <div className="prerequisites">
                      <strong>Prerequisites:</strong> {course.prerequisites.join(', ')}
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

export default ScheduleOutput;
