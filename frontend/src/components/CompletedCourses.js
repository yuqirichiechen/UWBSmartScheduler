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
    <div className="completed-courses-container">
      <h3>Completed Courses (for prerequisite checking)</h3>
      
      <div className="course-input-group">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value.toUpperCase())}
          onKeyPress={handleKeyPress}
          placeholder="e.g., CSS 143"
          className="course-input"
        />
        <button onClick={handleAddCourse} className="add-course-btn">
          + Add
        </button>
      </div>

      {courses.length > 0 && (
        <div className="courses-list">
          {courses.map((course) => (
            <div key={course} className="course-tag">
              <span>{course}</span>
              <button
                onClick={() => handleRemoveCourse(course)}
                className="remove-btn"
                title="Remove course"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {courses.length === 0 && (
        <p className="no-courses-text">No completed courses added yet</p>
      )}
    </div>
  );
}

export default CompletedCourses;
