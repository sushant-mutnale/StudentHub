import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { resumeService } from '../services/resumeService';
import SidebarLeft from './SidebarLeft';
import { FiUpload, FiFile, FiCheck, FiAlertCircle, FiRefreshCw } from 'react-icons/fi';
import '../App.css';

const ResumeUpload = () => {
               const navigate = useNavigate();
               const { user, refreshUser } = useAuth();
               const fileInputRef = useRef(null);

               const [file, setFile] = useState(null);
               const [loading, setLoading] = useState(false);
               const [result, setResult] = useState(null);
               const [error, setError] = useState('');
               const [dragOver, setDragOver] = useState(false);

               const handleFileSelect = (e) => {
                              const selectedFile = e.target.files?.[0];
                              if (selectedFile) {
                                             validateAndSetFile(selectedFile);
                              }
               };

               const validateAndSetFile = (selectedFile) => {
                              const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
                              if (!validTypes.includes(selectedFile.type)) {
                                             setError('Please upload a PDF or DOCX file');
                                             return;
                              }
                              if (selectedFile.size > 5 * 1024 * 1024) {
                                             setError('File size must be less than 5MB');
                                             return;
                              }
                              setFile(selectedFile);
                              setError('');
                              setResult(null);
               };

               const handleDrop = (e) => {
                              e.preventDefault();
                              setDragOver(false);
                              const droppedFile = e.dataTransfer.files?.[0];
                              if (droppedFile) {
                                             validateAndSetFile(droppedFile);
                              }
               };

               const handleUpload = async () => {
                              if (!file) return;

                              setLoading(true);
                              setError('');

                              try {
                                             const data = await resumeService.uploadResume(file);
                                             setResult(data);
                                             await refreshUser();
                              } catch (err) {
                                             setError(err.message || 'Failed to parse resume');
                              } finally {
                                             setLoading(false);
                              }
               };

               const handleRecalculate = async () => {
                              setLoading(true);
                              try {
                                             await resumeService.recalculate();
                                             await refreshUser();
                                             setResult({ ...result, recalculated: true });
                              } catch (err) {
                                             setError(err.message);
                              } finally {
                                             setLoading(false);
                              }
               };

               if (!user) return null;

               return (
                              <div className="dashboard-container">
                                             <SidebarLeft />
                                             <div className="dashboard-main">
                                                            <div className="dashboard-header">
                                                                           <h1 className="dashboard-title animate-fade-in">Resume Analysis</h1>
                                                            </div>
                                                            <div className="dashboard-content">
                                                                           {/* Upload Section */}
                                                                           <div className="card animate-slide-up" style={{ marginBottom: '1.5rem' }}>
                                                                                          <h3 style={{ marginBottom: '1rem', color: '#2c3e50' }}>
                                                                                                         <FiUpload style={{ marginRight: '0.5rem' }} />
                                                                                                         Upload Your Resume
                                                                                          </h3>

                                                                                          <div
                                                                                                         className={`upload-zone ${dragOver ? 'drag-over' : ''} interactive-card`}
                                                                                                         onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                                                                                                         onDragLeave={() => setDragOver(false)}
                                                                                                         onDrop={handleDrop}
                                                                                                         onClick={() => fileInputRef.current?.click()}
                                                                                                         style={{
                                                                                                                        border: '2px dashed #cbd5e0',
                                                                                                                        borderRadius: '12px',
                                                                                                                        padding: '3rem 2rem',
                                                                                                                        textAlign: 'center',
                                                                                                                        cursor: 'pointer',
                                                                                                                        background: dragOver ? 'rgba(59, 130, 246, 0.05)' : '#f8fafc',
                                                                                                                        transition: 'all 0.3s ease'
                                                                                                         }}
                                                                                          >
                                                                                                         <input
                                                                                                                        ref={fileInputRef}
                                                                                                                        type="file"
                                                                                                                        accept=".pdf,.docx"
                                                                                                                        onChange={handleFileSelect}
                                                                                                                        style={{ display: 'none' }}
                                                                                                         />
                                                                                                         <FiFile size={48} style={{ color: '#94a3b8', marginBottom: '1rem' }} />
                                                                                                         <p style={{ color: '#64748b', marginBottom: '0.5rem' }}>
                                                                                                                        Drag & drop your resume or <span style={{ color: '#3b82f6' }}>click to browse</span>
                                                                                                         </p>
                                                                                                         <p style={{ fontSize: '0.875rem', color: '#94a3b8' }}>
                                                                                                                        Supports PDF and DOCX (max 5MB)
                                                                                                         </p>
                                                                                          </div>

                                                                                          {file && (
                                                                                                         <div className="animate-fade-in" style={{ marginTop: '1rem', padding: '1rem', background: '#f0f9ff', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                                                                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                                                                                                                       <FiFile style={{ color: '#3b82f6' }} />
                                                                                                                                       <span style={{ fontWeight: 500 }}>{file.name}</span>
                                                                                                                                       <span style={{ fontSize: '0.875rem', color: '#64748b' }}>({(file.size / 1024).toFixed(1)} KB)</span>
                                                                                                                        </div>
                                                                                                                        <button
                                                                                                                                       onClick={handleUpload}
                                                                                                                                       disabled={loading}
                                                                                                                                       className="form-button hover-scale"
                                                                                                                                       style={{ margin: 0, padding: '0.5rem 1.5rem' }}
                                                                                                                        >
                                                                                                                                       {loading ? 'Analyzing...' : 'Analyze Resume'}
                                                                                                                        </button>
                                                                                                         </div>
                                                                                          )}

                                                                                          {error && (
                                                                                                         <div className="animate-fade-in" style={{ marginTop: '1rem', padding: '1rem', background: '#fef2f2', borderRadius: '8px', color: '#dc2626', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                                                                        <FiAlertCircle />
                                                                                                                        {error}
                                                                                                         </div>
                                                                                          )}
                                                                           </div>

                                                                           {/* Results Section */}
                                                                           {result && (
                                                                                          <div className="card animate-slide-up delay-100">
                                                                                                         <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                                                                                                                        <h3 style={{ color: '#2c3e50', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                                                                                       <FiCheck style={{ color: '#10b981' }} />
                                                                                                                                       Resume Parsed Successfully
                                                                                                                        </h3>
                                                                                                                        <button
                                                                                                                                       onClick={handleRecalculate}
                                                                                                                                       disabled={loading}
                                                                                                                                       className="edit-button hover-scale"
                                                                                                                                       style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                                                                                                                        >
                                                                                                                                       <FiRefreshCw />
                                                                                                                                       Recalculate AI Profile
                                                                                                                        </button>
                                                                                                         </div>

                                                                                                         {/* AI Feedback Section - Added for Demo */}
                                                                                                         {result.feedback && (
                                                                                                                        <div style={{ marginBottom: '2rem' }} className="animate-slide-up delay-200">
                                                                                                                                       {/* Summary */}
                                                                                                                                       <div className="glass-card hover-scale" style={{ padding: '1.5rem', borderRadius: '12px', marginBottom: '1.5rem', borderLeft: '4px solid #3b82f6' }}>
                                                                                                                                                      <h4 style={{ color: '#1e40af', marginBottom: '0.5rem' }}>AI Executive Summary</h4>
                                                                                                                                                      <p style={{ color: '#1e3a8a', lineHeight: '1.6' }}>{result.feedback.summary}</p>
                                                                                                                                       </div>

                                                                                                                                       {/* Ratings */}
                                                                                                                                       {result.feedback.rating && (
                                                                                                                                                      <div style={{ marginBottom: '1.5rem' }} className="animate-slide-up delay-300">
                                                                                                                                                                     <h4 style={{ marginBottom: '1rem', color: '#374151' }}>
                                                                                                                                                                                    Detailed Scoring (<span className="gradient-text" style={{ fontWeight: 'bold' }}>{result.feedback.rating.overall}/10</span>)
                                                                                                                                                                     </h4>
                                                                                                                                                                     <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                                                                                                                                                                                    {result.feedback.rating.breakdown.map((item, idx) => (
                                                                                                                                                                                                   <div key={idx} className="interactive-card" style={{ padding: '1rem', background: 'white', border: '1px solid #e2e8f0', borderRadius: '8px', animationDelay: `${idx * 100}ms` }}>
                                                                                                                                                                                                                  <div style={{ fontSize: '0.875rem', color: '#64748b', marginBottom: '0.25rem' }}>{item.aspect}</div>
                                                                                                                                                                                                                  <div style={{ fontSize: '1.25rem', fontWeight: 600, color: item.score >= 8 ? '#10b981' : item.score >= 6 ? '#f59e0b' : '#ef4444' }}>
                                                                                                                                                                                                                                 {item.score} <span style={{ fontSize: '0.875rem', color: '#94a3b8' }}>/ {item.max}</span>
                                                                                                                                                                                                                  </div>
                                                                                                                                                                                                   </div>
                                                                                                                                                                                    ))}
                                                                                                                                                                     </div>
                                                                                                                                                      </div>
                                                                                                                                       )}

                                                                                                                                       <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                                                                                                                                                      {/* Strengths */}
                                                                                                                                                      {result.feedback.strengths && (
                                                                                                                                                                     <div className="animate-slide-up delay-400">
                                                                                                                                                                                    <h4 style={{ marginBottom: '1rem', color: '#166534', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                                                                                                                                                   🟢 What is Excellent
                                                                                                                                                                                    </h4>
                                                                                                                                                                                    {result.feedback.strengths.map((str, idx) => (
                                                                                                                                                                                                   <div key={idx} className="hover-scale" style={{ padding: '1rem', background: '#f0fdf4', borderRadius: '8px', marginBottom: '0.75rem', border: '1px solid #bbf7d0', transition: 'all 0.2s' }}>
                                                                                                                                                                                                                  <div style={{ fontWeight: 600, color: '#166534', marginBottom: '0.25rem' }}>{str.title}</div>
                                                                                                                                                                                                                  <div style={{ fontSize: '0.875rem', color: '#15803d' }}>{str.description}</div>
                                                                                                                                                                                                   </div>
                                                                                                                                                                                    ))}
                                                                                                                                                                     </div>
                                                                                                                                                      )}

                                                                                                                                                      {/* Issues */}
                                                                                                                                                      {result.feedback.issues && (
                                                                                                                                                                     <div className="animate-slide-up delay-500">
                                                                                                                                                                                    <h4 style={{ marginBottom: '1rem', color: '#991b1b', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                                                                                                                                                   🔴 Major Issues
                                                                                                                                                                                    </h4>
                                                                                                                                                                                    {result.feedback.issues.map((iss, idx) => (
                                                                                                                                                                                                   <div key={idx} className="hover-scale" style={{ padding: '1rem', background: '#fef2f2', borderRadius: '8px', marginBottom: '0.75rem', border: '1px solid #fecaca', transition: 'all 0.2s' }}>
                                                                                                                                                                                                                  <div style={{ fontWeight: 600, color: '#991b1b', marginBottom: '0.25rem' }}>{iss.title}</div>
                                                                                                                                                                                                                  <div style={{ fontSize: '0.875rem', color: '#b91c1c' }}>{iss.description}</div>
                                                                                                                                                                                                   </div>
                                                                                                                                                                                    ))}
                                                                                                                                                                     </div>
                                                                                                                                                      )}
                                                                                                                                       </div>

                                                                                                                                       {/* Action Plan */}
                                                                                                                                       {result.feedback.action_plan && (
                                                                                                                                                      <div className="animate-slide-up delay-500 soft-shadow" style={{ marginTop: '1.5rem', padding: '1.5rem', background: '#fffbeb', borderRadius: '12px', border: '1px solid #fcd34d' }}>
                                                                                                                                                                     <h4 style={{ marginBottom: '1rem', color: '#92400e' }}>💡 Actionable Improvement Plan</h4>
                                                                                                                                                                     <ul style={{ paddingLeft: '1.5rem', margin: 0 }}>
                                                                                                                                                                                    {result.feedback.action_plan.map((action, idx) => (
                                                                                                                                                                                                   <li key={idx} style={{ marginBottom: '0.5rem', color: '#b45309' }}>{action}</li>
                                                                                                                                                                                    ))}
                                                                                                                                                                     </ul>
                                                                                                                                                      </div>
                                                                                                                                       )}
                                                                                                                        </div>
                                                                                                         )}

                                                                                                         {/* Extracted Info */}
                                                                                                         <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }} className="animate-fade-in delay-200">
                                                                                                                        {result.extracted_data?.name && (
                                                                                                                                       <div className="info-card hover-scale">
                                                                                                                                                      <div className="info-label">Name</div>
                                                                                                                                                      <div className="info-value">{result.extracted_data.name}</div>
                                                                                                                                       </div>
                                                                                                                        )}
                                                                                                                        {result.extracted_data?.email && (
                                                                                                                                       <div className="info-card hover-scale">
                                                                                                                                                      <div className="info-label">Email</div>
                                                                                                                                                      <div className="info-value">{result.extracted_data.email}</div>
                                                                                                                                       </div>
                                                                                                                        )}
                                                                                                                        {result.extracted_data?.phone && (
                                                                                                                                       <div className="info-card hover-scale">
                                                                                                                                                      <div className="info-label">Phone</div>
                                                                                                                                                      <div className="info-value">{result.extracted_data.phone}</div>
                                                                                                                                       </div>
                                                                                                                        )}
                                                                                                         </div>

                                                                                                         {/* Skills */}
                                                                                                         {result.extracted_data?.skills && result.extracted_data.skills.length > 0 && (
                                                                                                                        <div style={{ marginTop: '1.5rem' }} className="animate-fade-in delay-300">
                                                                                                                                       <h4 style={{ marginBottom: '0.75rem', color: '#374151' }}>Extracted Skills</h4>
                                                                                                                                       <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                                                                                                                                                      {result.extracted_data.skills.map((skill, idx) => (
                                                                                                                                                                     <span
                                                                                                                                                                                    key={idx}
                                                                                                                                                                                    className="hover-scale"
                                                                                                                                                                                    style={{
                                                                                                                                                                                                   padding: '0.375rem 0.75rem',
                                                                                                                                                                                                   background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                                                                                                                                                                                   color: 'white',
                                                                                                                                                                                                   borderRadius: '9999px',
                                                                                                                                                                                                   fontSize: '0.875rem',
                                                                                                                                                                                                   fontWeight: 500,
                                                                                                                                                                                                   boxShadow: '0 2px 4px rgba(102, 126, 234, 0.3)'
                                                                                                                                                                                    }}
                                                                                                                                                                     >
                                                                                                                                                                                    {typeof skill === 'string' ? skill : skill.name}
                                                                                                                                                                     </span>
                                                                                                                                                      ))}
                                                                                                                                       </div>
                                                                                                                        </div>
                                                                                                         )}

                                                                                                         {/* Experience */}
                                                                                                         {result.extracted_data?.experience && result.extracted_data.experience.length > 0 && (
                                                                                                                        <div style={{ marginTop: '1.5rem' }} className="animate-fade-in delay-400">
                                                                                                                                       <h4 style={{ marginBottom: '0.75rem', color: '#374151' }}>Experience</h4>
                                                                                                                                       {result.extracted_data.experience.map((exp, idx) => (
                                                                                                                                                      <div key={idx} className="hover-scale" style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', marginBottom: '0.75rem', borderLeft: '3px solid #64748b' }}>
                                                                                                                                                                     <div style={{ fontWeight: 600, color: '#1e293b' }}>{exp.title || exp.role}</div>
                                                                                                                                                                     <div style={{ color: '#64748b' }}>{exp.company} • {exp.duration}</div>
                                                                                                                                                      </div>
                                                                                                                                       ))}
                                                                                                                        </div>
                                                                                                         )}

                                                                                                         {/* Education */}
                                                                                                         {result.extracted_data?.education && result.extracted_data.education.length > 0 && (
                                                                                                                        <div style={{ marginTop: '1.5rem' }} className="animate-fade-in delay-500">
                                                                                                                                       <h4 style={{ marginBottom: '0.75rem', color: '#374151' }}>Education</h4>
                                                                                                                                       {result.extracted_data.education.map((edu, idx) => (
                                                                                                                                                      <div key={idx} className="hover-scale" style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', marginBottom: '0.75rem', borderLeft: '3px solid #64748b' }}>
                                                                                                                                                                     <div style={{ fontWeight: 600, color: '#1e293b' }}>{edu.degree}</div>
                                                                                                                                                                     <div style={{ color: '#64748b' }}>{edu.institution} • {edu.year}</div>
                                                                                                                                                      </div>
                                                                                                                                       ))}
                                                                                                                        </div>
                                                                                                         )}

                                                                                                         {/* Next Steps */}
                                                                                                         <div className="animate-slide-up delay-500" style={{ marginTop: '2rem', padding: '1.5rem', background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(147, 51, 234, 0.1) 100%)', borderRadius: '12px' }}>
                                                                                                                        <h4 style={{ marginBottom: '1rem', color: '#1e293b' }}>🚀 Next Steps</h4>
                                                                                                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
                                                                                                                                       <button onClick={() => navigate('/skill-gaps')} className="edit-button hover-scale" style={{ margin: 0 }}>
                                                                                                                                                      View Skill Gaps
                                                                                                                                       </button>
                                                                                                                                       <button onClick={() => navigate('/learning')} className="edit-button hover-scale" style={{ margin: 0 }}>
                                                                                                                                                      Start Learning Path
                                                                                                                                       </button>
                                                                                                                                       <button onClick={() => navigate('/opportunities')} className="edit-button hover-scale" style={{ margin: 0 }}>
                                                                                                                                                      Find Opportunities
                                                                                                                                       </button>
                                                                                                                        </div>
                                                                                                         </div>
                                                                                          </div>
                                                                           )}
                                                            </div>
                                             </div>
                              </div>
               );
};

export default ResumeUpload;
