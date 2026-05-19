import React, { useMemo } from 'react';
import '../styles/ScheduleCalendar.css';

const DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
const DAY_ABBREVIATIONS = {
  'M': 'Monday',
  'T': 'Tuesday',
  'W': 'Wednesday',
  'Th': 'Thursday',
  'F': 'Friday'
};

const HOURS = Array.from({ length: 13 }, (_, i) => i + 8); // 8am to 8pm

function ScheduleCalendar({ recommendedCourses }) {
  const scheduleEvents = useMemo(() => {
    const events = [];

    if (!recommendedCourses || !Array.isArray(recommendedCourses)) {
      return events;
    }

    recommendedCourses.forEach((course) => {
      if (course.sections && Array.isArray(course.sections)) {
        course.sections.forEach((section) => {
          if (section.meeting_times && Array.isArray(section.meeting_times)) {
            section.meeting_times.forEach((meeting) => {
              const days = Array.isArray(meeting.days) ? meeting.days : [meeting.days];
              const startTime = parseTime(meeting.start_time);
              const endTime = parseTime(meeting.end_time);

              days.forEach((day) => {
                const dayName = DAY_ABBREVIATIONS[day] || day;
                events.push({
                  day: dayName,
                  startHour: startTime.hour,
                  startMinute: startTime.minute,
                  endHour: endTime.hour,
                  endMinute: endTime.minute,
                  courseCode: course.code,
                  courseTitle: course.title,
                  section: section.section_number,
                  instructor: section.instructor || 'TBA',
                  room: section.location || 'TBA',
                });
              });
            });
          }
        });
      }
    });

    return events;
  }, [recommendedCourses]);

  const getPositionAndHeight = (event) => {
    const totalMinutesFromStart = (event.startHour - 8) * 60 + event.startMinute;
    const durationMinutes = (event.endHour - event.startHour) * 60 + 
                           (event.endMinute - event.startMinute);
    
    const topPercent = (totalMinutesFromStart / (13 * 60)) * 100;
    const heightPercent = (durationMinutes / (13 * 60)) * 100;

    return {
      top: `${topPercent}%`,
      height: `${heightPercent}%`,
    };
  };

  const eventsByDay = useMemo(() => {
    const map = {};
    DAYS_OF_WEEK.forEach(day => {
      map[day] = scheduleEvents.filter(e => e.day === day);
    });
    return map;
  }, [scheduleEvents]);

  const hasConflicts = useMemo(() => {
    return DAYS_OF_WEEK.some(day => {
      const dayEvents = eventsByDay[day];
      for (let i = 0; i < dayEvents.length; i++) {
        for (let j = i + 1; j < dayEvents.length; j++) {
          const e1 = dayEvents[i];
          const e2 = dayEvents[j];
          const e1End = e1.startHour * 60 + e1.endMinute;
          const e2Start = e2.startHour * 60 + e2.startMinute;
          const e2End = e2.startHour * 60 + e2.endMinute;
          const e1Start = e1.startHour * 60 + e1.startMinute;

          if (e1End > e2Start && e1Start < e2End) {
            return true;
          }
        }
      }
      return false;
    });
  }, [eventsByDay]);

  return (
    <div className="schedule-calendar-container">
      <div className="calendar-info">
        <h3>Weekly Schedule View</h3>
        {hasConflicts && (
          <div className="conflict-warning">
            ⚠️ Scheduling conflicts detected
          </div>
        )}
        {scheduleEvents.length === 0 && (
          <p className="no-courses">No courses scheduled</p>
        )}
      </div>

      <div className="calendar-wrapper">
        <div className="calendar-grid">
          {/* Time header */}
          <div className="time-slot header" />
          
          {/* Day headers */}
          {DAYS_OF_WEEK.map(day => (
            <div key={day} className="day-header">
              {day.substring(0, 3)}
            </div>
          ))}

          {/* Time slots and events */}
          {HOURS.map(hour => (
            <React.Fragment key={hour}>
              {/* Hour label */}
              <div className="time-slot">
                <span className="time-label">{formatHour(hour)}</span>
              </div>

              {/* Events for this hour on each day */}
              {DAYS_OF_WEEK.map(day => (
                <div key={`${day}-${hour}`} className="calendar-cell">
                  {eventsByDay[day]
                    .filter(event => {
                      return event.startHour === hour ||
                        (event.startHour < hour && event.endHour > hour);
                    })
                    .map((event, idx) => (
                      <div
                        key={idx}
                        className="event"
                        style={getPositionAndHeight(event)}
                        title={`${event.courseCode} - ${event.instructor} (${event.room})`}
                      >
                        <div className="event-content">
                          <div className="event-code">{event.courseCode}</div>
                          <div className="event-time">
                            {formatTime(event.startHour, event.startMinute)} - {formatTime(event.endHour, event.endMinute)}
                          </div>
                          <div className="event-room">{event.room}</div>
                        </div>
                      </div>
                    ))}
                </div>
              ))}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Event legend */}
      {scheduleEvents.length > 0 && (
        <div className="event-details">
          <h4>Scheduled Courses</h4>
          <div className="event-list">
            {recommendedCourses?.map((course, idx) => (
              <div key={idx} className="course-item">
                <div className="course-header">
                  <span className="course-code">{course.code}</span>
                  <span className="course-title">{course.title}</span>
                </div>
                {course.sections?.map((section, sidx) => (
                  <div key={sidx} className="section-item">
                    <div className="section-info">
                      <span className="section-num">Section {section.section_number}</span>
                      <span className="instructor">{section.instructor || 'TBA'}</span>
                    </div>
                    <div className="meeting-times">
                      {section.meeting_times?.map((mt, mtidx) => (
                        <div key={mtidx} className="meeting-time">
                          {Array.isArray(mt.days) ? mt.days.join(' ') : mt.days} {mt.start_time} - {mt.end_time}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function parseTime(timeStr) {
  if (!timeStr) return { hour: 8, minute: 0 };
  const match = timeStr.match(/(\d{1,2}):(\d{2})/);
  if (!match) return { hour: 8, minute: 0 };
  return {
    hour: parseInt(match[1]),
    minute: parseInt(match[2])
  };
}

function formatHour(hour) {
  if (hour === 12) return '12pm';
  if (hour < 12) return `${hour}am`;
  return `${hour - 12}pm`;
}

function formatTime(hour, minute) {
  const ampm = hour >= 12 ? 'pm' : 'am';
  const displayHour = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour;
  return `${displayHour}:${minute.toString().padStart(2, '0')}${ampm}`;
}

export default ScheduleCalendar;
