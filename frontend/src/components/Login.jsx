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
        // Check if user type matches
        if (result.user.role !== userType) {
          setError(
            `Please login as a ${result.user.role === 'student' ? 'Student' : 'Recruiter'}`
          );
          setLoading(false);
          return;
        }

        // Redirect to appropriate dashboard
        if (result.user.role === 'student') {
          navigate('/dashboard/student');
        } else {
          navigate('/dashboard/recruiter');
        }
      } else {
        setError(result.error || 'Login failed. Please check your credentials and try again.');
        setLoading(false);
      }
    } catch (error) {
      console.error('Login submission error:', error);
      setError(
        error.message || 'An unexpected error occurred. Please try again.'
      );
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-box">
        <h1 className="auth-title">
          {userType === 'student' ? 'Student' : 'Recruiter'} Login
        </h1>
        <p className="auth-subtitle">Welcome back! Please login to continue.</p>

        {error && <div className="error-message">{error}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Username or Email</label>
            <input
              type="text"
              name="username"
              className="form-input"
              value={formData.username}
              onChange={handleChange}
              required
              placeholder="Enter your username or email"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              name="password"
              className="form-input"
              value={formData.password}
              onChange={handleChange}
              required
              placeholder="Enter your password"
            />
          </div>

          <button
            type="submit"
            className="form-button"
            disabled={loading}
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        <div
          className="form-link"
          onClick={() => navigate(`/signup/${userType}`)}
        >
          Don't have an account? Sign Up
        </div>

        <div
          className="form-link forgot-link"
          onClick={() => navigate('/forgot-password')}
          style={{ marginTop: '0.5rem' }}
        >
          Forgot Password?
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

export default Login;


