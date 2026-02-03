import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { mockInterviewService } from '../services/mockInterviewService';
import { sandboxService } from '../services/sandboxService';
import SidebarLeft from './SidebarLeft';
import { FiMic, FiPlay, FiSend, FiClock, FiTarget, FiAward, FiCode, FiMessageSquare, FiHelpCircle } from 'react-icons/fi';
import '../App.css';

const MockInterview = () => {
               const navigate = useNavigate();
               const { user } = useAuth();
               const messagesEndRef = useRef(null);

               const [session, setSession] = useState(null);
               const [currentQuestion, setCurrentQuestion] = useState(null);
               const [answer, setAnswer] = useState('');
               const [code, setCode] = useState('');
               const [loading, setLoading] = useState(false);
               const [feedback, setFeedback] = useState(null);
               const [messages, setMessages] = useState([]);
               const [config, setConfig] = useState({
                              type: 'behavioral',
                              difficulty: 'medium',
                              topic: '',
                              company: ''
               });
               const [showConfig, setShowConfig] = useState(true);
               const [timer, setTimer] = useState(0);
               const [timerActive, setTimerActive] = useState(false);

               useEffect(() => {
                              if (!user) {
                                             navigate('/');
                              }
               }, [user, navigate]);

               useEffect(() => {
                              let interval;
                              if (timerActive) {
                                             interval = setInterval(() => {
                                                            setTimer(prev => prev + 1);
                                             }, 1000);
                              }
                              return () => clearInterval(interval);
               }, [timerActive]);

               useEffect(() => {
                              messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
               }, [messages]);

               const formatTime = (seconds) => {
                              const mins = Math.floor(seconds / 60);
                              const secs = seconds % 60;
                              return `${mins}:${secs.toString().padStart(2, '0')}`;
               };

               const startSession = async () => {
                              setLoading(true);
                              try {
                                             const sess = await mockInterviewService.startSession({
                                                            interview_type: config.type,
                                                            difficulty: config.difficulty,
                                                            topic: config.topic || undefined,
                                                            company: config.company || undefined
                                             });
                                             setSession(sess);
                                             setShowConfig(false);
                                             setTimerActive(true);

                                             // Get first question
                                             const question = await mockInterviewService.getNextQuestion(sess._id || sess.id || sess.session_id);
                                             setCurrentQuestion(question);

                                             setMessages([
                                                            { role: 'interviewer', content: `Welcome! Let's begin your ${config.type} interview${config.company ? ` for ${config.company}` : ''}.` },
                                                            { role: 'interviewer', content: question.question || question.text, type: question.type }
                                             ]);
                              } catch (err) {
                                             console.error('Failed to start session:', err);
                              } finally {
                                             setLoading(false);
                              }
               };

               const submitAnswer = async () => {
                              if (!answer.trim() && !code.trim()) return;

                              const userMessage = config.type === 'dsa' && code ? code : answer;
                              setMessages(prev => [...prev, { role: 'candidate', content: userMessage }]);
                              setLoading(true);

                              try {
                                             const sessionId = session._id || session.id || session.session_id;
                                             const questionId = currentQuestion._id || currentQuestion.id || currentQuestion.question_id;

                                             // For DSA, run code first
                                             if (config.type === 'dsa' && code) {
                                                            const codeResult = await sandboxService.runCode(code, 'python');
                                                            setMessages(prev => [...prev, {
                                                                           role: 'system',
                                                                           content: `Code Output:\n${codeResult.output || 'No output'}${codeResult.error ? `\nError: ${codeResult.error}` : ''}`
                                                            }]);
                                             }

                                             const result = await mockInterviewService.submitAnswer(sessionId, questionId, userMessage, code || null);

                                             setFeedback(result.feedback || result.evaluation);
                                             setMessages(prev => [...prev, {
                                                            role: 'feedback',
                                                            content: result.feedback?.summary || result.evaluation?.feedback || 'Answer recorded.',
                                                            score: result.feedback?.score || result.evaluation?.score
                                             }]);

                                             setAnswer('');
                                             setCode('');

                                             // Get next question if available
                                             if (!result.session_complete && !result.is_complete) {
                                                            const nextQ = await mockInterviewService.getNextQuestion(sessionId);
                                                            if (nextQ && nextQ.question) {
                                                                           setCurrentQuestion(nextQ);
                                                                           setMessages(prev => [...prev, {
                                                                                          role: 'interviewer',
                                                                                          content: nextQ.question || nextQ.text,
                                                                                          type: nextQ.type
                                                                           }]);
                                                            } else {
                                                                           endSession();
                                                            }
                                             } else {
                                                            endSession();
                                             }
                              } catch (err) {
                                             console.error('Failed to submit answer:', err);
                              } finally {
                                             setLoading(false);
                              }
               };

               const getHint = async () => {
                              if (!currentQuestion) return;
                              setLoading(true);
                              try {
                                             const sessionId = session._id || session.id || session.session_id;
                                             const questionId = currentQuestion._id || currentQuestion.id || currentQuestion.question_id;
                                             const hint = await mockInterviewService.getHint(sessionId, questionId);
                                             setMessages(prev => [...prev, {
                                                            role: 'hint',
                                                            content: hint.hint || hint.message || 'Think about the problem step by step...'
                                             }]);
                              } catch (err) {
                                             console.error('Failed to get hint:', err);
                              } finally {
                                             setLoading(false);
                              }
               };

               const endSession = async () => {
                              setTimerActive(false);
                              try {
                                             const sessionId = session._id || session.id || session.session_id;
                                             const summary = await mockInterviewService.getSummary(sessionId);
                                             setMessages(prev => [...prev, {
                                                            role: 'summary',
                                                            content: summary
                                             }]);
                              } catch (err) {
                                             console.error('Failed to get summary:', err);
                              }
               };

               if (!user) return null;

               return (
                              <div className="dashboard-container">
                                             <SidebarLeft />
                                             <div className="dashboard-main">
                                                            <div className="dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                                           <h1 className="dashboard-title">Mock Interview</h1>
                                                                           {session && (
                                                                                          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                                                                                         <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#64748b' }}>
                                                                                                                        <FiClock />
                                                                                                                        <span style={{ fontWeight: 600, fontFamily: 'monospace' }}>{formatTime(timer)}</span>
                                                                                                         </div>
                                                                                                         <button onClick={endSession} className="edit-button" style={{ margin: 0, background: '#ef4444', color: 'white' }}>
                                                                                                                        End Interview
                                                                                                         </button>
                                                                                          </div>
                                                                           )}
                                                            </div>

                                                            <div className="dashboard-content">
                                                                           {showConfig ? (
                                                                                          <div className="card" style={{ maxWidth: '600px', margin: '0 auto' }}>
                                                                                                         <h3 style={{ marginBottom: '1.5rem', color: '#2c3e50', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                                                                        <FiMic />
                                                                                                                        Configure Your Interview
                                                                                                         </h3>

                                                                                                         <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                                                                                                                        <div className="form-group" style={{ marginBottom: 0 }}>
                                                                                                                                       <label className="form-label">Interview Type</label>
                                                                                                                                       <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                                                                                                                                                      {[
                                                                                                                                                                     { value: 'behavioral', label: 'Behavioral', icon: FiMessageSquare },
                                                                                                                                                                     { value: 'technical', label: 'Technical', icon: FiTarget },
                                                                                                                                                                     { value: 'dsa', label: 'DSA/Coding', icon: FiCode },
                                                                                                                                                                     { value: 'system_design', label: 'System Design', icon: FiAward }
                                                                                                                                                      ].map(type => (
                                                                                                                                                                     <button
                                                                                                                                                                                    key={type.value}
                                                                                                                                                                                    onClick={() => setConfig({ ...config, type: type.value })}
                                                                                                                                                                                    style={{
                                                                                                                                                                                                   padding: '0.75rem 1.25rem',
                                                                                                                                                                                                   border: `2px solid ${config.type === type.value ? '#3b82f6' : '#e2e8f0'}`,
                                                                                                                                                                                                   borderRadius: '8px',
                                                                                                                                                                                                   background: config.type === type.value ? '#eff6ff' : 'white',
                                                                                                                                                                                                   cursor: 'pointer',
                                                                                                                                                                                                   display: 'flex',
                                                                                                                                                                                                   alignItems: 'center',
                                                                                                                                                                                                   gap: '0.5rem',
                                                                                                                                                                                                   fontWeight: config.type === type.value ? 600 : 400,
                                                                                                                                                                                                   color: config.type === type.value ? '#3b82f6' : '#64748b'
                                                                                                                                                                                    }}
                                                                                                                                                                     >
                                                                                                                                                                                    <type.icon />
                                                                                                                                                                                    {type.label}
                                                                                                                                                                     </button>
                                                                                                                                                      ))}
                                                                                                                                       </div>
                                                                                                                        </div>

                                                                                                                        <div className="form-group" style={{ marginBottom: 0 }}>
                                                                                                                                       <label className="form-label">Difficulty</label>
                                                                                                                                       <div style={{ display: 'flex', gap: '0.75rem' }}>
                                                                                                                                                      {['easy', 'medium', 'hard'].map(diff => (
                                                                                                                                                                     <button
                                                                                                                                                                                    key={diff}
                                                                                                                                                                                    onClick={() => setConfig({ ...config, difficulty: diff })}
                                                                                                                                                                                    style={{
                                                                                                                                                                                                   padding: '0.5rem 1.5rem',
                                                                                                                                                                                                   border: `2px solid ${config.difficulty === diff ? '#3b82f6' : '#e2e8f0'}`,
                                                                                                                                                                                                   borderRadius: '8px',
                                                                                                                                                                                                   background: config.difficulty === diff ? '#eff6ff' : 'white',
                                                                                                                                                                                                   cursor: 'pointer',
                                                                                                                                                                                                   fontWeight: config.difficulty === diff ? 600 : 400,
                                                                                                                                                                                                   color: config.difficulty === diff ? '#3b82f6' : '#64748b',
                                                                                                                                                                                                   textTransform: 'capitalize'
                                                                                                                                                                                    }}
                                                                                                                                                                     >
                                                                                                                                                                                    {diff}
                                                                                                                                                                     </button>
                                                                                                                                                      ))}
                                                                                                                                       </div>
                                                                                                                        </div>

                                                                                                                        <div className="form-group" style={{ marginBottom: 0 }}>
                                                                                                                                       <label className="form-label">Topic (optional)</label>
                                                                                                                                       <input
                                                                                                                                                      type="text"
                                                                                                                                                      value={config.topic}
                                                                                                                                                      onChange={(e) => setConfig({ ...config, topic: e.target.value })}
                                                                                                                                                      placeholder="e.g., Arrays, Leadership, Microservices"
                                                                                                                                                      className="form-input"
                                                                                                                                                      style={{ marginBottom: 0 }}
                                                                                                                                       />
                                                                                                                        </div>

                                                                                                                        <div className="form-group" style={{ marginBottom: 0 }}>
                                                                                                                                       <label className="form-label">Target Company (optional)</label>
                                                                                                                                       <input
                                                                                                                                                      type="text"
                                                                                                                                                      value={config.company}
                                                                                                                                                      onChange={(e) => setConfig({ ...config, company: e.target.value })}
                                                                                                                                                      placeholder="e.g., Google, Amazon, Microsoft"
                                                                                                                                                      className="form-input"
                                                                                                                                                      style={{ marginBottom: 0 }}
                                                                                                                                       />
                                                                                                                        </div>

                                                                                                                        <button
                                                                                                                                       onClick={startSession}
                                                                                                                                       disabled={loading}
                                                                                                                                       className="form-button"
                                                                                                                                       style={{ marginTop: '0.5rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
                                                                                                                        >
                                                                                                                                       <FiPlay />
                                                                                                                                       {loading ? 'Starting...' : 'Start Interview'}
                                                                                                                        </button>
                                                                                                         </div>
                                                                                          </div>
                                                                           ) : (
                                                                                          <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 200px)' }}>
                                                                                                         {/* Messages */}
                                                                                                         <div style={{
                                                                                                                        flex: 1,
                                                                                                                        overflowY: 'auto',
                                                                                                                        padding: '1rem',
                                                                                                                        display: 'flex',
                                                                                                                        flexDirection: 'column',
                                                                                                                        gap: '1rem'
                                                                                                         }}>
                                                                                                                        {messages.map((msg, idx) => (
                                                                                                                                       <div
                                                                                                                                                      key={idx}
                                                                                                                                                      style={{
                                                                                                                                                                     alignSelf: msg.role === 'candidate' ? 'flex-end' : 'flex-start',
                                                                                                                                                                     maxWidth: '80%'
                                                                                                                                                      }}
                                                                                                                                       >
                                                                                                                                                      <div style={{
                                                                                                                                                                     padding: '1rem',
                                                                                                                                                                     borderRadius: '12px',
                                                                                                                                                                     background: msg.role === 'candidate' ? 'linear-gradient(135deg, #3b82f6, #8b5cf6)' :
                                                                                                                                                                                    msg.role === 'feedback' ? '#f0fdf4' :
                                                                                                                                                                                                   msg.role === 'hint' ? '#fffbeb' :
                                                                                                                                                                                                                  msg.role === 'summary' ? 'linear-gradient(135deg, #667eea, #764ba2)' :
                                                                                                                                                                                                                                 '#f8fafc',
                                                                                                                                                                     color: ['candidate', 'summary'].includes(msg.role) ? 'white' : '#1e293b',
                                                                                                                                                                     border: msg.role === 'feedback' ? '1px solid #bbf7d0' :
                                                                                                                                                                                    msg.role === 'hint' ? '1px solid #fed7aa' : 'none'
                                                                                                                                                      }}>
                                                                                                                                                                     {msg.role === 'interviewer' && (
                                                                                                                                                                                    <div style={{ fontSize: '0.75rem', color: '#3b82f6', marginBottom: '0.5rem', fontWeight: 600 }}>
                                                                                                                                                                                                   Interviewer {msg.type && `• ${msg.type}`}
                                                                                                                                                                                    </div>
                                                                                                                                                                     )}
                                                                                                                                                                     {msg.role === 'feedback' && msg.score !== undefined && (
                                                                                                                                                                                    <div style={{ fontSize: '0.875rem', color: '#16a34a', marginBottom: '0.5rem', fontWeight: 600 }}>
                                                                                                                                                                                                   Score: {msg.score}/10
                                                                                                                                                                                    </div>
                                                                                                                                                                     )}
                                                                                                                                                                     {msg.role === 'summary' ? (
                                                                                                                                                                                    <div>
                                                                                                                                                                                                   <div style={{ fontWeight: 600, marginBottom: '0.75rem' }}>🎉 Interview Complete!</div>
                                                                                                                                                                                                   <div>Overall Score: {msg.content.overall_score || 'N/A'}</div>
                                                                                                                                                                                                   <div>Questions Answered: {msg.content.questions_answered || 'N/A'}</div>
                                                                                                                                                                                                   {msg.content.strengths && (
                                                                                                                                                                                                                  <div style={{ marginTop: '0.5rem' }}>Strengths: {msg.content.strengths.join(', ')}</div>
                                                                                                                                                                                                   )}
                                                                                                                                                                                    </div>
                                                                                                                                                                     ) : (
                                                                                                                                                                                    <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                                                                                                                                                                     )}
                                                                                                                                                      </div>
                                                                                                                                       </div>
                                                                                                                        ))}
                                                                                                                        <div ref={messagesEndRef} />
                                                                                                         </div>

                                                                                                         {/* Input Area */}
                                                                                                         <div style={{ padding: '1rem', borderTop: '1px solid #e2e8f0', background: 'white' }}>
                                                                                                                        {config.type === 'dsa' && (
                                                                                                                                       <div style={{ marginBottom: '1rem' }}>
                                                                                                                                                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                                                                                                                                                                     <label style={{ fontWeight: 500, color: '#374151' }}>Code (Python)</label>
                                                                                                                                                      </div>
                                                                                                                                                      <textarea
                                                                                                                                                                     value={code}
                                                                                                                                                                     onChange={(e) => setCode(e.target.value)}
                                                                                                                                                                     placeholder="def solution():\n    # Write your code here\n    pass"
                                                                                                                                                                     style={{
                                                                                                                                                                                    width: '100%',
                                                                                                                                                                                    minHeight: '150px',
                                                                                                                                                                                    padding: '1rem',
                                                                                                                                                                                    fontFamily: 'monospace',
                                                                                                                                                                                    fontSize: '0.875rem',
                                                                                                                                                                                    border: '1px solid #e2e8f0',
                                                                                                                                                                                    borderRadius: '8px',
                                                                                                                                                                                    resize: 'vertical',
                                                                                                                                                                                    background: '#f8fafc'
                                                                                                                                                                     }}
                                                                                                                                                      />
                                                                                                                                       </div>
                                                                                                                        )}

                                                                                                                        <div style={{ display: 'flex', gap: '0.75rem' }}>
                                                                                                                                       <textarea
                                                                                                                                                      value={answer}
                                                                                                                                                      onChange={(e) => setAnswer(e.target.value)}
                                                                                                                                                      placeholder={config.type === 'dsa' ? 'Explain your approach...' : 'Type your answer...'}
                                                                                                                                                      style={{
                                                                                                                                                                     flex: 1,
                                                                                                                                                                     padding: '0.75rem 1rem',
                                                                                                                                                                     border: '1px solid #e2e8f0',
                                                                                                                                                                     borderRadius: '8px',
                                                                                                                                                                     resize: 'none',
                                                                                                                                                                     minHeight: '60px'
                                                                                                                                                      }}
                                                                                                                                                      onKeyDown={(e) => e.ctrlKey && e.key === 'Enter' && submitAnswer()}
                                                                                                                                       />
                                                                                                                                       <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                                                                                                                                      <button
                                                                                                                                                                     onClick={getHint}
                                                                                                                                                                     disabled={loading}
                                                                                                                                                                     className="edit-button"
                                                                                                                                                                     style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.375rem' }}
                                                                                                                                                      >
                                                                                                                                                                     <FiHelpCircle />
                                                                                                                                                                     Hint
                                                                                                                                                      </button>
                                                                                                                                                      <button
                                                                                                                                                                     onClick={submitAnswer}
                                                                                                                                                                     disabled={loading || (!answer.trim() && !code.trim())}
                                                                                                                                                                     className="form-button"
                                                                                                                                                                     style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.375rem' }}
                                                                                                                                                      >
                                                                                                                                                                     <FiSend />
                                                                                                                                                                     Submit
                                                                                                                                                      </button>
                                                                                                                                       </div>
                                                                                                                        </div>
                                                                                                         </div>
                                                                                          </div>
                                                                           )}
                                                            </div>
                                             </div>
                              </div>
               );
};

export default MockInterview;
