import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import '../App.css';

const SignupRecruiter = () => {
  const navigate = useNavigate();
  const { signupRecruiter } = useAuth();
  const [formData, setFormData] = useState({
    companyName: '',
    username: '',
    email: '',
    password: '',
    contactNumber: '',
    website: '',
    description: '',
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

    const payload = {
      company_name: formData.companyName,
      username: formData.username,
      email: formData.email,
      password: formData.password,
      contact_number: formData.contactNumber,
      website: formData.website,
      company_description: formData.description,
    };

    const result = await signupRecruiter(payload);

    if (result.success) {
      setSuccess('Signup successful! Please login to continue.');
      setTimeout(() => {
        navigate('/login/recruiter');
      }, 2000);
    } else {
      setError(result.error);
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-box">
        <h1 className="auth-title">Recruiter Sign Up</h1>
        <p className="auth-subtitle">Create your recruiter account.</p>

        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Company Name *</label>
            <input
              type="text"
              name="companyName"
              className="form-input"
              value={formData.companyName}
              onChange={handleChange}
              required
              placeholder="Enter company name"
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
            <label className="form-label">Contact Number *</label>
            <input
              type="tel"
              name="contactNumber"
              className="form-input"
              value={formData.contactNumber}
              onChange={handleChange}
              required
              placeholder="Enter contact number"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Website</label>
            <input
              type="url"
              name="website"
              className="form-input"
              value={formData.website}
              onChange={handleChange}
              placeholder="https://example.com"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description *</label>
            <textarea
              name="description"
              className="form-textarea"
              value={formData.description}
              onChange={handleChange}
              required
              placeholder="Describe your company"
              rows="4"
            />
          </div>

          <button type="submit" className="form-button" disabled={loading}>
            {loading ? 'Creating Account...' : 'Sign Up'}
          </button>
        </form>

        <div className="form-link" onClick={() => navigate('/login/recruiter')}>
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

export default SignupRecruiter;

