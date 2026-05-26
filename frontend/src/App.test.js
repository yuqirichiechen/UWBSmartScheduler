import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';
import { scheduleAPI } from './services/api';

jest.mock('./services/api');

beforeEach(() => {
  scheduleAPI.healthCheck = jest.fn().mockResolvedValue({ status: 'healthy' });
  scheduleAPI.getCourses = jest.fn().mockResolvedValue({
    count: 1,
    status: 'ready',
    courses: [
      {
        code: 'CSS 143',
        title: 'Computer Programming II',
        credit_hours: 5,
        department: 'CSS',
        prerequisites: ['CSS 142'],
        sections: [
          {
            section_number: 'A',
            instructor: 'Dr. C',
            meeting_times: [
              { days: ['M', 'W'], start_time: '10:00', end_time: '11:30', location: 'UWB 3' },
            ],
          },
        ],
      },
    ],
  });
  scheduleAPI.getSchedule = jest.fn().mockResolvedValue({
    query: 'CSS core, no Friday',
    recommendations: 'Selected 2 courses (9 credits): CSS 112, CSS 225.',
    constraints: { avoid_days: ['F'] },
    is_valid: true,
    issues: [],
    recommended_courses: [
      {
        code: 'CSS 112',
        title: 'Computer Animation',
        credits: 4,
        prerequisites: [],
        sections: [
          {
            section_number: 'A',
            instructor: 'Dr. A',
            meeting_times: [
              { days: ['T', 'Th'], start_time: '15:30', end_time: '17:30', location: 'UWB 1' },
            ],
          },
        ],
      },
      {
        code: 'CSS 225',
        title: 'Software for Web',
        credits: 5,
        prerequisites: ['CSS 143'],
        sections: [
          {
            section_number: 'A',
            instructor: 'Dr. B',
            meeting_times: [
              { days: ['M', 'W'], start_time: '11:00', end_time: '13:00', location: 'UWB 2' },
            ],
          },
        ],
      },
    ],
  });
});

afterEach(() => {
  jest.resetAllMocks();
});

test('renders header and connects to the API', async () => {
  render(<App />);
  // The brand mark in the header
  expect(
    screen.getByRole('heading', { level: 1, name: /Smart/i })
  ).toBeInTheDocument();
  await waitFor(() => {
    expect(screen.getByText(/^Connected$/)).toBeInTheDocument();
  });
});

test('submitting a query renders the resulting schedule', async () => {
  render(<App />);
  await waitFor(() => expect(screen.getByText(/^Connected$/)).toBeInTheDocument());

  const textarea = screen.getByPlaceholderText(/Tuesday and Thursday/i);
  fireEvent.change(textarea, { target: { value: 'CSS core, no Friday' } });
  fireEvent.click(screen.getByRole('button', { name: /Generate Schedule/i }));

  await waitFor(() =>
    expect(scheduleAPI.getSchedule).toHaveBeenCalledWith('CSS core, no Friday', [])
  );

  // Both courses land in the output (calendar + course rows)
  await waitFor(() => {
    expect(screen.getAllByText(/CSS 112/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/CSS 225/).length).toBeGreaterThan(0);
  });

  // Total credit pill in the schedule header
  expect(screen.getByText(/^9 credits$/)).toBeInTheDocument();
  // No-conflicts badge
  expect(screen.getByText(/No Conflicts/i)).toBeInTheDocument();

  // Tabs are present and Calendar is the default
  expect(screen.getByRole('tab', { name: /Calendar/i, selected: true })).toBeInTheDocument();
  expect(screen.getByRole('tab', { name: /Sections/i, selected: false })).toBeInTheDocument();

  // Switching to Sections renders the course rows
  fireEvent.click(screen.getByRole('tab', { name: /Sections/i }));
  await waitFor(() =>
    expect(screen.getByRole('tab', { name: /Sections/i, selected: true })).toBeInTheDocument()
  );
});

test('catalog nav loads and shows available courses', async () => {
  render(<App />);
  await waitFor(() => expect(screen.getByText(/^Connected$/)).toBeInTheDocument());

  fireEvent.click(screen.getByRole('button', { name: /^Catalog$/ }));

  await waitFor(() =>
    expect(scheduleAPI.getCourses).toHaveBeenCalled()
  );

  // The mocked course shows up
  await waitFor(() => {
    expect(screen.getByText('CSS 143')).toBeInTheDocument();
    expect(screen.getByText(/Computer Programming II/)).toBeInTheDocument();
  });
});

test('calendar nav opens year planner with quarter tabs', async () => {
  // Clean storage so the planner starts empty
  localStorage.removeItem('smartsched.yearplan.v1');

  render(<App />);
  await waitFor(() => expect(screen.getByText(/^Connected$/)).toBeInTheDocument());

  fireEvent.click(screen.getByRole('button', { name: /^Calendar$/ }));

  // Title + the four quarter tabs
  await waitFor(() => {
    expect(screen.getByText(/Year planner/i)).toBeInTheDocument();
  });
  expect(screen.getByRole('tab', { name: /Autumn 2026/i, selected: true })).toBeInTheDocument();
  expect(screen.getByRole('tab', { name: /Winter 2027/i })).toBeInTheDocument();
  expect(screen.getByRole('tab', { name: /Spring 2027/i })).toBeInTheDocument();
  expect(screen.getByRole('tab', { name: /Summer 2027/i })).toBeInTheDocument();

  // Empty state CTA
  expect(screen.getByText(/No courses planned/i)).toBeInTheDocument();

  // Open course picker, add the catalog course
  fireEvent.click(screen.getByRole('button', { name: /\+ Add your first course/i }));
  await waitFor(() =>
    expect(screen.getByPlaceholderText(/Search courses/i)).toBeInTheDocument()
  );

  // Wait for catalog to load and click the row
  await waitFor(() => expect(scheduleAPI.getCourses).toHaveBeenCalled());
  await waitFor(() => {
    expect(screen.getByText('CSS 143')).toBeInTheDocument();
  });
  fireEvent.click(screen.getByText('CSS 143'));

  // It should now appear in the planner sections list with its credit count
  await waitFor(() => {
    // "1 course" stat
    expect(screen.getByText(/^course$/i)).toBeInTheDocument();
  });
});
