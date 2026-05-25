import React, { useState, useEffect } from 'react';
import './styles/App.css';
import QueryInput from './components/QueryInput';
import ScheduleOutput from './components/ScheduleOutput';
import CompletedCourses from './components/CompletedCourses';
import { scheduleAPI } from './services/api';

function App() {
  const [schedule, setSchedule] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [completedCourses, setCompletedCourses] = useState([]);
  const [apiStatus, setApiStatus] = useState('checking');

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
          {apiStatus === 'checking' && (
            <div className="status checking">Connecting...</div>
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

          {apiStatus !== 'error' && (
            <>
              <QueryInput onSubmit={handleQuery} loading={loading} />
              <CompletedCourses onUpdate={handleCompletedCoursesUpdate} />

              {error && (
                <div className="error-message">{error}</div>
              )}

              {loading && (
                <div className="loading-spinner">
                  <div className="spinner"></div>
                  <p>Building your schedule...</p>
                </div>
              )}

              {schedule && !loading && (
                <ScheduleOutput schedule={schedule} />
              )}
            </>
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
