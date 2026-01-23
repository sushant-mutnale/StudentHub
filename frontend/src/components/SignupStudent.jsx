import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import '../App.css';

const SignupStudent = () => {
  const navigate = useNavigate();
  const { signupStudent } = useAuth();
  const [formData, setFormData] = useState({
    fullName: '',
    username: '',
    email: '',
    password: '',
    prn: '',
    college: '',
    year: '',
    branch: '',
    skills: '',
    bio: '',
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    // Convert skills string to array
    const skillsArray = formData.skills
      .split(',')
      .map((skill) => skill.trim())
      .filter((skill) => skill.length > 0);

    const payload = {
      full_name: formData.fullName,
      username: formData.username,
      email: formData.email,
      password: formData.password,
      prn: formData.prn,
      college: formData.college,
      branch: formData.branch,
      year: formData.year,
      bio: formData.bio,
      skills: skillsArray,
    };

    const result = await signupStudent(payload);

    if (result.success) {
      setSuccess('Signup successful! Please login to continue.');
      setTimeout(() => {
        navigate('/login/student');
      }, 2000);
    } else {
      setError(result.error);
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-box">
        <h1 className="auth-title">Student Sign Up</h1>
        <p className="auth-subtitle">Create your account to get started.</p>

        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Full Name *</label>
            <input
              type="text"
              name="fullName"
              className="form-input"
              value={formData.fullName}
              onChange={handleChange}
              required
              placeholder="Enter your full name"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Username *</label>
            <input
              type="text"
              name="username"
              className="form-input"
              value={formData.username}
              onChange={handleChange}
              required
              placeholder="Choose a username"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Email *</label>
            <input
              type="email"
              name="email"
              className="form-input"
              value={formData.email}
              onChange={handleChange}
              required
              placeholder="Enter your email"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password *</label>
            <input
              type="password"
              name="password"
              className="form-input"
              value={formData.password}
              onChange={handleChange}
              required
              placeholder="Create a password"
              minLength="6"
            />
          </div>

          <div className="form-group">
            <label className="form-label">PRN Number *</label>
            <input
              type="text"
              name="prn"
              className="form-input"
              value={formData.prn}
              onChange={handleChange}
              required
              placeholder="Enter your PRN"
            />
          </div>

          <div className="form-group">
            <label className="form-label">College *</label>
            <input
              type="text"
              name="college"
              className="form-input"
              value={formData.college}
              onChange={handleChange}
              required
              placeholder="Enter your college name"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Year *</label>
            <select
              name="year"
              className="form-input"
              value={formData.year}
              onChange={handleChange}
              required
            >
              <option value="">Select Year</option>
              <option value="1st Year">1st Year</option>
              <option value="2nd Year">2nd Year</option>
              <option value="3rd Year">3rd Year</option>
              <option value="4th Year">4th Year</option>
              <option value="Graduate">Graduate</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Branch *</label>
            <input
              type="text"
              name="branch"
              className="form-input"
              value={formData.branch}
              onChange={handleChange}
              required
              placeholder="e.g., Computer Science"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Skills *</label>
            <input
              type="text"
              name="skills"
              className="form-input"
              value={formData.skills}
              onChange={handleChange}
              required
              placeholder="Comma-separated: React, Node.js, Python"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Bio</label>
            <textarea
              name="bio"
              className="form-textarea"
              value={formData.bio}
              onChange={handleChange}
              placeholder="Tell us about yourself"
              rows="3"
            />
          </div>

          <button type="submit" className="form-button" disabled={loading}>
            {loading ? 'Creating Account...' : 'Sign Up'}
          </button>
        </form>

        <div className="form-link" onClick={() => navigate('/login/student')}>
          Already have an account? Login
        </div>

        <div
          className="form-link"
          onClick={() => navigate('/')}
          style={{ marginTop: '0.5rem' }}
        >
          ← Back to Home
        </div>
      </div>
    </div>
  );
};

export default SignupStudent;

