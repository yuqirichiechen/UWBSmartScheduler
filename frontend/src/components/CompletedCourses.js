import React, { useState } from 'react';
import '../styles/CompletedCourses.css';

function CompletedCourses({ onUpdate }) {
  const [courses, setCourses] = useState([]);
  const [input, setInput] = useState('');

  const handleAddCourse = () => {
    const courseCode = input.toUpperCase().trim();
    if (courseCode && !courses.includes(courseCode)) {
      const updatedCourses = [...courses, courseCode];
      setCourses(updatedCourses);
      onUpdate(updatedCourses);
      setInput('');
    }
  };

  const handleRemoveCourse = (course) => {
    const updatedCourses = courses.filter(c => c !== course);
    setCourses(updatedCourses);
    onUpdate(updatedCourses);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleAddCourse();
    }
  };

  return (
    <div className="completed-courses">
      <div className="completed-label">
        <span className="completed-label-text">Already completed</span>
        <span className="completed-label-hint">used to gate prerequisites</span>
      </div>

      <div className="completed-row">
        {courses.map((course) => (
          <span key={course} className="course-tag">
            {course}
            <button
              onClick={() => handleRemoveCourse(course)}
              className="remove-btn"
              title={`Remove ${course}`}
              aria-label={`Remove ${course}`}
            >
              ×
            </button>
          </span>
        ))}

        <span className="course-input-wrap">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value.toUpperCase())}
            onKeyPress={handleKeyPress}
            placeholder={courses.length ? 'Add another…' : 'e.g. CSS 143'}
            className="course-input"
          />
          {input.trim() && (
            <button onClick={handleAddCourse} className="add-course-btn">
              add
            </button>
          )}
        </span>
      </div>
    </div>
  );
}

export default CompletedCourses;
