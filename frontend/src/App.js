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

  // Check API health on mount
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
            <h1>🎓 SmartScheduler</h1>
            <p>Plan your perfect schedule with AI assistance</p>
          </div>
          {apiStatus === 'checking' && (
            <div className="status checking">Connecting to backend...</div>
          )}
          {apiStatus === 'ready' && (
            <div className="status ready">✓ Backend connected</div>
          )}
          {apiStatus === 'error' && (
            <div className="status error">
              ✗ Backend unavailable - Make sure the Python server is running on port 8000
            </div>
          )}
        </div>
      </header>

      <main className="App-main">
        <div className="container">
          {apiStatus === 'error' && (
            <div className="api-error-banner">
              <h3>Backend Connection Issue</h3>
              <p>To run the application locally:</p>
              <ol>
                <li>
                  <code>cd backend</code>
                </li>
                <li>
                  <code>source venv/bin/activate</code>
                </li>
                <li>
                  <code>python main.py</code>
                </li>
              </ol>
              <p>The server should start at http://localhost:8000</p>
            </div>
          )}

          {apiStatus !== 'error' && (
            <>
              <QueryInput onSubmit={handleQuery} loading={loading} />

              <CompletedCourses onUpdate={handleCompletedCoursesUpdate} />

              {error && (
                <div className="error-message">
                  <strong>⚠️ Error:</strong> {error}
                </div>
              )}

              {loading && (
                <div className="loading-spinner">
                  <div className="spinner"></div>
                  <p>Generating your personalized schedule...</p>
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
        <p>CSS 382 Capstone | UW Bothell AI-Powered Course Scheduler</p>
        <p className="footer-links">
          <a href="https://github.com/uwbothell-css382/course-scheduler" target="_blank" rel="noopener noreferrer">
            GitHub
          </a>
          {' | '}
          <a href="/BACKEND.md" target="_blank" rel="noopener noreferrer">
            API Docs
          </a>
        </p>
      </footer>
    </div>
  );
}

export default App;
