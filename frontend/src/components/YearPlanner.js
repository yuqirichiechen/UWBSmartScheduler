import React, { useEffect, useMemo, useState } from 'react';
import '../styles/YearPlanner.css';
import ScheduleCalendar from './ScheduleCalendar';
import { scheduleAPI } from '../services/api';

const DAY_NAMES = { M: 'Mon', T: 'Tue', W: 'Wed', Th: 'Thu', F: 'Fri' };

const QUARTERS = [
  { id: 'autumn-2026', label: 'Autumn 2026', short: 'Aut' },
  { id: 'winter-2027', label: 'Winter 2027', short: 'Win' },
  { id: 'spring-2027', label: 'Spring 2027', short: 'Spr' },
  { id: 'summer-2027', label: 'Summer 2027', short: 'Sum', optional: true },
];

const STORAGE_KEY = 'smartsched.yearplan.v1';

// Each entry in a quarter is { code, sectionNumber } so we can pick a specific section
function loadPlan() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw);
  } catch {
    return {};
  }
}

function savePlan(plan) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(plan)); } catch {}
}

function YearPlanner() {
  const [activeQuarter, setActiveQuarter] = useState(QUARTERS[0].id);
  const [catalog, setCatalog] = useState([]);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [error, setError] = useState(null);
  const [plan, setPlan] = useState(loadPlan);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const res = await scheduleAPI.getCourses();
        setCatalog(res.courses || []);
      } catch (err) {
        setError(err.message || 'Failed to load catalog');
      } finally {
        setLoadingCatalog(false);
      }
    })();
  }, []);

  useEffect(() => { savePlan(plan); }, [plan]);

  const catalogByCode = useMemo(() => {
    const map = {};
    for (const c of catalog) map[c.code] = c;
    return map;
  }, [catalog]);

  const entries = useMemo(
    () => plan[activeQuarter] || [],
    [plan, activeQuarter]
  );

  // Hydrate the plan entries into full course+section objects for rendering
  const hydratedCourses = useMemo(() => {
    return entries.map((entry) => {
      const course = catalogByCode[entry.code];
      if (!course) return null;
      const sections = course.sections || [];
      const chosen = sections.find(s => s.section_number === entry.sectionNumber)
                  || sections[0]
                  || null;
      return {
        code: course.code,
        title: course.title,
        credits: course.credit_hours || course.credits || 0,
        prerequisites: course.prerequisites || [],
        sections: chosen ? [chosen] : [],
        _allSections: sections,
        _chosenSectionNumber: chosen ? chosen.section_number : null,
      };
    }).filter(Boolean);
  }, [entries, catalogByCode]);

  const totalCredits = hydratedCourses.reduce((s, c) => s + (c.credits || 0), 0);

  const conflicts = useMemo(() => {
    return detectConflicts(hydratedCourses);
  }, [hydratedCourses]);

  const addCourse = (code) => {
    const course = catalogByCode[code];
    if (!course) return;
    const sectionNumber = course.sections && course.sections[0]
      ? course.sections[0].section_number
      : null;
    setPlan((prev) => {
      const list = prev[activeQuarter] || [];
      if (list.some(e => e.code === code)) return prev; // already added
      return { ...prev, [activeQuarter]: [...list, { code, sectionNumber }] };
    });
    setSearchOpen(false);
    setSearchQuery('');
  };

  const removeCourse = (code) => {
    setPlan((prev) => {
      const list = (prev[activeQuarter] || []).filter(e => e.code !== code);
      return { ...prev, [activeQuarter]: list };
    });
  };

  const changeSection = (code, sectionNumber) => {
    setPlan((prev) => {
      const list = (prev[activeQuarter] || []).map(e =>
        e.code === code ? { ...e, sectionNumber } : e
      );
      return { ...prev, [activeQuarter]: list };
    });
  };

  const clearQuarter = () => {
    if (entries.length === 0) return;
    if (!window.confirm(`Clear all courses from ${QUARTERS.find(q=>q.id===activeQuarter).label}?`)) return;
    setPlan((prev) => ({ ...prev, [activeQuarter]: [] }));
  };

  const searchResults = useMemo(() => {
    if (!searchOpen) return [];
    const q = searchQuery.toLowerCase().trim();
    const alreadyAdded = new Set(entries.map(e => e.code));
    let list = catalog.filter(c => !alreadyAdded.has(c.code));
    if (q) {
      list = list.filter(c =>
        c.code.toLowerCase().includes(q) ||
        (c.title || '').toLowerCase().includes(q)
      );
    }
    return list.slice(0, 20);
  }, [searchOpen, searchQuery, catalog, entries]);

  return (
    <section className="planner">
      <header className="planner-header">
        <div>
          <h2 className="planner-title">Year planner</h2>
          <p className="planner-sub">
            Manually build a quarter-by-quarter schedule. Add courses, pick sections, and see
            conflicts in real time. Saved to this browser.
          </p>
        </div>
      </header>

      {/* Quarter tabs */}
      <div className="quarter-tabs" role="tablist">
        {QUARTERS.map((q) => {
          const count = (plan[q.id] || []).length;
          return (
            <button
              key={q.id}
              type="button"
              role="tab"
              aria-selected={activeQuarter === q.id}
              className={`quarter-tab ${activeQuarter === q.id ? 'active' : ''} ${q.optional ? 'optional' : ''}`}
              onClick={() => setActiveQuarter(q.id)}
            >
              <span className="quarter-tab-label">{q.label}</span>
              {count > 0 && <span className="quarter-tab-count">{count}</span>}
              {q.optional && <span className="quarter-tab-optional">optional</span>}
            </button>
          );
        })}
      </div>

      {/* Quarter summary strip */}
      <div className="quarter-summary">
        <div className="quarter-summary-left">
          <span className="quarter-summary-stat">
            <strong>{hydratedCourses.length}</strong> {hydratedCourses.length === 1 ? 'course' : 'courses'}
          </span>
          <span className="quarter-summary-dot">·</span>
          <span className="quarter-summary-stat">
            <strong>{totalCredits}</strong> credits
          </span>
          {conflicts.length > 0 ? (
            <span className="quarter-summary-status invalid">
              {conflicts.length} conflict{conflicts.length === 1 ? '' : 's'}
            </span>
          ) : hydratedCourses.length > 0 ? (
            <span className="quarter-summary-status valid">No conflicts</span>
          ) : null}
        </div>
        <div className="quarter-summary-actions">
          <button
            type="button"
            className="planner-action-btn primary"
            onClick={() => setSearchOpen(v => !v)}
            disabled={loadingCatalog}
          >
            {searchOpen ? 'Close' : '+ Add course'}
          </button>
          {hydratedCourses.length > 0 && (
            <button
              type="button"
              className="planner-action-btn ghost"
              onClick={clearQuarter}
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Add-course dropdown */}
      {searchOpen && (
        <div className="course-picker">
          <div className="course-picker-search">
            <input
              autoFocus
              type="text"
              placeholder="Search courses by code or title…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <ul className="course-picker-list">
            {loadingCatalog && <li className="course-picker-empty">Loading catalog…</li>}
            {!loadingCatalog && searchResults.length === 0 && (
              <li className="course-picker-empty">
                {catalog.length === 0 ? 'Catalog unavailable' : 'No matches'}
              </li>
            )}
            {searchResults.map((c) => (
              <li key={c.code}>
                <button
                  type="button"
                  className="course-picker-item"
                  onClick={() => addCourse(c.code)}
                >
                  <span className="course-picker-code">{c.code}</span>
                  <span className="course-picker-title">{c.title}</span>
                  <span className="course-picker-cr">{c.credit_hours || 0} cr</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      {/* Conflicts */}
      {conflicts.length > 0 && (
        <div className="issues-section">
          <h3>Time conflicts</h3>
          <ul className="issues-list">
            {conflicts.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </div>
      )}

      {/* Calendar + sections */}
      {hydratedCourses.length === 0 ? (
        <div className="planner-empty">
          <div className="planner-empty-mark">◇</div>
          <p>
            No courses planned for{' '}
            <strong>{QUARTERS.find(q => q.id === activeQuarter).label}</strong> yet.
          </p>
          <button
            type="button"
            className="planner-action-btn primary"
            onClick={() => setSearchOpen(true)}
          >
            + Add your first course
          </button>
        </div>
      ) : (
        <>
          <ScheduleCalendar recommendedCourses={hydratedCourses} />

          <section className="planner-section-list">
            <h3 className="section-eyebrow">Sections</h3>
            <ul className="course-rows">
              {hydratedCourses.map((course) => (
                <PlannerRow
                  key={course.code}
                  course={course}
                  onChangeSection={(sectionNumber) => changeSection(course.code, sectionNumber)}
                  onRemove={() => removeCourse(course.code)}
                />
              ))}
            </ul>
          </section>
        </>
      )}
    </section>
  );
}

function PlannerRow({ course, onChangeSection, onRemove }) {
  const section = course.sections[0];
  const meeting = section && section.meeting_times && section.meeting_times[0];

  return (
    <li className="course-row planner-row">
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
        {course._allSections && course._allSections.length > 1 ? (
          <select
            className="section-select"
            value={course._chosenSectionNumber || ''}
            onChange={(e) => onChangeSection(e.target.value)}
            aria-label={`Section for ${course.code}`}
          >
            {course._allSections.map((s) => (
              <option key={s.section_number} value={s.section_number}>
                Sec {s.section_number}
              </option>
            ))}
          </select>
        ) : section ? (
          <span className="section-pill">Sec {section.section_number}</span>
        ) : null}
        {meeting && meeting.days && (
          <span className="meeting-days">
            {(Array.isArray(meeting.days) ? meeting.days : [meeting.days])
              .filter(Boolean)
              .map(d => DAY_NAMES[d] || d).join(' · ') || 'Async'}
          </span>
        )}
        {meeting && meeting.start_time && (
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
        <button
          type="button"
          className="planner-remove"
          onClick={onRemove}
          aria-label={`Remove ${course.code}`}
          title={`Remove ${course.code}`}
        >
          ×
        </button>
      </div>
    </li>
  );
}

/* ---- conflict detection (client-side mirror of backend logic) ---- */
function detectConflicts(courses) {
  const issues = [];
  const events = [];
  for (const c of courses) {
    const sec = c.sections && c.sections[0];
    if (!sec) continue;
    for (const mt of sec.meeting_times || []) {
      const days = Array.isArray(mt.days) ? mt.days : [mt.days];
      for (const d of days.filter(Boolean)) {
        const start = timeToMinutes(mt.start_time);
        const end = timeToMinutes(mt.end_time);
        if (start == null || end == null) continue;
        events.push({ code: c.code, sec: sec.section_number, day: d, start, end });
      }
    }
  }
  for (let i = 0; i < events.length; i++) {
    for (let j = i + 1; j < events.length; j++) {
      const a = events[i], b = events[j];
      if (a.code === b.code) continue;
      if (a.day === b.day && a.start < b.end && b.start < a.end) {
        const msg = `${a.code} Sec ${a.sec} overlaps ${b.code} Sec ${b.sec} on ${DAY_NAMES[a.day] || a.day}`;
        if (!issues.includes(msg)) issues.push(msg);
      }
    }
  }
  return issues;
}

function timeToMinutes(t) {
  if (!t) return null;
  const m = String(t).match(/(\d{1,2}):(\d{2})/);
  if (!m) return null;
  return parseInt(m[1]) * 60 + parseInt(m[2]);
}

function formatTimeStr(timeStr) {
  if (!timeStr) return '';
  const m = String(timeStr).match(/(\d{1,2}):(\d{2})/);
  if (!m) return timeStr;
  let hour = parseInt(m[1]);
  const minute = m[2];
  const ampm = hour >= 12 ? 'pm' : 'am';
  if (hour > 12) hour -= 12;
  if (hour === 0) hour = 12;
  return `${hour}:${minute}${ampm}`;
}

export default YearPlanner;
