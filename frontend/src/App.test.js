import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';
import { scheduleAPI } from './services/api';

jest.mock('./services/api');

beforeEach(() => {
  scheduleAPI.healthCheck = jest.fn().mockResolvedValue({ status: 'healthy' });
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
});
