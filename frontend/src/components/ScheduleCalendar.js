import React, { useMemo } from 'react';
import '../styles/ScheduleCalendar.css';

const DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
const DAY_SHORT = { Monday: 'Mon', Tuesday: 'Tue', Wednesday: 'Wed', Thursday: 'Thu', Friday: 'Fri' };
const DAY_ABBREVIATIONS = { M: 'Monday', T: 'Tuesday', W: 'Wednesday', Th: 'Thursday', F: 'Friday' };

const COURSE_COLORS = [
  { bg: 'rgba(249,112,102,0.22)', border: 'rgba(249,112,102,0.45)', text: '#f97066' },
  { bg: 'rgba(45,212,191,0.18)',  border: 'rgba(45,212,191,0.45)',  text: '#2dd4bf' },
  { bg: 'rgba(167,139,250,0.18)', border: 'rgba(167,139,250,0.45)', text: '#a78bfa' },
  { bg: 'rgba(251,191,36,0.18)',  border: 'rgba(251,191,36,0.45)',  text: '#fbbf24' },
  { bg: 'rgba(56,189,248,0.18)',  border: 'rgba(56,189,248,0.45)',  text: '#38bdf8' },
  { bg: 'rgba(251,113,133,0.18)', border: 'rgba(251,113,133,0.45)', text: '#fb7185' },
];

const START_HOUR = 8;
const END_HOUR = 21;
const TOTAL_HOURS = END_HOUR - START_HOUR;
const HOUR_HEIGHT = 72; // px per hour
const HOURS = Array.from({ length: TOTAL_HOURS }, (_, i) => i + START_HOUR);

function ScheduleCalendar({ recommendedCourses }) {
  const courseColorMap = useMemo(() => {
    const map = {};
    if (!recommendedCourses) return map;
    recommendedCourses.forEach((course, i) => {
      map[course.code] = COURSE_COLORS[i % COURSE_COLORS.length];
    });
    return map;
  }, [recommendedCourses]);

  const scheduleEvents = useMemo(() => {
    const events = [];
    if (!recommendedCourses || !Array.isArray(recommendedCourses)) return events;

    recommendedCourses.forEach((course) => {
      if (!course.sections || !Array.isArray(course.sections)) return;
      course.sections.forEach((section) => {
        if (!section.meeting_times || !Array.isArray(section.meeting_times)) return;
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
              instructor: section.instructor || 'TBA',
              room: meeting.location || section.location || 'TBA',
            });
          });
        });
      });
    });

    return events;
  }, [recommendedCourses]);

  // Compute the visible hour range based on actual events
  const { visibleStart, visibleEnd } = useMemo(() => {
    if (scheduleEvents.length === 0) return { visibleStart: 8, visibleEnd: 18 };
    let minH = 24, maxH = 0;
    scheduleEvents.forEach(e => {
      if (e.startHour < minH) minH = e.startHour;
      if (e.endHour > maxH) maxH = e.endHour;
      if (e.endMinute > 0 && e.endHour + 1 > maxH) maxH = e.endHour + 1;
    });
    return {
      visibleStart: Math.max(START_HOUR, minH - 1),
      visibleEnd: Math.min(END_HOUR, maxH + 1),
    };
  }, [scheduleEvents]);

  const visibleHours = useMemo(() => {
    return HOURS.filter(h => h >= visibleStart && h < visibleEnd);
  }, [visibleStart, visibleEnd]);

  const gridHeight = (visibleEnd - visibleStart) * HOUR_HEIGHT;

  const eventsByDay = useMemo(() => {
    const map = {};
    DAYS_OF_WEEK.forEach(day => {
      map[day] = scheduleEvents.filter(e => e.day === day);
    });
    return map;
  }, [scheduleEvents]);

  const getEventStyle = (event) => {
    const startMinutes = (event.startHour - visibleStart) * 60 + event.startMinute;
    const endMinutes = (event.endHour - visibleStart) * 60 + event.endMinute;
    const duration = endMinutes - startMinutes;
    const totalMinutes = (visibleEnd - visibleStart) * 60;

    const top = (startMinutes / totalMinutes) * 100;
    const height = (duration / totalMinutes) * 100;
    const color = courseColorMap[event.courseCode] || COURSE_COLORS[0];

    return {
      top: `${top}%`,
      height: `${height}%`,
      background: color.bg,
      borderColor: color.border,
      '--event-text': color.text,
    };
  };

  return (
    <div className="schedule-calendar-container">
      <div className="calendar-info">
        <h3>Weekly Schedule</h3>
        {scheduleEvents.length === 0 && (
          <p className="no-courses">No courses scheduled</p>
        )}
      </div>

      <div className="calendar-wrapper">
        {/* Day headers */}
        <div className="calendar-header">
          <div className="time-gutter-header" />
          {DAYS_OF_WEEK.map(day => (
            <div key={day} className="day-header">{DAY_SHORT[day]}</div>
          ))}
        </div>

        {/* Grid body */}
        <div className="calendar-body" style={{ height: gridHeight }}>
          {/* Time gutter */}
          <div className="time-gutter">
            {visibleHours.map(hour => (
              <div
                key={hour}
                className="time-label"
                style={{
                  top: `${((hour - visibleStart) / (visibleEnd - visibleStart)) * 100}%`,
                }}
              >
                {formatHour(hour)}
              </div>
            ))}
          </div>

          {/* Day columns */}
          {DAYS_OF_WEEK.map(day => (
            <div key={day} className="day-column">
              {/* Hour gridlines */}
              {visibleHours.map(hour => (
                <div
                  key={hour}
                  className="hour-line"
                  style={{
                    top: `${((hour - visibleStart) / (visibleEnd - visibleStart)) * 100}%`,
                  }}
                />
              ))}

              {/* Events */}
              {eventsByDay[day].map((event, idx) => (
                <div
                  key={idx}
                  className="event-block"
                  style={getEventStyle(event)}
                  title={`${event.courseCode}: ${event.courseTitle} — ${event.instructor} (${event.room})`}
                >
                  <span className="event-code">{event.courseCode}</span>
                  <span className="event-title">{event.courseTitle}</span>
                  <span className="event-time">
                    {formatTime(event.startHour, event.startMinute)} - {formatTime(event.endHour, event.endMinute)}
                  </span>
                  <span className="event-room">{event.room}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      {scheduleEvents.length > 0 && (
        <div className="calendar-legend">
          {recommendedCourses?.map((course, idx) => {
            const color = courseColorMap[course.code] || COURSE_COLORS[0];
            return (
              <div key={idx} className="legend-item">
                <span className="legend-dot" style={{ background: color.text }} />
                <span className="legend-code" style={{ color: color.text }}>{course.code}</span>
                <span className="legend-title">{course.title}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function parseTime(timeStr) {
  if (!timeStr) return { hour: 8, minute: 0 };
  const match = timeStr.match(/(\d{1,2}):(\d{2})/);
  if (!match) return { hour: 8, minute: 0 };
  return { hour: parseInt(match[1]), minute: parseInt(match[2]) };
}

function formatHour(hour) {
  if (hour === 12) return '12 PM';
  if (hour < 12) return `${hour} AM`;
  return `${hour - 12} PM`;
}

function formatTime(hour, minute) {
  const ampm = hour >= 12 ? 'pm' : 'am';
  const displayHour = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour;
  return `${displayHour}:${minute.toString().padStart(2, '0')}${ampm}`;
}

export default ScheduleCalendar;
