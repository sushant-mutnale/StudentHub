import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api/client';
import OTPInput from './OTPInput';
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

  // OTP States
  const [otp, setOtp] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [otpVerified, setOtpVerified] = useState(false);

  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    // Reset Verification if email changes
    if (name === 'email') {
      setOtpVerified(false);
      setOtpSent(false);
      setOtp('');
    }
    setFormData({
      ...formData,
      [name]: value,
    });
    setError('');
  };

  const handleSendOTP = async () => {
    if (!formData.email || !formData.email.includes('@')) {
      setError("Please enter a valid email first");
      return;
    }
    setLoading(true);
    setError('');
    try {
      const { data } = await api.post('/auth/send-otp', {
        email: formData.email,
        purpose: 'signup'
      });
      if (data.success) {
        setOtpSent(true);
        setSuccess('OTP sent to your email!');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async (otpValue) => {
    setOtp(otpValue);
    setLoading(true);
    setError('');
    try {
      // Frontend verification (endpoint uses consume=False)
      const { data } = await api.post('/auth/verify-otp', {
        email: formData.email,
        otp: otpValue,
        purpose: 'signup'
      });
      if (data.success) {
        setOtpVerified(true);
        setSuccess('Email Verified!');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!otpVerified) {
      setError('Please verify your email first.');
      return;
    }

    setLoading(true);

    const payload = {
      company_name: formData.companyName,
      username: formData.username,
      email: formData.email,
      password: formData.password,
      contact_number: formData.contactNumber,
      website: formData.website,
      company_description: formData.description,
      otp: otp // Include OTP for backend verification
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
              disabled={otpVerified}
            />
          </div>

          {/* OTP Section */}
          {!otpVerified && (
            <div className="form-group" style={{ marginBottom: '20px' }}>
              {!otpSent ? (
                <button type="button" className="form-button" style={{ background: '#555' }} onClick={handleSendOTP} disabled={loading}>
                  {loading ? 'Sending...' : 'Verify Email'}
                </button>
              ) : (
                <div style={{ marginTop: '10px' }}>
                  <label className="form-label">Enter OTP Sent to Email</label>
                  <OTPInput onComplete={handleVerifyOTP} disabled={loading} />
                  <button type="button" className="resend-link" onClick={handleSendOTP} disabled={loading} style={{ marginTop: '5px' }}>
                    Resend Code
                  </button>
                </div>
              )}
            </div>
          )}

          {otpVerified && (
            <div className="verified-badge" style={{ color: '#00c851', fontWeight: 'bold', marginBottom: '15px', display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span>✓</span> Email Verified Successfully
            </div>
          )}

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

          <button type="submit" className="form-button" disabled={loading || !otpVerified}>
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
