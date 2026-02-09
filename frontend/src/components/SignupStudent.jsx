import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api/client';
import OTPInput from './OTPInput';
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

  // Multi-step state
  const [step, setStep] = useState(1);
  const totalSteps = 4;

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

  const [otp, setOtp] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [otpVerified, setOtpVerified] = useState(false);

  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  // Real-time validation states
  const [usernameStatus, setUsernameStatus] = useState(null);
  const [emailStatus, setEmailStatus] = useState(null);
  const [passwordStrength, setPasswordStrength] = useState(0);

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

  // Send OTP for email verification
  const handleSendOTP = async () => {
    if (emailStatus !== 'available') {
      setError('Please enter a valid, available email first');
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

  // Verify OTP
  const handleVerifyOTP = async (otpValue) => {
    setOtp(otpValue);
    setLoading(true);
    setError('');

    try {
      const { data } = await api.post('/auth/verify-otp', {
        email: formData.email,
        otp: otpValue,
        purpose: 'signup'
      });

      if (data.success) {
        setOtpVerified(true);
        setSuccess('Email verified! ✓');
        setTimeout(() => setStep(3), 1000);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid OTP');
    } finally {
      setLoading(false);
    }
  };

  // Navigate steps
  const canProceedStep1 = formData.fullName && formData.username &&
    usernameStatus === 'available' && formData.password && passwordStrength >= 60;

  const canProceedStep2 = formData.email && emailStatus === 'available' && otpVerified;

  const canProceedStep3 = formData.prn && formData.college && formData.year && formData.branch;

  const nextStep = () => {
    setError('');
    setSuccess('');
    if (step < totalSteps) setStep(step + 1);
  };

  const prevStep = () => {
    setError('');
    setSuccess('');
    if (step > 1) setStep(step - 1);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

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
      otp: otp, // Include OTP for verification
    };

    const result = await signupStudent(payload);

    if (result.success) {
      setSuccess('🎉 Account created successfully! Redirecting to login...');
      setTimeout(() => navigate('/login/student'), 2000);
    } else {
      setError(result.error);
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'checking': return <span className="status-icon spinning">⟳</span>;
      case 'available': return <span className="status-icon success">✓</span>;
      case 'taken': return <span className="status-icon error">✗</span>;
      case 'invalid': return <span className="status-icon warning">!</span>;
      default: return null;
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
    <div className="auth-container modern">
      {/* Decorative Elements */}
      <div className="auth-decoration">
        <div className="floating-shape shape-1"></div>
        <div className="floating-shape shape-2"></div>
        <div className="floating-shape shape-3"></div>
      </div>

      <div className="auth-box glass signup-box">
        {/* Header */}
        <div className="auth-header">
          <div className="auth-icon">🎓</div>
          <h1 className="auth-title gradient-text">Student Sign Up</h1>
          <p className="auth-subtitle">Create your account in {totalSteps} easy steps</p>
        </div>

        {/* Progress Bar */}
        <div className="step-progress">
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${(step / totalSteps) * 100}%` }}
            ></div>
          </div>
          <div className="step-labels">
            <span className={step >= 1 ? 'active' : ''}>Account</span>
            <span className={step >= 2 ? 'active' : ''}>Verify</span>
            <span className={step >= 3 ? 'active' : ''}>Academic</span>
            <span className={step >= 4 ? 'active' : ''}>Skills</span>
          </div>
        </div>

        {error && <div className="error-message shake">{error}</div>}
        {success && <div className="success-message">{success}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>

          {/* Step 1: Basic Account Info */}
          {step === 1 && (
            <div className="form-step-content animate-fadeIn">
              <div className="step-header">
                <span className="step-badge">Step 1</span>
                <h2 className="step-title">Account Details</h2>
              </div>

              <div className="form-group modern">
                <input
                  type="text"
                  name="fullName"
                  className="form-input modern"
                  value={formData.fullName}
                  onChange={handleChange}
                  required
                  placeholder=" "
                />
                <label className="form-label floating">Full Name</label>
                <div className="input-icon">👤</div>
              </div>

              <div className="form-group modern">
                <div className="input-with-status">
                  <input
                    type="text"
                    name="username"
                    className={`form-input modern ${usernameStatus === 'taken' ? 'input-error' : usernameStatus === 'available' ? 'input-success' : ''}`}
                    value={formData.username}
                    onChange={handleChange}
                    required
                    placeholder=" "
                  />
                  <label className="form-label floating">Username</label>
                  {getStatusIcon(usernameStatus)}
                </div>
                {usernameStatus === 'taken' && <span className="field-error">Username already taken</span>}
                {usernameStatus === 'invalid' && <span className="field-warning">Min 3 characters</span>}
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
                  minLength="6"
                />
                <label className="form-label floating">Password</label>
                <div className="input-icon">🔒</div>
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

              <button
                type="button"
                className="form-button gradient"
                onClick={nextStep}
                disabled={!canProceedStep1}
              >
                Continue <span className="btn-arrow">→</span>
              </button>
            </div>
          )}

          {/* Step 2: Email Verification with OTP */}
          {step === 2 && (
            <div className="form-step-content animate-fadeIn">
              <div className="step-header">
                <span className="step-badge">Step 2</span>
                <h2 className="step-title">Verify Your Email</h2>
              </div>

              <div className="form-group modern">
                <div className="input-with-status">
                  <input
                    type="email"
                    name="email"
                    className={`form-input modern ${emailStatus === 'taken' ? 'input-error' : emailStatus === 'available' ? 'input-success' : ''}`}
                    value={formData.email}
                    onChange={handleChange}
                    required
                    placeholder=" "
                    disabled={otpVerified}
                  />
                  <label className="form-label floating">Email Address</label>
                  {getStatusIcon(emailStatus)}
                </div>
                {emailStatus === 'taken' && <span className="field-error">Email already registered</span>}
              </div>

              {!otpSent && !otpVerified && (
                <button
                  type="button"
                  className="form-button gradient"
                  onClick={handleSendOTP}
                  disabled={loading || emailStatus !== 'available'}
                >
                  {loading ? <span className="spinner"></span> : 'Send Verification Code'}
                </button>
              )}

              {otpSent && !otpVerified && (
                <div className="otp-section">
                  <p className="otp-info">Enter the 6-digit code sent to your email</p>
                  <OTPInput onComplete={handleVerifyOTP} disabled={loading} />
                  <button
                    type="button"
                    className="resend-link"
                    onClick={handleSendOTP}
                    disabled={loading}
                  >
                    Didn't receive code? Resend
                  </button>
                </div>
              )}

              {otpVerified && (
                <div className="verified-badge">
                  <span className="verified-icon">✓</span>
                  Email Verified Successfully!
                </div>
              )}

              <div className="step-nav">
                <button type="button" className="btn-back" onClick={prevStep}>
                  ← Back
                </button>
                {otpVerified && (
                  <button type="button" className="form-button gradient" onClick={nextStep}>
                    Continue <span className="btn-arrow">→</span>
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Step 3: Academic Info */}
          {step === 3 && (
            <div className="form-step-content animate-fadeIn">
              <div className="step-header">
                <span className="step-badge">Step 3</span>
                <h2 className="step-title">Academic Information</h2>
              </div>

              <div className="form-row">
                <div className="form-group modern half">
                  <input
                    type="text"
                    name="prn"
                    className="form-input modern"
                    value={formData.prn}
                    onChange={handleChange}
                    required
                    placeholder=" "
                  />
                  <label className="form-label floating">PRN Number</label>
                </div>

                <div className="form-group modern half">
                  <select
                    name="year"
                    className="form-input modern form-select"
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
              </div>

              <div className="form-group modern">
                <input
                  type="text"
                  name="college"
                  className="form-input modern"
                  value={formData.college}
                  onChange={handleChange}
                  required
                  placeholder=" "
                />
                <label className="form-label floating">College Name</label>
                <div className="input-icon">🏫</div>
              </div>

              <div className="form-group modern">
                <input
                  type="text"
                  name="branch"
                  className="form-input modern"
                  value={formData.branch}
                  onChange={handleChange}
                  required
                  placeholder=" "
                />
                <label className="form-label floating">Branch / Department</label>
                <div className="input-icon">📚</div>
              </div>

              <div className="step-nav">
                <button type="button" className="btn-back" onClick={prevStep}>
                  ← Back
                </button>
                <button
                  type="button"
                  className="form-button gradient"
                  onClick={nextStep}
                  disabled={!canProceedStep3}
                >
                  Continue <span className="btn-arrow">→</span>
                </button>
              </div>
            </div>
          )}

          {/* Step 4: Skills & Bio */}
          {step === 4 && (
            <div className="form-step-content animate-fadeIn">
              <div className="step-header">
                <span className="step-badge">Step 4</span>
                <h2 className="step-title">Skills & Profile</h2>
              </div>

              <div className="form-group modern">
                <input
                  type="text"
                  name="skills"
                  className="form-input modern"
                  value={formData.skills}
                  onChange={handleChange}
                  required
                  placeholder=" "
                />
                <label className="form-label floating">Your Skills</label>
                <div className="input-icon">💡</div>
                <span className="field-hint">Separate with commas: React, Python, ML</span>
              </div>

              <div className="form-group modern">
                <textarea
                  name="bio"
                  className="form-input modern form-textarea"
                  value={formData.bio}
                  onChange={handleChange}
                  placeholder=" "
                  rows="3"
                />
                <label className="form-label floating textarea-label">Bio (Optional)</label>
              </div>

              <div className="step-nav">
                <button type="button" className="btn-back" onClick={prevStep}>
                  ← Back
                </button>
                <button
                  type="submit"
                  className="form-button gradient"
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <span className="spinner"></span>
                      Creating Account...
                    </>
                  ) : (
                    '🚀 Create Account'
                  )}
                </button>
              </div>
            </div>
          )}
        </form>

        {/* Footer */}
        <div className="auth-footer">
          <div className="form-link" onClick={() => navigate('/login/student')}>
            Already have an account? <strong>Login</strong>
          </div>
          <div className="form-link back-link" onClick={() => navigate('/')}>
            ← Back to Home
          </div>
        </div>
      </div>
    </div>
  );
};

export default SignupStudent;
