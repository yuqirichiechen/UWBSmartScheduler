import axios from 'axios';

/*
 * API base URL resolution
 * -----------------------
 * - In production (Vercel) the frontend and backend live on the same origin,
 *   so we use a relative base ('') and hit `/api/*` directly.
 * - In local dev (`react-scripts start` on :3000), point at the FastAPI dev
 *   server on :8000. Override with REACT_APP_API_URL in .env.local if needed.
 */
const isProd = process.env.NODE_ENV === 'production';
const API_URL =
  process.env.REACT_APP_API_URL ?? (isProd ? '' : 'http://localhost:8000');
const API_TIMEOUT = process.env.REACT_APP_API_TIMEOUT || 30000;

const apiClient = axios.create({
  baseURL: API_URL,
  timeout: parseInt(API_TIMEOUT),
  headers: {
    'Content-Type': 'application/json',
  },
});

export const scheduleAPI = {
  async getSchedule(query, completedCourses = []) {
    try {
      const response = await apiClient.post('/api/schedule', {
        query,
        completed_courses: completedCourses,
      });
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to get schedule');
    }
  },

  async getCourses() {
    try {
      const response = await apiClient.get('/api/courses');
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to get courses');
    }
  },

  async triggerScrape() {
    try {
      const response = await apiClient.post('/api/scrape');
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to trigger scrape');
    }
  },

  async healthCheck() {
    try {
      const response = await apiClient.get('/api/health');
      return response.data;
    } catch (error) {
      throw new Error('Health check failed');
    }
  },
};

export default apiClient;
