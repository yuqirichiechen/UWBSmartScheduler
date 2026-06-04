import React, { useState, useEffect } from 'react';
import './styles/App.css';
import QueryInput from './components/QueryInput';
import ScheduleOutput from './components/ScheduleOutput';
import CompletedCourses from './components/CompletedCourses';
import ClarifyingQuestions from './components/ClarifyingQuestions';
import CourseCatalog from './components/CourseCatalog';
import YearPlanner from './components/YearPlanner';
import { scheduleAPI } from './services/api';

// A request is "open-ended" when the student is asking for advice rather than
// stating concrete constraints. In that case we ask what they've completed
// first (unless they already told us).
function isAdviceSeeking(query) {
  const q = (query || '').toLowerCase().trim();
  if (q.length < 12) return true; // very vague ("test", "help", "idk")
  return /\b(what|which)\b.*\b(take|class|course|should)\b|recommend|suggest|help me|not sure|don'?t know|no idea|advice|where do i (start|begin)/.test(q);
}

function App() {
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [completedCourses, setCompletedCourses] = useState([]);
  const [apiStatus, setApiStatus] = useState('checking');
  const [view, setView] = useState('schedule'); // 'schedule' | 'catalog' | 'calendar'
  const [pendingQuery, setPendingQuery] = useState(null); // awaiting clarification
  const [clarify, setClarify] = useState(null); // { question, options } | null
  const [clarifyLoading, setClarifyLoading] = useState(false);
  const [lastQuery, setLastQuery] = useState('');

  useEffect(() => {
    const checkAPI = async () => {
      try {
        await scheduleAPI.healthCheck();
        setApiStatus('ready');
      } catch (err) {
        setApiStatus('error');
        console.warn('API health check failed:', err);
      }
    };
    checkAPI();
  }, []);

  const runQuery = async (query) => {
    setLoading(true);
    setError(null);
    setView('schedule');
    setLastQuery(query);
    try {
      const response = await scheduleAPI.getSchedule(query, completedCourses);
      setSchedule(response);
    } catch (err) {
      setError(err.message || 'Failed to generate schedule');
      console.error('Error:', err);
      setSchedule(null);
    } finally {
      setLoading(false);
    }
  };

  // Intercept open-ended requests to ask an AI-generated clarifying question.
  const handleQuery = async (query) => {
    if (isAdviceSeeking(query)) {
      setPendingQuery(query);
      setSchedule(null);
      setClarify(null);
      setClarifyLoading(true);
      try {
        const q = await scheduleAPI.clarify(query, completedCourses);
        setClarify(q);
      } finally {
        setClarifyLoading(false);
      }
      return;
    }
    runQuery(query);
  };

  // User picked an option (or typed "Other"): fold it into the query + generate.
  const answerClarify = (answer) => {
    const base = pendingQuery || '';
    const augmented = `${base} — ${answer}`.trim();
    setPendingQuery(null);
    setClarify(null);
    runQuery(augmented);
  };

  const skipClarify = () => {
    const q = pendingQuery;
    setPendingQuery(null);
    setClarify(null);
    runQuery(q);
  };

  const handleCompletedCoursesUpdate = (courses) => {
    setCompletedCourses(courses);
  };

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <div className="header-main">
            <h1>Smart<span className="brand-dot">Scheduler</span></h1>
          </div>

          {apiStatus !== 'error' && (
            <nav className="header-nav" aria-label="Primary">
              <button
                type="button"
                className={`nav-link ${view === 'schedule' ? 'active' : ''}`}
                onClick={() => setView('schedule')}
              >
                Schedule
              </button>
              <button
                type="button"
                className={`nav-link ${view === 'catalog' ? 'active' : ''}`}
                onClick={() => setView('catalog')}
              >
                Catalog
              </button>
              <button
                type="button"
                className={`nav-link ${view === 'calendar' ? 'active' : ''}`}
                onClick={() => setView('calendar')}
              >
                Calendar
              </button>
            </nav>
          )}

          {apiStatus === 'checking' && (
            <div className="status checking">Connecting</div>
          )}
          {apiStatus === 'ready' && (
            <div className="status ready">Connected</div>
          )}
          {apiStatus === 'error' && (
            <div className="status error">Offline</div>
          )}
        </div>
      </header>

      <main className="App-main">
        <div className="container">
          {apiStatus === 'error' && (
            <div className="api-error-banner">
              <h3>Backend Unavailable</h3>
              <p>Start the server to use SmartScheduler:</p>
              <ol>
                <li><code>cd backend</code></li>
                <li><code>source venv/bin/activate</code></li>
                <li><code>python main.py</code></li>
              </ol>
            </div>
          )}

          {apiStatus !== 'error' && view === 'schedule' && (
            <>
              {!schedule && !loading && !pendingQuery && (
                <section className="hero">
                  <div className="hero-eyebrow">UW Bothell · CSS</div>
                  <h2>
                    Plan your quarter in <em>plain English</em>.
                  </h2>
                  <p>
                    Describe the schedule you want — days you can come to campus,
                    credit limits, courses you need — and SmartScheduler picks
                    the sections that actually fit.
                  </p>
                </section>
              )}

              {/* Completed-courses context card — now ABOVE the chatbox */}
              {!schedule && (
                <CompletedCourses
                  courses={completedCourses}
                  onUpdate={handleCompletedCoursesUpdate}
                  collapsible
                />
              )}

              <QueryInput onSubmit={handleQuery} loading={loading} />

              {/* AI clarifying question for open-ended asks */}
              {pendingQuery && !loading && (
                <>
                  <div className="user-bubble">{pendingQuery}</div>
                  <ClarifyingQuestions
                    query={pendingQuery}
                    question={clarify?.question}
                    options={clarify?.options || []}
                    loadingQuestion={clarifyLoading}
                    onAnswer={answerClarify}
                    onSkip={skipClarify}
                  />
                </>
              )}

              {error && (
                <div className="error-message">{error}</div>
              )}

              {loading && (
                <div className="loading-spinner">
                  <div className="spinner"></div>
                  <p>Building your schedule…</p>
                </div>
              )}

              {schedule && !loading && (
                <>
                  {lastQuery && <div className="user-bubble">{lastQuery}</div>}
                  <ScheduleOutput schedule={schedule} />
                  <div className="followup">
                    <button
                      type="button"
                      className="followup-btn"
                      onClick={() => { setSchedule(null); setLastQuery(''); }}
                    >
                      ← Start over / new request
                    </button>
                    <button
                      type="button"
                      className="followup-btn ghost"
                      onClick={() => setView('calendar')}
                    >
                      Save to a quarter in Calendar →
                    </button>
                  </div>
                </>
              )}
            </>
          )}

          {apiStatus !== 'error' && view === 'catalog' && (
            <CourseCatalog />
          )}

          {apiStatus !== 'error' && view === 'calendar' && (
            <YearPlanner />
          )}
        </div>
      </main>

      <footer className="App-footer">
        <p>CSS 382 &middot; UW Bothell &middot; AI-Powered Course Scheduling</p>
      </footer>
    </div>
  );
}

export default App;
