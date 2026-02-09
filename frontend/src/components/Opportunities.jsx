import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { recommendationService } from '../services/recommendationService';
import SidebarLeft from './SidebarLeft';
import { FiBriefcase, FiZap, FiBookOpen, FiStar, FiClock, FiMapPin, FiDollarSign, FiExternalLink, FiHeart, FiX, FiFilter, FiSearch } from 'react-icons/fi';
import '../App.css';

const Opportunities = () => {
               const navigate = useNavigate();
               const { user } = useAuth();
               const [activeTab, setActiveTab] = useState('jobs');
               const [jobs, setJobs] = useState([]);
               const [hackathons, setHackathons] = useState([]);
               const [content, setContent] = useState([]);
               const [loading, setLoading] = useState(true);
               const [filters, setFilters] = useState({ skill: '', location: '' });

               useEffect(() => {
                              if (!user) {
                                             navigate('/');
                                             return;
                              }
                              loadOpportunities();
               }, [user, navigate, activeTab]);

               const loadOpportunities = async () => {
                              setLoading(true);
                              try {
                                             if (activeTab === 'jobs') {
                                                            const data = await recommendationService.getJobRecommendations(20, filters);
                                                            const raw = data.recommendations || data.jobs || data || [];
                                                            setJobs(raw.map(item => item.job ? { ...item.job, score: item.score, match_details: item.match_details } : item));
                                             } else if (activeTab === 'hackathons') {
                                                            const data = await recommendationService.getHackathonRecommendations(15);
                                                            const raw = data.recommendations || data.hackathons || data || [];
                                                            setHackathons(raw.map(item => item.hackathon ? { ...item.hackathon, score: item.score, match_details: item.match_details } : item));
                                             } else {
                                                            const data = await recommendationService.getContentRecommendations(15);
                                                            const raw = data.recommendations || data.content || data || [];
                                                            setContent(raw.map(item => item.article ? { ...item.article, score: item.score, match_details: item.match_details } : item));
                                             }
                              } catch (err) {
                                             console.error('Failed to load opportunities:', err);
                              } finally {
                                             setLoading(false);
                              }
               };

               const handleFeedback = async (id, type, action) => {
                              try {
                                             await recommendationService.recordFeedback(id, type, action);
                                             if (action === 'dismiss') {
                                                            if (type === 'job') setJobs(jobs.filter(j => (j._id || j.id) !== id));
                                                            if (type === 'hackathon') setHackathons(hackathons.filter(h => (h._id || h.id) !== id));
                                                            if (type === 'content') setContent(content.filter(c => (c._id || c.id) !== id));
                                             }
                              } catch (err) {
                                             console.error('Failed to record feedback:', err);
                              }
               };

               const getScoreColor = (score) => {
                              if (score >= 80) return '#10b981';
                              if (score >= 60) return '#f59e0b';
                              return '#6b7280';
               };

               const tabs = [
                              { id: 'jobs', label: 'Jobs', icon: FiBriefcase },
                              { id: 'hackathons', label: 'Hackathons', icon: FiZap },
                              { id: 'content', label: 'Content', icon: FiBookOpen },
               ];

               if (!user) return null;

               return (
                              <div className="dashboard-container">
                                             <SidebarLeft />
                                             <div className="dashboard-main">
                                                            <div className="dashboard-header">
                                                                           <h1 className="dashboard-title animate-fade-in">Opportunities</h1>
                                                            </div>
                                                            <div className="dashboard-content">
                                                                           {/* Tabs */}
                                                                           <div className="animate-slide-up" style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
                                                                                          {tabs.map(tab => (
                                                                                                         <button
                                                                                                                        key={tab.id}
                                                                                                                        onClick={() => setActiveTab(tab.id)}
                                                                                                                        className="interactive-card"
                                                                                                                        style={{
                                                                                                                                       padding: '1rem 2rem',
                                                                                                                                       border: 'none',
                                                                                                                                       background: activeTab === tab.id ? 'linear-gradient(135deg, #3b82f6 0%, #6366f1 100%)' : 'white',
                                                                                                                                       color: activeTab === tab.id ? 'white' : '#64748b',
                                                                                                                                       borderRadius: '12px',
                                                                                                                                       cursor: 'pointer',
                                                                                                                                       display: 'flex',
                                                                                                                                       alignItems: 'center',
                                                                                                                                       gap: '0.75rem',
                                                                                                                                       fontWeight: 600,
                                                                                                                                       boxShadow: activeTab === tab.id ? '0 4px 6px -1px rgba(59, 130, 246, 0.4)' : '0 1px 3px rgba(0,0,0,0.1)',
                                                                                                                                       transition: 'all 0.3s ease'
                                                                                                                        }}
                                                                                                         >
                                                                                                                        <tab.icon size={20} />
                                                                                                                        {tab.label}
                                                                                                         </button>
                                                                                          ))}
                                                                           </div>

                                                                           {/* Filters for Jobs */}
                                                                           {activeTab === 'jobs' && (
                                                                                          <div className="card glass-card animate-slide-up delay-100" style={{ marginBottom: '2rem', padding: '1.5rem' }}>
                                                                                                         <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                                                                                                                        <div style={{ position: 'relative', flex: 1 }}>
                                                                                                                                       <FiSearch style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
                                                                                                                                       <input
                                                                                                                                                      type="text"
                                                                                                                                                      placeholder="Filter by skill..."
                                                                                                                                                      value={filters.skill}
                                                                                                                                                      onChange={(e) => setFilters({ ...filters, skill: e.target.value })}
                                                                                                                                                      className="form-input"
                                                                                                                                                      style={{ marginBottom: 0, paddingLeft: '2.5rem' }}
                                                                                                                                       />
                                                                                                                        </div>
                                                                                                                        <div style={{ position: 'relative', flex: 1 }}>
                                                                                                                                       <FiMapPin style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
                                                                                                                                       <input
                                                                                                                                                      type="text"
                                                                                                                                                      placeholder="Location..."
                                                                                                                                                      value={filters.location}
                                                                                                                                                      onChange={(e) => setFilters({ ...filters, location: e.target.value })}
                                                                                                                                                      className="form-input"
                                                                                                                                                      style={{ marginBottom: 0, paddingLeft: '2.5rem' }}
                                                                                                                                       />
                                                                                                                        </div>
                                                                                                                        <button onClick={loadOpportunities} className="form-button hover-scale" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                                                                                       <FiFilter /> Apply Filters
                                                                                                                        </button>
                                                                                                         </div>
                                                                                          </div>
                                                                           )}

                                                                           {/* Content Grid */}
                                                                           {loading ? (
                                                                                          <div className="card" style={{ textAlign: 'center', padding: '4rem' }}>
                                                                                                         <div className="loading-spinner" style={{ margin: '0 auto 1.5rem', width: '48px', height: '48px', border: '4px solid #e2e8f0', borderTop: '4px solid #3b82f6' }} />
                                                                                                         <p style={{ color: '#64748b', fontSize: '1.1rem' }}>Curating personalized {activeTab} for you...</p>
                                                                                          </div>
                                                                           ) : (
                                                                                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '1.5rem' }}>
                                                                                                         {activeTab === 'jobs' && jobs.map((job, idx) => (
                                                                                                                        <div
                                                                                                                                       key={job._id || job.id || idx}
                                                                                                                                       className="interactive-card animate-slide-up"
                                                                                                                                       style={{
                                                                                                                                                      padding: '1.5rem',
                                                                                                                                                      background: 'white',
                                                                                                                                                      borderRadius: '16px',
                                                                                                                                                      border: '1px solid #e2e8f0',
                                                                                                                                                      display: 'flex',
                                                                                                                                                      flexDirection: 'column',
                                                                                                                                                      justifyContent: 'space-between',
                                                                                                                                                      animationDelay: `${idx * 50}ms`,
                                                                                                                                                      height: '100%'
                                                                                                                                       }}
                                                                                                                        >
                                                                                                                                       <div>
                                                                                                                                                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                                                                                                                                                                     <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'linear-gradient(135deg, #e2e8f0 0%, #f1f5f9 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.5rem', fontWeight: 700, color: '#64748b' }}>
                                                                                                                                                                                    {job.company?.[0] || <FiBriefcase />}
                                                                                                                                                                     </div>
                                                                                                                                                                     {job.score !== undefined && (
                                                                                                                                                                                    <span style={{
                                                                                                                                                                                                   padding: '0.25rem 0.75rem',
                                                                                                                                                                                                   background: `${getScoreColor(job.score)}15`,
                                                                                                                                                                                                   color: getScoreColor(job.score),
                                                                                                                                                                                                   borderRadius: '9999px',
                                                                                                                                                                                                   fontWeight: 700,
                                                                                                                                                                                                   fontSize: '0.875rem',
                                                                                                                                                                                                   display: 'flex',
                                                                                                                                                                                                   alignItems: 'center',
                                                                                                                                                                                                   gap: '0.25rem'
                                                                                                                                                                                    }}>
                                                                                                                                                                                                   <FiStar fill={getScoreColor(job.score)} />
                                                                                                                                                                                                   {Math.round(job.score)}%
                                                                                                                                                                                    </span>
                                                                                                                                                                     )}
                                                                                                                                                      </div>

                                                                                                                                                      <h3 style={{ margin: '0 0 0.25rem', color: '#1e293b', fontSize: '1.1rem', lineHeight: '1.4' }}>{job.title}</h3>
                                                                                                                                                      <div style={{ color: '#64748b', marginBottom: '1rem', fontWeight: 500 }}>{job.company}</div>

                                                                                                                                                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1rem' }}>
                                                                                                                                                                     {job.location && (
                                                                                                                                                                                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.875rem', color: '#64748b', background: '#f8fafc', padding: '0.25rem 0.5rem', borderRadius: '6px' }}>
                                                                                                                                                                                                   <FiMapPin size={14} /> {job.location}
                                                                                                                                                                                    </span>
                                                                                                                                                                     )}
                                                                                                                                                                     {job.stipend && (
                                                                                                                                                                                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.875rem', color: '#64748b', background: '#f8fafc', padding: '0.25rem 0.5rem', borderRadius: '6px' }}>
                                                                                                                                                                                                   <FiDollarSign size={14} /> {job.stipend}
                                                                                                                                                                                    </span>
                                                                                                                                                                     )}
                                                                                                                                                      </div>

                                                                                                                                                      {job.skills && job.skills.length > 0 && (
                                                                                                                                                                     <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
                                                                                                                                                                                    {job.skills.slice(0, 3).map((skill, sIdx) => (
                                                                                                                                                                                                   <span key={sIdx} style={{
                                                                                                                                                                                                                  padding: '0.25rem 0.75rem',
                                                                                                                                                                                                                  background: user.skills?.some(s => (s.name || s).toLowerCase() === skill.toLowerCase()) ? '#dcfce7' : '#f1f5f9',
                                                                                                                                                                                                                  color: user.skills?.some(s => (s.name || s).toLowerCase() === skill.toLowerCase()) ? '#166534' : '#64748b',
                                                                                                                                                                                                                  borderRadius: '9999px',
                                                                                                                                                                                                                  fontSize: '0.75rem',
                                                                                                                                                                                                                  fontWeight: 500
                                                                                                                                                                                                   }}>
                                                                                                                                                                                                                  {skill}
                                                                                                                                                                                                   </span>
                                                                                                                                                                                    ))}
                                                                                                                                                                                    {job.skills.length > 3 && <span style={{ fontSize: '0.75rem', color: '#94a3b8', alignSelf: 'center' }}>+{job.skills.length - 3}</span>}
                                                                                                                                                                     </div>
                                                                                                                                                      )}
                                                                                                                                       </div>

                                                                                                                                       <div style={{ display: 'flex', gap: '0.75rem', marginTop: 'auto', borderTop: '1px solid #f1f5f9', paddingTop: '1rem' }}>
                                                                                                                                                      <button
                                                                                                                                                                     onClick={() => handleFeedback(job._id || job.id, 'job', 'save')}
                                                                                                                                                                     className="hover-scale"
                                                                                                                                                                     style={{ padding: '0.5rem', border: '1px solid #e2e8f0', borderRadius: '8px', background: 'white', cursor: 'pointer', color: '#64748b' }}
                                                                                                                                                                     title="Save"
                                                                                                                                                      >
                                                                                                                                                                     <FiHeart />
                                                                                                                                                      </button>
                                                                                                                                                      <button
                                                                                                                                                                     onClick={() => handleFeedback(job._id || job.id, 'job', 'dismiss')}
                                                                                                                                                                     className="hover-scale"
                                                                                                                                                                     style={{ padding: '0.5rem', border: '1px solid #e2e8f0', borderRadius: '8px', background: 'white', cursor: 'pointer', color: '#64748b' }}
                                                                                                                                                                     title="Dismiss"
                                                                                                                                                      >
                                                                                                                                                                     <FiX />
                                                                                                                                                      </button>
                                                                                                                                                      {job.url && (
                                                                                                                                                                     <a
                                                                                                                                                                                    href={job.url}
                                                                                                                                                                                    target="_blank"
                                                                                                                                                                                    rel="noopener noreferrer"
                                                                                                                                                                                    className="form-button hover-scale"
                                                                                                                                                                                    style={{ margin: 0, flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', textDecoration: 'none' }}
                                                                                                                                                                     >
                                                                                                                                                                                    Apply Now <FiExternalLink />
                                                                                                                                                                     </a>
                                                                                                                                                      )}
                                                                                                                                       </div>
                                                                                                                        </div>
                                                                                                         ))}

                                                                                                         {activeTab === 'hackathons' && hackathons.map((hack, idx) => (
                                                                                                                        <div
                                                                                                                                       key={hack._id || hack.id || idx}
                                                                                                                                       className="interactive-card animate-slide-up"
                                                                                                                                       style={{
                                                                                                                                                      padding: '1.5rem',
                                                                                                                                                      background: 'white',
                                                                                                                                                      borderRadius: '16px',
                                                                                                                                                      border: '1px solid #e2e8f0',
                                                                                                                                                      display: 'flex',
                                                                                                                                                      flexDirection: 'column',
                                                                                                                                                      justifyContent: 'space-between',
                                                                                                                                                      animationDelay: `${idx * 50}ms`,
                                                                                                                                                      height: '100%'
                                                                                                                                       }}
                                                                                                                        >
                                                                                                                                       <div>
                                                                                                                                                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                                                                                                                                                                     <div style={{ padding: '0.5rem', background: '#eff6ff', borderRadius: '10px', color: '#3b82f6' }}>
                                                                                                                                                                                    <FiZap size={24} />
                                                                                                                                                                     </div>
                                                                                                                                                                     {hack.start_date && (
                                                                                                                                                                                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.875rem', color: '#64748b', background: '#f8fafc', padding: '0.25rem 0.75rem', borderRadius: '9999px' }}>
                                                                                                                                                                                                   <FiClock size={14} /> {new Date(hack.start_date).toLocaleDateString()}
                                                                                                                                                                                    </span>
                                                                                                                                                                     )}
                                                                                                                                                      </div>

                                                                                                                                                      <h3 style={{ margin: '0 0 0.5rem', color: '#1e293b', fontSize: '1.1rem' }}>{hack.name || hack.event_name}</h3>
                                                                                                                                                      <p style={{ color: '#64748b', fontSize: '0.9rem', lineHeight: '1.5', marginBottom: '1rem', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                                                                                                                                                                     {hack.description}
                                                                                                                                                      </p>

                                                                                                                                                      {hack.themes && (
                                                                                                                                                                     <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1.5rem' }}>
                                                                                                                                                                                    {hack.themes.slice(0, 3).map((theme, tIdx) => (
                                                                                                                                                                                                   <span key={tIdx} style={{ padding: '0.25rem 0.75rem', background: '#f5f3ff', color: '#7c3aed', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: 500 }}>
                                                                                                                                                                                                                  {theme}
                                                                                                                                                                                                   </span>
                                                                                                                                                                                    ))}
                                                                                                                                                                     </div>
                                                                                                                                                      )}
                                                                                                                                       </div>

                                                                                                                                       {hack.url && (
                                                                                                                                                      <a
                                                                                                                                                                     href={hack.url}
                                                                                                                                                                     target="_blank"
                                                                                                                                                                     rel="noopener noreferrer"
                                                                                                                                                                     className="form-button hover-scale"
                                                                                                                                                                     style={{ margin: 0, textDecoration: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
                                                                                                                                                      >
                                                                                                                                                                     View Hackathon <FiExternalLink />
                                                                                                                                                      </a>
                                                                                                                                       )}
                                                                                                                        </div>
                                                                                                         ))}

                                                                                                         {activeTab === 'content' && content.map((item, idx) => (
                                                                                                                        <div
                                                                                                                                       key={item._id || item.id || idx}
                                                                                                                                       className="interactive-card animate-slide-up"
                                                                                                                                       style={{
                                                                                                                                                      padding: '1.5rem',
                                                                                                                                                      background: 'white',
                                                                                                                                                      borderRadius: '16px',
                                                                                                                                                      border: '1px solid #e2e8f0',
                                                                                                                                                      display: 'flex',
                                                                                                                                                      flexDirection: 'column',
                                                                                                                                                      justifyContent: 'space-between',
                                                                                                                                                      animationDelay: `${idx * 50}ms`,
                                                                                                                                                      height: '100%'
                                                                                                                                       }}
                                                                                                                        >
                                                                                                                                       <div>
                                                                                                                                                      <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                                                                                                                     <span style={{ padding: '0.25rem 0.75rem', background: '#fff7ed', color: '#c2410c', borderRadius: '9999px', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>
                                                                                                                                                                                    {item.topic || 'Article'}
                                                                                                                                                                     </span>
                                                                                                                                                                     <span style={{ fontSize: '0.875rem', color: '#94a3b8' }}>• {item.publisher}</span>
                                                                                                                                                      </div>

                                                                                                                                                      <h3 style={{ margin: '0 0 1rem', color: '#1e293b', fontSize: '1.1rem', lineHeight: '1.4' }}>{item.title}</h3>
                                                                                                                                       </div>

                                                                                                                                       {item.url && (
                                                                                                                                                      <a
                                                                                                                                                                     href={item.url}
                                                                                                                                                                     target="_blank"
                                                                                                                                                                     rel="noopener noreferrer"
                                                                                                                                                                     className="edit-button hover-scale"
                                                                                                                                                                     style={{ margin: 0, textDecoration: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
                                                                                                                                                      >
                                                                                                                                                                     Read Article <FiExternalLink />
                                                                                                                                                      </a>
                                                                                                                                       )}
                                                                                                                        </div>
                                                                                                         ))}
                                                                                          </div>
                                                                           )}

                                                                           {!loading && ((activeTab === 'jobs' && jobs.length === 0) || (activeTab === 'hackathons' && hackathons.length === 0) || (activeTab === 'content' && content.length === 0)) && (
                                                                                          <div className="card glass-card" style={{ textAlign: 'center', padding: '4rem' }}>
                                                                                                         <p style={{ color: '#64748b' }}>No {activeTab} found matching your criteria.</p>
                                                                                                         <button onClick={() => setFilters({ skill: '', location: '' })} className="edit-button" style={{ marginTop: '1rem' }}>
                                                                                                                        Clear Filters
                                                                                                         </button>
                                                                                          </div>
                                                                           )}
                                                            </div>
                                             </div>
                              </div>
               );
};

export default Opportunities;
