import { useState, useRef, useEffect } from 'react';
import '../App.css';

/**
 * OTPInput Component
 * A modern 6-digit OTP input with auto-focus and animations.
 */
const OTPInput = ({ length = 6, onComplete, disabled = false }) => {
               const [otp, setOtp] = useState(new Array(length).fill(''));
               const inputRefs = useRef([]);

               useEffect(() => {
                              // Focus first input on mount
                              if (inputRefs.current[0]) {
                                             inputRefs.current[0].focus();
                              }
               }, []);

               const handleChange = (e, index) => {
                              const value = e.target.value;

                              // Only allow single digit
                              if (!/^\d*$/.test(value)) return;

                              const newOtp = [...otp];
                              newOtp[index] = value.slice(-1);
                              setOtp(newOtp);

                              // Auto-focus next input
                              if (value && index < length - 1) {
                                             inputRefs.current[index + 1].focus();
                              }

                              // Check if complete
                              const otpValue = newOtp.join('');
                              if (otpValue.length === length) {
                                             onComplete?.(otpValue);
                              }
               };

               const handleKeyDown = (e, index) => {
                              if (e.key === 'Backspace') {
                                             if (!otp[index] && index > 0) {
                                                            inputRefs.current[index - 1].focus();
                                             }
                              }
                              if (e.key === 'ArrowLeft' && index > 0) {
                                             inputRefs.current[index - 1].focus();
                              }
                              if (e.key === 'ArrowRight' && index < length - 1) {
                                             inputRefs.current[index + 1].focus();
                              }
               };

               const handlePaste = (e) => {
                              e.preventDefault();
                              const pastedData = e.clipboardData.getData('text').slice(0, length);
                              if (!/^\d+$/.test(pastedData)) return;

                              const newOtp = [...otp];
                              pastedData.split('').forEach((char, i) => {
                                             if (i < length) newOtp[i] = char;
                              });
                              setOtp(newOtp);

                              // Focus last filled input or next empty
                              const nextIndex = Math.min(pastedData.length, length - 1);
                              inputRefs.current[nextIndex].focus();

                              if (pastedData.length === length) {
                                             onComplete?.(pastedData);
                              }
               };

               return (
                              <div className="otp-container">
                                             {otp.map((digit, index) => (
                                                            <input
                                                                           key={index}
                                                                           ref={(el) => (inputRefs.current[index] = el)}
                                                                           type="text"
                                                                           inputMode="numeric"
                                                                           maxLength={1}
                                                                           value={digit}
                                                                           onChange={(e) => handleChange(e, index)}
                                                                           onKeyDown={(e) => handleKeyDown(e, index)}
                                                                           onPaste={handlePaste}
                                                                           disabled={disabled}
                                                                           className={`otp-input ${digit ? 'filled' : ''}`}
                                                                           autoComplete="one-time-code"
                                                            />
                                             ))}
                              </div>
               );
};

export default OTPInput;
