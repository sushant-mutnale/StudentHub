import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { opportunityService } from '../services/opportunityService';
import { recommendationService } from '../services/recommendationService';
import SidebarLeft from './SidebarLeft';
import { FiBriefcase, FiZap, FiBookOpen, FiStar, FiClock, FiMapPin, FiDollarSign, FiExternalLink, FiHeart, FiX } from 'react-icons/fi';
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
                                                            setJobs(data.recommendations || data.jobs || data || []);
                                             } else if (activeTab === 'hackathons') {
                                                            const data = await recommendationService.getHackathonRecommendations(15);
                                                            setHackathons(data.recommendations || data.hackathons || data || []);
                                             } else {
                                                            const data = await recommendationService.getContentRecommendations(15);
                                                            setContent(data.recommendations || data.content || data || []);
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
                                             // Update UI based on action
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
                              { id: 'jobs', label: 'Jobs', icon: FiBriefcase, count: jobs.length },
                              { id: 'hackathons', label: 'Hackathons', icon: FiZap, count: hackathons.length },
                              { id: 'content', label: 'Content', icon: FiBookOpen, count: content.length },
               ];

               if (!user) return null;

               return (
                              <div className="dashboard-container">
                                             <SidebarLeft />
                                             <div className="dashboard-main">
                                                            <div className="dashboard-header">
                                                                           <h1 className="dashboard-title">Opportunities</h1>
                                                            </div>
                                                            <div className="dashboard-content">
                                                                           {/* Tabs */}
                                                                           <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
                                                                                          {tabs.map(tab => (
                                                                                                         <button
                                                                                                                        key={tab.id}
                                                                                                                        onClick={() => setActiveTab(tab.id)}
                                                                                                                        style={{
                                                                                                                                       padding: '0.75rem 1.5rem',
                                                                                                                                       border: 'none',
                                                                                                                                       background: activeTab === tab.id ? 'linear-gradient(135deg, #3b82f6, #8b5cf6)' : '#f1f5f9',
                                                                                                                                       color: activeTab === tab.id ? 'white' : '#64748b',
                                                                                                                                       borderRadius: '10px',
                                                                                                                                       cursor: 'pointer',
                                                                                                                                       display: 'flex',
                                                                                                                                       alignItems: 'center',
                                                                                                                                       gap: '0.5rem',
                                                                                                                                       fontWeight: 500,
                                                                                                                                       transition: 'all 0.2s'
                                                                                                                        }}
                                                                                                         >
                                                                                                                        <tab.icon />
                                                                                                                        {tab.label}
                                                                                                         </button>
                                                                                          ))}
                                                                           </div>

                                                                           {/* Filters for Jobs */}
                                                                           {activeTab === 'jobs' && (
                                                                                          <div className="card" style={{ marginBottom: '1.5rem', padding: '1rem' }}>
                                                                                                         <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                                                                                                                        <input
                                                                                                                                       type="text"
                                                                                                                                       placeholder="Filter by skill..."
                                                                                                                                       value={filters.skill}
                                                                                                                                       onChange={(e) => setFilters({ ...filters, skill: e.target.value })}
                                                                                                                                       className="form-input"
                                                                                                                                       style={{ flex: 1, marginBottom: 0 }}
                                                                                                                        />
                                                                                                                        <input
                                                                                                                                       type="text"
                                                                                                                                       placeholder="Location..."
                                                                                                                                       value={filters.location}
                                                                                                                                       onChange={(e) => setFilters({ ...filters, location: e.target.value })}
                                                                                                                                       className="form-input"
                                                                                                                                       style={{ flex: 1, marginBottom: 0 }}
                                                                                                                        />
                                                                                                                        <button onClick={loadOpportunities} className="form-button" style={{ margin: 0 }}>
                                                                                                                                       Apply Filters
                                                                                                                        </button>
                                                                                                         </div>
                                                                                          </div>
                                                                           )}

                                                                           {/* Content */}
                                                                           {loading ? (
                                                                                          <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
                                                                                                         <div className="loading-spinner" style={{ margin: '0 auto 1rem' }} />
                                                                                                         <p style={{ color: '#64748b' }}>Finding personalized {activeTab}...</p>
                                                                                          </div>
                                                                           ) : (
                                                                                          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                                                                                         {activeTab === 'jobs' && jobs.map((job, idx) => (
                                                                                                                        <div key={job._id || job.id || idx} className="card" style={{ padding: '1.25rem' }}>
                                                                                                                                       <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                                                                                                                                      <div style={{ flex: 1 }}>
                                                                                                                                                                     <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                                                                                                                                                                                    <h3 style={{ margin: 0, color: '#1e293b' }}>{job.title}</h3>
                                                                                                                                                                                    {job.score !== undefined && (
                                                                                                                                                                                                   <span style={{
                                                                                                                                                                                                                  padding: '0.25rem 0.75rem',
                                                                                                                                                                                                                  background: `${getScoreColor(job.score)}20`,
                                                                                                                                                                                                                  color: getScoreColor(job.score),
                                                                                                                                                                                                                  borderRadius: '9999px',
                                                                                                                                                                                                                  fontWeight: 600,
                                                                                                                                                                                                                  fontSize: '0.875rem',
                                                                                                                                                                                                                  display: 'flex',
                                                                                                                                                                                                                  alignItems: 'center',
                                                                                                                                                                                                                  gap: '0.25rem'
                                                                                                                                                                                                   }}>
                                                                                                                                                                                                                  <FiStar size={14} />
                                                                                                                                                                                                                  {Math.round(job.score)}% match
                                                                                                                                                                                                   </span>
                                                                                                                                                                                    )}
                                                                                                                                                                     </div>
                                                                                                                                                                     <div style={{ color: '#64748b', marginBottom: '0.75rem' }}>{job.company}</div>
                                                                                                                                                                     <div style={{ display: 'flex', gap: '1rem', fontSize: '0.875rem', color: '#94a3b8', flexWrap: 'wrap' }}>
                                                                                                                                                                                    {job.location && (
                                                                                                                                                                                                   <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                                                                                                                                                                                                  <FiMapPin size={14} /> {job.location}
                                                                                                                                                                                                   </span>
                                                                                                                                                                                    )}
                                                                                                                                                                                    {job.stipend && (
                                                                                                                                                                                                   <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                                                                                                                                                                                                  <FiDollarSign size={14} /> {job.stipend}
                                                                                                                                                                                                   </span>
                                                                                                                                                                                    )}
                                                                                                                                                                                    {job.deadline && (
                                                                                                                                                                                                   <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                                                                                                                                                                                                  <FiClock size={14} /> Deadline: {new Date(job.deadline).toLocaleDateString()}
                                                                                                                                                                                                   </span>
                                                                                                                                                                                    )}
                                                                                                                                                                     </div>
                                                                                                                                                                     {job.skills && job.skills.length > 0 && (
                                                                                                                                                                                    <div style={{ display: 'flex', gap: '0.375rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
                                                                                                                                                                                                   {job.skills.slice(0, 5).map((skill, sIdx) => (
                                                                                                                                                                                                                  <span key={sIdx} style={{
                                                                                                                                                                                                                                 padding: '0.25rem 0.5rem',
                                                                                                                                                                                                                                 background: user.skills?.some(s => (s.name || s).toLowerCase() === skill.toLowerCase()) ? '#dcfce7' : '#f1f5f9',
                                                                                                                                                                                                                                 color: user.skills?.some(s => (s.name || s).toLowerCase() === skill.toLowerCase()) ? '#166534' : '#64748b',
                                                                                                                                                                                                                                 borderRadius: '4px',
                                                                                                                                                                                                                                 fontSize: '0.75rem'
                                                                                                                                                                                                                  }}>
                                                                                                                                                                                                                                 {skill}
                                                                                                                                                                                                                  </span>
                                                                                                                                                                                                   ))}
                                                                                                                                                                                    </div>
                                                                                                                                                                     )}
                                                                                                                                                      </div>
                                                                                                                                                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                                                                                                                                                                     <button
                                                                                                                                                                                    onClick={() => handleFeedback(job._id || job.id, 'job', 'save')}
                                                                                                                                                                                    style={{ padding: '0.5rem', border: '1px solid #e2e8f0', borderRadius: '8px', background: 'white', cursor: 'pointer' }}
                                                                                                                                                                                    title="Save"
                                                                                                                                                                     >
                                                                                                                                                                                    <FiHeart />
                                                                                                                                                                     </button>
                                                                                                                                                                     <button
                                                                                                                                                                                    onClick={() => handleFeedback(job._id || job.id, 'job', 'dismiss')}
                                                                                                                                                                                    style={{ padding: '0.5rem', border: '1px solid #e2e8f0', borderRadius: '8px', background: 'white', cursor: 'pointer' }}
                                                                                                                                                                                    title="Dismiss"
                                                                                                                                                                     >
                                                                                                                                                                                    <FiX />
                                                                                                                                                                     </button>
                                                                                                                                                                     {job.url && (
                                                                                                                                                                                    <a
                                                                                                                                                                                                   href={job.url}
                                                                                                                                                                                                   target="_blank"
                                                                                                                                                                                                   rel="noopener noreferrer"
                                                                                                                                                                                                   className="form-button"
                                                                                                                                                                                                   style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.375rem', textDecoration: 'none' }}
                                                                                                                                                                                    >
                                                                                                                                                                                                   <FiExternalLink /> Apply
                                                                                                                                                                                    </a>
                                                                                                                                                                     )}
                                                                                                                                                      </div>
                                                                                                                                       </div>
                                                                                                                        </div>
                                                                                                         ))}

                                                                                                         {activeTab === 'hackathons' && hackathons.map((hack, idx) => (
                                                                                                                        <div key={hack._id || hack.id || idx} className="card" style={{ padding: '1.25rem' }}>
                                                                                                                                       <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                                                                                                                                      <div>
                                                                                                                                                                     <h3 style={{ margin: '0 0 0.5rem', color: '#1e293b' }}>{hack.name || hack.event_name}</h3>
                                                                                                                                                                     <p style={{ color: '#64748b', marginBottom: '0.5rem' }}>{hack.description?.slice(0, 150)}...</p>
                                                                                                                                                                     <div style={{ display: 'flex', gap: '1rem', fontSize: '0.875rem', color: '#94a3b8' }}>
                                                                                                                                                                                    {hack.start_date && (
                                                                                                                                                                                                   <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                                                                                                                                                                                                  <FiClock size={14} /> {new Date(hack.start_date).toLocaleDateString()}
                                                                                                                                                                                                   </span>
                                                                                                                                                                                    )}
                                                                                                                                                                                    {hack.prize && (
                                                                                                                                                                                                   <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                                                                                                                                                                                                  <FiDollarSign size={14} /> {hack.prize}
                                                                                                                                                                                                   </span>
                                                                                                                                                                                    )}
                                                                                                                                                                     </div>
                                                                                                                                                                     {hack.themes && (
                                                                                                                                                                                    <div style={{ display: 'flex', gap: '0.375rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
                                                                                                                                                                                                   {hack.themes.slice(0, 4).map((theme, tIdx) => (
                                                                                                                                                                                                                  <span key={tIdx} style={{ padding: '0.25rem 0.5rem', background: '#eff6ff', color: '#3b82f6', borderRadius: '4px', fontSize: '0.75rem' }}>
                                                                                                                                                                                                                                 {theme}
                                                                                                                                                                                                                  </span>
                                                                                                                                                                                                   ))}
                                                                                                                                                                                    </div>
                                                                                                                                                                     )}
                                                                                                                                                      </div>
                                                                                                                                                      {hack.url && (
                                                                                                                                                                     <a href={hack.url} target="_blank" rel="noopener noreferrer" className="form-button" style={{ margin: 0, textDecoration: 'none' }}>
                                                                                                                                                                                    <FiExternalLink /> View
                                                                                                                                                                     </a>
                                                                                                                                                      )}
                                                                                                                                       </div>
                                                                                                                        </div>
                                                                                                         ))}

                                                                                                         {activeTab === 'content' && content.map((item, idx) => (
                                                                                                                        <div key={item._id || item.id || idx} className="card" style={{ padding: '1rem' }}>
                                                                                                                                       <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                                                                                                                      <div>
                                                                                                                                                                     <h4 style={{ margin: '0 0 0.25rem', color: '#1e293b' }}>{item.title}</h4>
                                                                                                                                                                     <div style={{ fontSize: '0.875rem', color: '#64748b' }}>
                                                                                                                                                                                    {item.publisher} • {item.topic}
                                                                                                                                                                     </div>
                                                                                                                                                      </div>
                                                                                                                                                      {item.url && (
                                                                                                                                                                     <a href={item.url} target="_blank" rel="noopener noreferrer" className="edit-button" style={{ margin: 0, textDecoration: 'none' }}>
                                                                                                                                                                                    Read
                                                                                                                                                                     </a>
                                                                                                                                                      )}
                                                                                                                                       </div>
                                                                                                                        </div>
                                                                                                         ))}

                                                                                                         {((activeTab === 'jobs' && jobs.length === 0) ||
                                                                                                                        (activeTab === 'hackathons' && hackathons.length === 0) ||
                                                                                                                        (activeTab === 'content' && content.length === 0)) && (
                                                                                                                                       <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
                                                                                                                                                      <p style={{ color: '#64748b' }}>No {activeTab} found. Check back later!</p>
                                                                                                                                       </div>
                                                                                                                        )}
                                                                                          </div>
                                                                           )}
                                                            </div>
                                             </div>
                              </div>
               );
};

export default Opportunities;
