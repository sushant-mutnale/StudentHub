import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api/client';
import '../App.css';

// Debounce utility
const useDebounce = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  return debouncedValue;
};

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

  // Real-time validation states
  const [usernameStatus, setUsernameStatus] = useState(null); // null, 'checking', 'available', 'taken', 'invalid'
  const [emailStatus, setEmailStatus] = useState(null);
  const [passwordStrength, setPasswordStrength] = useState(0);

  // Debounced values for validation
  const debouncedUsername = useDebounce(formData.username, 500);
  const debouncedEmail = useDebounce(formData.email, 500);

  // Check username availability
  useEffect(() => {
    const checkUsername = async () => {
      if (debouncedUsername.length < 3) {
        setUsernameStatus(debouncedUsername.length > 0 ? 'invalid' : null);
        return;
      }
      setUsernameStatus('checking');
      try {
        const { data } = await api.get(`/auth/check-username/${debouncedUsername}`);
        setUsernameStatus(data.available ? 'available' : 'taken');
      } catch {
        setUsernameStatus(null);
      }
    };
    checkUsername();
  }, [debouncedUsername]);

  // Check email availability
  useEffect(() => {
    const checkEmail = async () => {
      if (!debouncedEmail || !debouncedEmail.includes('@')) {
        setEmailStatus(null);
        return;
      }
      setEmailStatus('checking');
      try {
        const { data } = await api.get(`/auth/check-email/${debouncedEmail}`);
        setEmailStatus(data.available ? 'available' : 'taken');
      } catch {
        setEmailStatus(null);
      }
    };
    checkEmail();
  }, [debouncedEmail]);

  // Password strength calculator
  useEffect(() => {
    const password = formData.password;
    let strength = 0;
    if (password.length >= 6) strength += 20;
    if (password.length >= 8) strength += 20;
    if (/[A-Z]/.test(password)) strength += 20;
    if (/[0-9]/.test(password)) strength += 20;
    if (/[^A-Za-z0-9]/.test(password)) strength += 20;
    setPasswordStrength(strength);
  }, [formData.password]);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validate before submit
    if (usernameStatus === 'taken') {
      setError('Username is already taken');
      return;
    }
    if (emailStatus === 'taken') {
      setError('Email is already registered');
      return;
    }
    if (passwordStrength < 60) {
      setError('Please use a stronger password');
      return;
    }

    setError('');
    setSuccess('');
    setLoading(true);

    // Convert skills string to array of SkillSchema objects
    const skillsArray = formData.skills
      .split(',')
      .map((skill) => skill.trim())
      .filter((skill) => skill.length > 0)
      .map((skill) => ({
        name: skill,
        level: 0,
        proficiency: "Beginner",
        confidence: 0,
        evidence: []
      }));

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
      setSuccess('🎉 Account created successfully! Redirecting to login...');
      setTimeout(() => {
        navigate('/login/student');
      }, 2000);
    } else {
      setError(result.error);
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'checking':
        return <span className="status-icon spinning">⟳</span>;
      case 'available':
        return <span className="status-icon success">✓</span>;
      case 'taken':
        return <span className="status-icon error">✗</span>;
      case 'invalid':
        return <span className="status-icon warning">!</span>;
      default:
        return null;
    }
  };

  const getStrengthColor = () => {
    if (passwordStrength <= 20) return '#ff4444';
    if (passwordStrength <= 40) return '#ff8c00';
    if (passwordStrength <= 60) return '#ffd700';
    if (passwordStrength <= 80) return '#9acd32';
    return '#00c851';
  };

  const getStrengthLabel = () => {
    if (passwordStrength <= 20) return 'Very Weak';
    if (passwordStrength <= 40) return 'Weak';
    if (passwordStrength <= 60) return 'Fair';
    if (passwordStrength <= 80) return 'Strong';
    return 'Very Strong';
  };

  return (
    <div className="auth-container">
      <div className="auth-box signup-box">
        <div className="auth-header">
          <h1 className="auth-title">🎓 Student Sign Up</h1>
          <p className="auth-subtitle">Create your account to start your career journey</p>
        </div>

        {error && <div className="error-message animate-shake">{error}</div>}
        {success && <div className="success-message animate-pulse">{success}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-row">
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
              <div className="input-with-status">
                <input
                  type="text"
                  name="username"
                  className={`form-input ${usernameStatus === 'taken' ? 'input-error' : usernameStatus === 'available' ? 'input-success' : ''}`}
                  value={formData.username}
                  onChange={handleChange}
                  required
                  placeholder="Choose a username"
                />
                {getStatusIcon(usernameStatus)}
              </div>
              {usernameStatus === 'taken' && <span className="field-error">Username already taken</span>}
              {usernameStatus === 'invalid' && <span className="field-warning">Min 3 characters</span>}
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Email *</label>
              <div className="input-with-status">
                <input
                  type="email"
                  name="email"
                  className={`form-input ${emailStatus === 'taken' ? 'input-error' : emailStatus === 'available' ? 'input-success' : ''}`}
                  value={formData.email}
                  onChange={handleChange}
                  required
                  placeholder="Enter your email"
                />
                {getStatusIcon(emailStatus)}
              </div>
              {emailStatus === 'taken' && <span className="field-error">Email already registered</span>}
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
                placeholder="Create a strong password"
                minLength="6"
              />
              {formData.password && (
                <div className="password-strength">
                  <div className="strength-bar">
                    <div
                      className="strength-fill"
                      style={{ width: `${passwordStrength}%`, backgroundColor: getStrengthColor() }}
                    />
                  </div>
                  <span className="strength-label" style={{ color: getStrengthColor() }}>
                    {getStrengthLabel()}
                  </span>
                </div>
              )}
            </div>
          </div>

          <div className="form-row">
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
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Year *</label>
              <select
                name="year"
                className="form-input form-select"
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
              placeholder="Comma-separated: React, Node.js, Python, Machine Learning"
            />
            <span className="field-hint">Separate skills with commas</span>
          </div>

          <div className="form-group">
            <label className="form-label">Bio <span className="optional">(Optional)</span></label>
            <textarea
              name="bio"
              className="form-textarea"
              value={formData.bio}
              onChange={handleChange}
              placeholder="Tell us about yourself, your goals, and aspirations..."
              rows="3"
            />
          </div>

          <button
            type="submit"
            className={`form-button ${loading ? 'loading' : ''}`}
            disabled={loading || usernameStatus === 'taken' || emailStatus === 'taken'}
          >
            {loading ? (
              <>
                <span className="button-spinner"></span>
                Creating Account...
              </>
            ) : (
              '🚀 Create Account'
            )}
          </button>
        </form>

        <div className="auth-footer">
          <div className="form-link" onClick={() => navigate('/login/student')}>
            Already have an account? <strong>Login</strong>
          </div>
          <div className="form-link secondary" onClick={() => navigate('/')}>
            ← Back to Home
          </div>
        </div>
      </div>
    </div>
  );
};

export default SignupStudent;
