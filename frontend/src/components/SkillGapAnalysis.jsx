import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { gapService } from '../services/gapService';
import { learningService } from '../services/learningService';
import SidebarLeft from './SidebarLeft';
import { FiTrendingUp, FiTarget, FiArrowRight, FiBook, FiAlertTriangle, FiCheckCircle, FiCpu } from 'react-icons/fi';
import '../App.css';

const SkillGapAnalysis = () => {
               const navigate = useNavigate();
               const { user } = useAuth();
               const [gaps, setGaps] = useState([]);
               const [loading, setLoading] = useState(true);
               const [targetRole, setTargetRole] = useState('');
               const [generating, setGenerating] = useState(null);

               useEffect(() => {
                              if (!user) {
                                             navigate('/');
                                             return;
                              }
                              loadGaps();
               }, [user, navigate]);

               const loadGaps = async () => {
                              try {
                                             const data = await gapService.getMyGaps();
                                             setGaps(data.gaps || data || []);
                              } catch (err) {
                                             console.error('Failed to load gaps:', err);
                              } finally {
                                             setLoading(false);
                              }
               };

               const handleAnalyzeRole = async () => {
                              if (!targetRole.trim()) return;
                              setLoading(true);
                              try {
                                             const data = await gapService.getGapWithRecommendations(targetRole);
                                             setGaps(data.gaps || data || []);
                              } catch (err) {
                                             console.error('Failed to analyze:', err);
                              } finally {
                                             setLoading(false);
                              }
               };

               const handleGeneratePath = async (skill) => {
                              setGenerating(skill);
                              try {
                                             await learningService.generatePath(skill);
                                             navigate('/learning');
                              } catch (err) {
                                             console.error('Failed to generate path:', err);
                              } finally {
                                             setGenerating(null);
                              }
               };

               const getPriorityColor = (priority) => {
                              switch (priority?.toUpperCase()) {
                                             case 'HIGH': return { bg: '#fef2f2', border: '#fecaca', text: '#dc2626' };
                                             case 'MEDIUM': return { bg: '#fffbeb', border: '#fed7aa', text: '#d97706' };
                                             case 'LOW': return { bg: '#f0fdf4', border: '#bbf7d0', text: '#16a34a' };
                                             default: return { bg: '#f8fafc', border: '#e2e8f0', text: '#64748b' };
                              }
               };

               if (!user) return null;

               return (
                              <div className="dashboard-container">
                                             <SidebarLeft />
                                             <div className="dashboard-main">
                                                            <div className="dashboard-header">
                                                                           <h1 className="dashboard-title animate-fade-in">Skill Gap Analysis</h1>
                                                            </div>
                                                            <div className="dashboard-content">
                                                                           {/* Target Role Input */}
                                                                           <div className="card glass-card animate-slide-up" style={{ marginBottom: '1.5rem' }}>
                                                                                          <h3 style={{ marginBottom: '1rem', color: '#2c3e50', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                                                         <FiTarget className="text-blue-500" />
                                                                                                         Target Role Analysis
                                                                                          </h3>
                                                                                          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                                                                                                         <input
                                                                                                                        type="text"
                                                                                                                        value={targetRole}
                                                                                                                        onChange={(e) => setTargetRole(e.target.value)}
                                                                                                                        placeholder="e.g., Backend Developer, Data Scientist, ML Engineer"
                                                                                                                        className="form-input"
                                                                                                                        style={{ flex: 1, marginBottom: 0, transition: 'all 0.3s' }}
                                                                                                         />
                                                                                                         <button
                                                                                                                        onClick={handleAnalyzeRole}
                                                                                                                        disabled={loading || !targetRole.trim()}
                                                                                                                        className="form-button hover-scale"
                                                                                                                        style={{ margin: 0, whiteSpace: 'nowrap' }}
                                                                                                         >
                                                                                                                        {loading ? 'Analyzing...' : 'Analyze Gaps'}
                                                                                                         </button>
                                                                                          </div>
                                                                           </div>

                                                                           {/* Current Skills */}
                                                                           {user.skills && user.skills.length > 0 && (
                                                                                          <div className="card animate-slide-up delay-100" style={{ marginBottom: '1.5rem' }}>
                                                                                                         <h3 style={{ marginBottom: '1rem', color: '#2c3e50', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                                                                        <FiCheckCircle style={{ color: '#10b981' }} />
                                                                                                                        Your Current Skills
                                                                                                         </h3>
                                                                                                         <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                                                                                                                        {user.skills.map((skill, idx) => (
                                                                                                                                       <div
                                                                                                                                                      key={idx}
                                                                                                                                                      className="hover-scale"
                                                                                                                                                      style={{
                                                                                                                                                                     padding: '0.5rem 1rem',
                                                                                                                                                                     background: '#f0fdf4',
                                                                                                                                                                     border: '1px solid #bbf7d0',
                                                                                                                                                                     borderRadius: '9999px',
                                                                                                                                                                     display: 'flex',
                                                                                                                                                                     alignItems: 'center',
                                                                                                                                                                     gap: '0.5rem',
                                                                                                                                                                     transition: 'all 0.2s',
                                                                                                                                                                     cursor: 'default'
                                                                                                                                                      }}
                                                                                                                                       >
                                                                                                                                                      <span style={{ fontWeight: 500, color: '#166534' }}>
                                                                                                                                                                     {typeof skill === 'string' ? skill : skill.name}
                                                                                                                                                      </span>
                                                                                                                                                      {skill.level && (
                                                                                                                                                                     <span style={{
                                                                                                                                                                                    fontSize: '0.75rem',
                                                                                                                                                                                    background: '#16a34a',
                                                                                                                                                                                    color: 'white',
                                                                                                                                                                                    padding: '0.125rem 0.5rem',
                                                                                                                                                                                    borderRadius: '9999px'
                                                                                                                                                                     }}>
                                                                                                                                                                                    {skill.level}%
                                                                                                                                                                     </span>
                                                                                                                                                      )}
                                                                                                                                       </div>
                                                                                                                        ))}
                                                                                                         </div>
                                                                                          </div>
                                                                           )}

                                                                           {/* Gap Analysis Results */}
                                                                           <div className="card animate-slide-up delay-200">
                                                                                          <h3 style={{ marginBottom: '1rem', color: '#2c3e50', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                                                         <FiTrendingUp style={{ color: '#3b82f6' }} />
                                                                                                         Skill Gaps {targetRole && `for ${targetRole}`}
                                                                                          </h3>

                                                                                          {loading ? (
                                                                                                         <div style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
                                                                                                                        <div style={{ display: 'inline-block', animation: 'pulse 2s infinite' }}>
                                                                                                                                       <FiCpu size={48} style={{ color: '#94a3b8', marginBottom: '1rem' }} />
                                                                                                                        </div>
                                                                                                                        <p>Analyzing your skill gaps against market data...</p>
                                                                                                         </div>
                                                                                          ) : gaps.length === 0 ? (
                                                                                                         <div style={{ textAlign: 'center', padding: '3rem' }}>
                                                                                                                        <FiCheckCircle size={48} style={{ color: '#10b981', marginBottom: '1rem' }} />
                                                                                                                        <p style={{ color: '#64748b' }}>
                                                                                                                                       {targetRole
                                                                                                                                                      ? 'Great! You have most skills for this role.'
                                                                                                                                                      : 'Enter a target role to analyze skill gaps.'}
                                                                                                                        </p>
                                                                                                         </div>
                                                                                          ) : (
                                                                                                         <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                                                                                                        {gaps.map((gap, idx) => {
                                                                                                                                       const colors = getPriorityColor(gap.priority);
                                                                                                                                       return (
                                                                                                                                                      <div
                                                                                                                                                                     key={idx}
                                                                                                                                                                     className="interactive-card"
                                                                                                                                                                     style={{
                                                                                                                                                                                    padding: '1.25rem',
                                                                                                                                                                                    background: colors.bg,
                                                                                                                                                                                    border: `1px solid ${colors.border}`,
                                                                                                                                                                                    borderRadius: '12px',
                                                                                                                                                                                    display: 'flex',
                                                                                                                                                                                    alignItems: 'center',
                                                                                                                                                                                    justifyContent: 'space-between',
                                                                                                                                                                                    animationDelay: `${idx * 100}ms`
                                                                                                                                                                     }}
                                                                                                                                                      >
                                                                                                                                                                     <div style={{ flex: 1 }}>
                                                                                                                                                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                                                                                                                                                                                                   <FiAlertTriangle style={{ color: colors.text }} />
                                                                                                                                                                                                   <span style={{ fontWeight: 600, fontSize: '1.1rem', color: '#1e293b' }}>
                                                                                                                                                                                                                  {gap.skill || gap.name}
                                                                                                                                                                                                   </span>
                                                                                                                                                                                                   <span
                                                                                                                                                                                                                  style={{
                                                                                                                                                                                                                                 fontSize: '0.75rem',
                                                                                                                                                                                                                                 padding: '0.25rem 0.75rem',
                                                                                                                                                                                                                                 background: colors.text,
                                                                                                                                                                                                                                 color: 'white',
                                                                                                                                                                                                                                 borderRadius: '9999px',
                                                                                                                                                                                                                                 fontWeight: 600,
                                                                                                                                                                                                                                 boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                                                                                                                                                                                                                  }}
                                                                                                                                                                                                   >
                                                                                                                                                                                                                  {gap.priority || 'MEDIUM'} PRIORITY
                                                                                                                                                                                                   </span>
                                                                                                                                                                                    </div>
                                                                                                                                                                                    <p style={{ color: '#64748b', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                                                                                                                                                                                                   {gap.reason || gap.description || 'Required for your target role'}
                                                                                                                                                                                    </p>
                                                                                                                                                                                    {gap.current_level !== undefined && (
                                                                                                                                                                                                   <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                                                                                                                                                                                                  <span style={{ fontSize: '0.875rem', color: '#94a3b8' }}>
                                                                                                                                                                                                                                 Current: {gap.current_level}%
                                                                                                                                                                                                                  </span>
                                                                                                                                                                                                                  <FiArrowRight style={{ color: '#94a3b8' }} />
                                                                                                                                                                                                                  <span style={{ fontSize: '0.875rem', color: '#10b981', fontWeight: 500 }}>
                                                                                                                                                                                                                                 Required: {gap.required_level || gap.target_level || 70}%
                                                                                                                                                                                                                  </span>
                                                                                                                                                                                                   </div>
                                                                                                                                                                                    )}
                                                                                                                                                                     </div>
                                                                                                                                                                     <button
                                                                                                                                                                                    onClick={() => handleGeneratePath(gap.skill || gap.name)}
                                                                                                                                                                                    disabled={generating === (gap.skill || gap.name)}
                                                                                                                                                                                    className="form-button hover-scale"
                                                                                                                                                                                    style={{
                                                                                                                                                                                                   margin: 0,
                                                                                                                                                                                                   display: 'flex',
                                                                                                                                                                                                   alignItems: 'center',
                                                                                                                                                                                                   gap: '0.5rem',
                                                                                                                                                                                                   whiteSpace: 'nowrap',
                                                                                                                                                                                                   background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                                                                                                                                                                                                   boxShadow: '0 4px 6px -1px rgba(37, 99, 235, 0.2)'
                                                                                                                                                                                    }}
                                                                                                                                                                     >
                                                                                                                                                                                    <FiBook />
                                                                                                                                                                                    {generating === (gap.skill || gap.name) ? 'Creating...' : 'Start Learning'}
                                                                                                                                                                     </button>
                                                                                                                                                      </div>
                                                                                                                                       );
                                                                                                                        })}
                                                                                                         </div>
                                                                                          )}
                                                                           </div>
                                                            </div>
                                             </div>
                              </div>
               );
};

export default SkillGapAnalysis;
