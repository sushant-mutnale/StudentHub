import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import OTPInput from './OTPInput';
import '../App.css';

const API_BASE = 'https://studenthub-i7pa.onrender.com';

const ForgotPassword = () => {
               const navigate = useNavigate();
               const [step, setStep] = useState(1); // 1: email, 2: otp, 3: new password
               const [email, setEmail] = useState('');
               const [otp, setOtp] = useState('');
               const [newPassword, setNewPassword] = useState('');
               const [confirmPassword, setConfirmPassword] = useState('');
               const [loading, setLoading] = useState(false);
               const [error, setError] = useState('');
               const [success, setSuccess] = useState('');

               const handleSendOTP = async (e) => {
                              e.preventDefault();
                              setError('');
                              setLoading(true);

                              try {
                                             const res = await fetch(`${API_BASE}/auth/forgot-password`, {
                                                            method: 'POST',
                                                            headers: { 'Content-Type': 'application/json' },
                                                            body: JSON.stringify({ email, purpose: 'password_reset' }),
                                             });

                                             const data = await res.json();

                                             if (res.ok) {
                                                            setSuccess('OTP sent to your email!');
                                                            setStep(2);
                                             } else {
                                                            setError(data.detail || 'Failed to send OTP');
                                             }
                              } catch (err) {
                                             setError('Network error. Please try again.');
                              } finally {
                                             setLoading(false);
                              }
               };

               const handleVerifyOTP = async (otpValue) => {
                              setOtp(otpValue);
                              setError('');
                              setLoading(true);

                              try {
                                             const res = await fetch(`${API_BASE}/auth/verify-otp`, {
                                                            method: 'POST',
                                                            headers: { 'Content-Type': 'application/json' },
                                                            body: JSON.stringify({ email, otp: otpValue, purpose: 'password_reset' }),
                                             });

                                             const data = await res.json();

                                             if (res.ok) {
                                                            setSuccess('OTP verified! Set your new password.');
                                                            setStep(3);
                                             } else {
                                                            setError(data.detail || 'Invalid OTP');
                                             }
                              } catch (err) {
                                             setError('Network error. Please try again.');
                              } finally {
                                             setLoading(false);
                              }
               };

               const handleResetPassword = async (e) => {
                              e.preventDefault();
                              setError('');

                              if (newPassword !== confirmPassword) {
                                             setError('Passwords do not match');
                                             return;
                              }

                              if (newPassword.length < 8) {
                                             setError('Password must be at least 8 characters');
                                             return;
                              }

                              setLoading(true);

                              try {
                                             // Need to resend OTP for final verification
                                             const otpRes = await fetch(`${API_BASE}/auth/forgot-password`, {
                                                            method: 'POST',
                                                            headers: { 'Content-Type': 'application/json' },
                                                            body: JSON.stringify({ email, purpose: 'password_reset' }),
                                             });

                                             if (!otpRes.ok) {
                                                            setError('Session expired. Please start again.');
                                                            setStep(1);
                                                            return;
                                             }

                                             // For now, we'll use the remembered OTP
                                             const res = await fetch(`${API_BASE}/auth/reset-password`, {
                                                            method: 'POST',
                                                            headers: { 'Content-Type': 'application/json' },
                                                            body: JSON.stringify({ email, otp, new_password: newPassword }),
                                             });

                                             const data = await res.json();

                                             if (res.ok) {
                                                            setSuccess('Password reset successfully!');
                                                            setTimeout(() => navigate('/login/student'), 2000);
                                             } else {
                                                            setError(data.detail || 'Failed to reset password');
                                             }
                              } catch (err) {
                                             setError('Network error. Please try again.');
                              } finally {
                                             setLoading(false);
                              }
               };

               return (
                              <div className="auth-container modern">
                                             <div className="auth-box glass">
                                                            <div className="auth-header">
                                                                           <div className="auth-icon">🔐</div>
                                                                           <h1 className="auth-title gradient-text">
                                                                                          {step === 1 && 'Forgot Password'}
                                                                                          {step === 2 && 'Enter OTP'}
                                                                                          {step === 3 && 'New Password'}
                                                                           </h1>
                                                                           <p className="auth-subtitle">
                                                                                          {step === 1 && "Enter your email to receive a reset code"}
                                                                                          {step === 2 && `We sent a 6-digit code to ${email}`}
                                                                                          {step === 3 && "Create a strong new password"}
                                                                           </p>
                                                            </div>

                                                            {error && <div className="error-message shake">{error}</div>}
                                                            {success && <div className="success-message">{success}</div>}

                                                            {/* Step 1: Email */}
                                                            {step === 1 && (
                                                                           <form className="auth-form" onSubmit={handleSendOTP}>
                                                                                          <div className="form-group modern">
                                                                                                         <input
                                                                                                                        type="email"
                                                                                                                        className="form-input modern"
                                                                                                                        value={email}
                                                                                                                        onChange={(e) => setEmail(e.target.value)}
                                                                                                                        required
                                                                                                                        placeholder=" "
                                                                                                         />
                                                                                                         <label className="form-label floating">Email Address</label>
                                                                                          </div>
                                                                                          <button type="submit" className="form-button gradient" disabled={loading}>
                                                                                                         {loading ? <span className="spinner"></span> : 'Send Reset Code'}
                                                                                          </button>
                                                                           </form>
                                                            )}

                                                            {/* Step 2: OTP */}
                                                            {step === 2 && (
                                                                           <div className="otp-section">
                                                                                          <OTPInput onComplete={handleVerifyOTP} disabled={loading} />
                                                                                          <button
                                                                                                         className="resend-link"
                                                                                                         onClick={handleSendOTP}
                                                                                                         disabled={loading}
                                                                                          >
                                                                                                         Didn't receive code? Resend
                                                                                          </button>
                                                                           </div>
                                                            )}

                                                            {/* Step 3: New Password */}
                                                            {step === 3 && (
                                                                           <form className="auth-form" onSubmit={handleResetPassword}>
                                                                                          <div className="form-group modern">
                                                                                                         <input
                                                                                                                        type="password"
                                                                                                                        className="form-input modern"
                                                                                                                        value={newPassword}
                                                                                                                        onChange={(e) => setNewPassword(e.target.value)}
                                                                                                                        required
                                                                                                                        minLength={8}
                                                                                                                        placeholder=" "
                                                                                                         />
                                                                                                         <label className="form-label floating">New Password</label>
                                                                                          </div>
                                                                                          <div className="form-group modern">
                                                                                                         <input
                                                                                                                        type="password"
                                                                                                                        className="form-input modern"
                                                                                                                        value={confirmPassword}
                                                                                                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                                                                                                        required
                                                                                                                        placeholder=" "
                                                                                                         />
                                                                                                         <label className="form-label floating">Confirm Password</label>
                                                                                          </div>
                                                                                          <button type="submit" className="form-button gradient" disabled={loading}>
                                                                                                         {loading ? <span className="spinner"></span> : 'Reset Password'}
                                                                                          </button>
                                                                           </form>
                                                            )}

                                                            <div className="form-link" onClick={() => navigate('/')}>
                                                                           ← Back to Login
                                                            </div>
                                             </div>
                              </div>
               );
};

export default ForgotPassword;
