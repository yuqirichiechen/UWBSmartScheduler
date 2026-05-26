import React, { useState, useEffect } from 'react';
import './styles/App.css';
import QueryInput from './components/QueryInput';
import ScheduleOutput from './components/ScheduleOutput';
import CompletedCourses from './components/CompletedCourses';
import CourseCatalog from './components/CourseCatalog';
import YearPlanner from './components/YearPlanner';
import { scheduleAPI } from './services/api';

function App() {
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [completedCourses, setCompletedCourses] = useState([]);
  const [apiStatus, setApiStatus] = useState('checking');
  const [view, setView] = useState('schedule'); // 'schedule' | 'catalog' | 'calendar'

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

  const handleQuery = async (query) => {
    setLoading(true);
    setError(null);
    setView('schedule');
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
              {!schedule && !loading && (
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

              <QueryInput onSubmit={handleQuery} loading={loading} />
              <CompletedCourses onUpdate={handleCompletedCoursesUpdate} />

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
                <ScheduleOutput schedule={schedule} />
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
