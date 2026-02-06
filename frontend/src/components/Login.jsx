import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import '../App.css';

const Login = () => {
  const { userType } = useParams();
  const navigate = useNavigate();
  const { login } = useAuth();
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });
  const [error, setError] = useState('');
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
    setLoading(true);

    try {
      const result = await login(formData.username, formData.password, userType);

      if (result.success) {
        if (result.user.role !== userType) {
          setError(
            `Please login as a ${result.user.role === 'student' ? 'Student' : 'Recruiter'}`
          );
          setLoading(false);
          return;
        }

        if (result.user.role === 'student') {
          navigate('/dashboard/student');
        } else {
          navigate('/dashboard/recruiter');
        }
      } else {
        setError(result.error || 'Login failed. Please check your credentials.');
        setLoading(false);
      }
    } catch (error) {
      console.error('Login error:', error);
      setError(error.message || 'An unexpected error occurred.');
      setLoading(false);
    }
  };

  const isStudent = userType === 'student';

  return (
    <div className="auth-container modern">
      {/* Decorative Elements */}
      <div className="auth-decoration">
        <div className="floating-shape shape-1"></div>
        <div className="floating-shape shape-2"></div>
        <div className="floating-shape shape-3"></div>
      </div>

      <div className="auth-box glass">
        {/* Header */}
        <div className="auth-header">
          <div className="auth-icon">
            {isStudent ? '🎓' : '💼'}
          </div>
          <h1 className="auth-title gradient-text">
            {isStudent ? 'Student Login' : 'Recruiter Login'}
          </h1>
          <p className="auth-subtitle">
            Welcome back! Enter your credentials to continue.
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="error-message shake">
            <span className="error-icon">⚠️</span>
            {error}
          </div>
        )}

        {/* Login Form */}
        <form className="auth-form" onSubmit={handleSubmit}>
          {/* Step 1: Username */}
          <div className="form-step">
            <div className="step-indicator">
              <span className="step-number">1</span>
              <span className="step-label">Username</span>
            </div>
            <div className="form-group modern">
              <input
                type="text"
                name="username"
                className="form-input modern"
                value={formData.username}
                onChange={handleChange}
                required
                placeholder=" "
                autoComplete="username"
              />
              <label className="form-label floating">Username or Email</label>
              <div className="input-icon">👤</div>
            </div>
          </div>

          {/* Step 2: Password */}
          <div className="form-step">
            <div className="step-indicator">
              <span className="step-number">2</span>
              <span className="step-label">Password</span>
            </div>
            <div className="form-group modern">
              <input
                type="password"
                name="password"
                className="form-input modern"
                value={formData.password}
                onChange={handleChange}
                required
                placeholder=" "
                autoComplete="current-password"
              />
              <label className="form-label floating">Password</label>
              <div className="input-icon">🔒</div>
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            className="form-button gradient"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                <span>Signing in...</span>
              </>
            ) : (
              <>
                <span>Sign In</span>
                <span className="btn-arrow">→</span>
              </>
            )}
          </button>
        </form>

        {/* Footer Links */}
        <div className="auth-footer">
          <div
            className="form-link primary-link"
            onClick={() => navigate(`/signup/${userType}`)}
          >
            Don't have an account? <strong>Sign Up</strong>
          </div>

          <div
            className="form-link forgot-link"
            onClick={() => navigate('/forgot-password')}
          >
            Forgot Password?
          </div>

          <div className="auth-divider">
            <span>or</span>
          </div>

          <div
            className="form-link switch-link"
            onClick={() => navigate(`/login/${isStudent ? 'recruiter' : 'student'}`)}
          >
            Login as {isStudent ? 'Recruiter' : 'Student'} instead
          </div>

          <div
            className="form-link back-link"
            onClick={() => navigate('/')}
          >
            ← Back to Home
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
