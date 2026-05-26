import React, { useEffect, useMemo, useState } from 'react';
import '../styles/CourseCatalog.css';
import { scheduleAPI } from '../services/api';

const DAY_NAMES = { M: 'Mon', T: 'Tue', W: 'Wed', Th: 'Thu', F: 'Fri' };

function CourseCatalog() {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState('');
  const [expanded, setExpanded] = useState(() => new Set());

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await scheduleAPI.getCourses();
        if (cancelled) return;
        setCourses(res.courses || []);
      } catch (err) {
        if (cancelled) return;
        setError(err.message || 'Failed to load catalog');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const filtered = useMemo(() => {
    if (!query.trim()) return courses;
    const q = query.toLowerCase();
    return courses.filter(c =>
      c.code.toLowerCase().includes(q) ||
      (c.title || '').toLowerCase().includes(q) ||
      (c.prerequisites || []).some(p => p.toLowerCase().includes(q))
    );
  }, [courses, query]);

  const toggle = (code) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  };

  return (
    <section className="catalog">
      <header className="catalog-header">
        <div>
          <h2 className="catalog-title">Course catalog</h2>
          <p className="catalog-sub">
            Every CSS course SmartScheduler can recommend, with sections and meeting times.
          </p>
        </div>
        <div className="catalog-meta">
          {!loading && (
            <span className="catalog-count">
              {filtered.length} of {courses.length}
            </span>
          )}
        </div>
      </header>

      <div className="catalog-search">
        <SearchIcon />
        <input
          type="text"
          placeholder="Search by code, title, or prerequisite…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {query && (
          <button className="catalog-clear" onClick={() => setQuery('')} aria-label="Clear">
            ×
          </button>
        )}
      </div>

      {loading && (
        <div className="catalog-loading">
          <div className="spinner" />
          <p>Loading courses…</p>
        </div>
      )}

      {error && (
        <div className="error-message">{error}</div>
      )}

      {!loading && !error && filtered.length === 0 && (
        <div className="no-courses-message">
          <p>No courses match “{query}”.</p>
        </div>
      )}

      {!loading && !error && filtered.length > 0 && (
        <ul className="catalog-list">
          {filtered.map((course) => (
            <CatalogRow
              key={course.code}
              course={course}
              open={expanded.has(course.code)}
              onToggle={() => toggle(course.code)}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

function CatalogRow({ course, open, onToggle }) {
  const credits = course.credit_hours || course.credits || 0;
  const sectionCount = course.sections ? course.sections.length : 0;
  return (
    <li className={`catalog-row ${open ? 'open' : ''}`}>
      <button
        type="button"
        className="catalog-row-summary"
        onClick={onToggle}
        aria-expanded={open}
      >
        <div className="catalog-row-left">
          <span className="catalog-code">{course.code}</span>
          <span className="catalog-row-title">{course.title}</span>
        </div>
        <div className="catalog-row-right">
          <span className="catalog-pill">{credits} cr</span>
          <span className="catalog-pill subtle">
            {sectionCount} {sectionCount === 1 ? 'section' : 'sections'}
          </span>
          <Chevron open={open} />
        </div>
      </button>

      {open && (
        <div className="catalog-row-detail">
          {course.prerequisites && course.prerequisites.length > 0 ? (
            <div className="catalog-prereqs">
              <span className="catalog-eyebrow">Prerequisites</span>
              <div className="catalog-prereq-tags">
                {course.prerequisites.map((p) => (
                  <span key={p} className="catalog-prereq-tag">{p}</span>
                ))}
              </div>
            </div>
          ) : (
            <div className="catalog-prereqs muted">
              <span className="catalog-eyebrow">Prerequisites</span>
              <span>None</span>
            </div>
          )}

          <div className="catalog-sections">
            <span className="catalog-eyebrow">Sections</span>
            <ul className="catalog-section-list">
              {(course.sections || []).map((s, idx) => (
                <CatalogSection key={s.section_id || idx} section={s} />
              ))}
            </ul>
          </div>
        </div>
      )}
    </li>
  );
}

function CatalogSection({ section }) {
  return (
    <li className="catalog-section">
      <div className="catalog-section-top">
        <span className="catalog-section-num">Sec {section.section_number}</span>
        <span className="catalog-section-instructor">
          {section.instructor || 'TBA'}
        </span>
      </div>
      {(section.meeting_times || []).map((mt, idx) => (
        <div key={idx} className="catalog-section-meeting">
          <span className="catalog-section-days">
            {(Array.isArray(mt.days) ? mt.days : [mt.days])
              .filter(Boolean)
              .map((d) => DAY_NAMES[d] || d)
              .join(' · ') || 'Async / TBA'}
          </span>
          {mt.start_time && (
            <span className="catalog-section-time">
              {formatTimeStr(mt.start_time)} – {formatTimeStr(mt.end_time)}
            </span>
          )}
          <span className="catalog-section-loc">
            {mt.location || section.location || 'TBA'}
          </span>
        </div>
      ))}
      {(!section.meeting_times || section.meeting_times.length === 0) && (
        <div className="catalog-section-meeting">
          <span className="catalog-section-days">Async / TBA</span>
        </div>
      )}
    </li>
  );
}

function formatTimeStr(timeStr) {
  if (!timeStr) return '';
  const match = String(timeStr).match(/(\d{1,2}):(\d{2})/);
  if (!match) return timeStr;
  let hour = parseInt(match[1]);
  const minute = match[2];
  const ampm = hour >= 12 ? 'pm' : 'am';
  if (hour > 12) hour -= 12;
  if (hour === 0) hour = 12;
  return `${hour}:${minute}${ampm}`;
}

function SearchIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="11" cy="11" r="8"></circle>
      <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
    </svg>
  );
}

function Chevron({ open }) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
         style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s ease' }}>
      <polyline points="6 9 12 15 18 9"></polyline>
    </svg>
  );
}

export default CourseCatalog;
