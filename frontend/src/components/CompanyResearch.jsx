import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { researchService } from '../services/researchService';
import SidebarLeft from './SidebarLeft';
import { FiSearch, FiBuilding, FiUsers, FiCode, FiTrendingUp, FiExternalLink, FiBookOpen } from 'react-icons/fi';
import '../App.css';

const CompanyResearch = () => {
               const navigate = useNavigate();
               const { user } = useAuth();
               const [company, setCompany] = useState('');
               const [loading, setLoading] = useState(false);
               const [research, setResearch] = useState(null);
               const [activeTab, setActiveTab] = useState('overview');
               const [recentSearches, setRecentSearches] = useState([]);

               useEffect(() => {
                              if (!user) {
                                             navigate('/');
                              }
                              // Load recent searches from localStorage
                              const saved = localStorage.getItem('recentCompanySearches');
                              if (saved) setRecentSearches(JSON.parse(saved));
               }, [user, navigate]);

               const handleSearch = async () => {
                              if (!company.trim()) return;
                              setLoading(true);
                              setResearch(null);

                              try {
                                             const data = await researchService.deepResearch(company, ['culture', 'interview', 'tech', 'salary']);
                                             setResearch(data);

                                             // Update recent searches
                                             const updated = [company, ...recentSearches.filter(c => c.toLowerCase() !== company.toLowerCase())].slice(0, 5);
                                             setRecentSearches(updated);
                                             localStorage.setItem('recentCompanySearches', JSON.stringify(updated));
                              } catch (err) {
                                             console.error('Research failed:', err);
                              } finally {
                                             setLoading(false);
                              }
               };

               const tabs = [
                              { id: 'overview', label: 'Overview', icon: FiBuilding },
                              { id: 'culture', label: 'Culture', icon: FiUsers },
                              { id: 'interview', label: 'Interview Process', icon: FiBookOpen },
                              { id: 'tech', label: 'Tech Stack', icon: FiCode },
               ];

               if (!user) return null;

               return (
                              <div className="dashboard-container">
                                             <SidebarLeft />
                                             <div className="dashboard-main">
                                                            <div className="dashboard-header">
                                                                           <h1 className="dashboard-title">Company Research</h1>
                                                            </div>
                                                            <div className="dashboard-content">
                                                                           {/* Search */}
                                                                           <div className="card" style={{ marginBottom: '1.5rem' }}>
                                                                                          <h3 style={{ marginBottom: '1rem', color: '#2c3e50', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                                                         <FiSearch />
                                                                                                         Research a Company
                                                                                          </h3>
                                                                                          <div style={{ display: 'flex', gap: '1rem' }}>
                                                                                                         <input
                                                                                                                        type="text"
                                                                                                                        value={company}
                                                                                                                        onChange={(e) => setCompany(e.target.value)}
                                                                                                                        placeholder="e.g., Google, Amazon, Microsoft, Flipkart"
                                                                                                                        className="form-input"
                                                                                                                        style={{ flex: 1, marginBottom: 0 }}
                                                                                                                        onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                                                                                                         />
                                                                                                         <button
                                                                                                                        onClick={handleSearch}
                                                                                                                        disabled={loading || !company.trim()}
                                                                                                                        className="form-button"
                                                                                                                        style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                                                                                                         >
                                                                                                                        <FiSearch />
                                                                                                                        {loading ? 'Researching...' : 'Deep Research'}
                                                                                                         </button>
                                                                                          </div>

                                                                                          {/* Recent searches */}
                                                                                          {recentSearches.length > 0 && (
                                                                                                         <div style={{ marginTop: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                                                                                                                        <span style={{ fontSize: '0.875rem', color: '#64748b' }}>Recent:</span>
                                                                                                                        {recentSearches.map((c, idx) => (
                                                                                                                                       <button
                                                                                                                                                      key={idx}
                                                                                                                                                      onClick={() => { setCompany(c); }}
                                                                                                                                                      style={{
                                                                                                                                                                     padding: '0.25rem 0.75rem',
                                                                                                                                                                     background: '#f1f5f9',
                                                                                                                                                                     border: '1px solid #e2e8f0',
                                                                                                                                                                     borderRadius: '9999px',
                                                                                                                                                                     fontSize: '0.875rem',
                                                                                                                                                                     cursor: 'pointer',
                                                                                                                                                                     color: '#475569'
                                                                                                                                                      }}
                                                                                                                                       >
                                                                                                                                                      {c}
                                                                                                                                       </button>
                                                                                                                        ))}
                                                                                                         </div>
                                                                                          )}
                                                                           </div>

                                                                           {/* Loading */}
                                                                           {loading && (
                                                                                          <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
                                                                                                         <div className="loading-spinner" style={{ margin: '0 auto 1rem' }} />
                                                                                                         <p style={{ color: '#64748b' }}>Gathering insights about {company}...</p>
                                                                                                         <p style={{ fontSize: '0.875rem', color: '#94a3b8' }}>This may take a few moments</p>
                                                                                          </div>
                                                                           )}

                                                                           {/* Results */}
                                                                           {research && !loading && (
                                                                                          <div className="card">
                                                                                                         {/* Company Header */}
                                                                                                         <div style={{
                                                                                                                        display: 'flex',
                                                                                                                        alignItems: 'center',
                                                                                                                        gap: '1rem',
                                                                                                                        marginBottom: '1.5rem',
                                                                                                                        paddingBottom: '1.5rem',
                                                                                                                        borderBottom: '1px solid #e2e8f0'
                                                                                                         }}>
                                                                                                                        <div style={{
                                                                                                                                       width: '64px',
                                                                                                                                       height: '64px',
                                                                                                                                       background: 'linear-gradient(135deg, #667eea, #764ba2)',
                                                                                                                                       borderRadius: '12px',
                                                                                                                                       display: 'flex',
                                                                                                                                       alignItems: 'center',
                                                                                                                                       justifyContent: 'center',
                                                                                                                                       color: 'white',
                                                                                                                                       fontSize: '1.5rem',
                                                                                                                                       fontWeight: 'bold'
                                                                                                                        }}>
                                                                                                                                       {company.charAt(0).toUpperCase()}
                                                                                                                        </div>
                                                                                                                        <div>
                                                                                                                                       <h2 style={{ margin: 0, color: '#1e293b' }}>{research.company_name || company}</h2>
                                                                                                                                       <p style={{ margin: '0.25rem 0 0', color: '#64748b' }}>
                                                                                                                                                      {research.industry || 'Technology'} • {research.headquarters || 'Global'}
                                                                                                                                       </p>
                                                                                                                        </div>
                                                                                                                        {research.website && (
                                                                                                                                       <a
                                                                                                                                                      href={research.website}
                                                                                                                                                      target="_blank"
                                                                                                                                                      rel="noopener noreferrer"
                                                                                                                                                      style={{ marginLeft: 'auto' }}
                                                                                                                                                      className="edit-button"
                                                                                                                                       >
                                                                                                                                                      <FiExternalLink style={{ marginRight: '0.5rem' }} />
                                                                                                                                                      Website
                                                                                                                                       </a>
                                                                                                                        )}
                                                                                                         </div>

                                                                                                         {/* Tabs */}
                                                                                                         <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '1px solid #e2e8f0', paddingBottom: '1rem' }}>
                                                                                                                        {tabs.map(tab => (
                                                                                                                                       <button
                                                                                                                                                      key={tab.id}
                                                                                                                                                      onClick={() => setActiveTab(tab.id)}
                                                                                                                                                      style={{
                                                                                                                                                                     padding: '0.5rem 1rem',
                                                                                                                                                                     border: 'none',
                                                                                                                                                                     background: activeTab === tab.id ? 'linear-gradient(135deg, #3b82f6, #8b5cf6)' : 'transparent',
                                                                                                                                                                     color: activeTab === tab.id ? 'white' : '#64748b',
                                                                                                                                                                     borderRadius: '8px',
                                                                                                                                                                     cursor: 'pointer',
                                                                                                                                                                     display: 'flex',
                                                                                                                                                                     alignItems: 'center',
                                                                                                                                                                     gap: '0.5rem',
                                                                                                                                                                     fontWeight: activeTab === tab.id ? 600 : 400
                                                                                                                                                      }}
                                                                                                                                       >
                                                                                                                                                      <tab.icon />
                                                                                                                                                      {tab.label}
                                                                                                                                       </button>
                                                                                                                        ))}
                                                                                                         </div>

                                                                                                         {/* Tab Content */}
                                                                                                         <div>
                                                                                                                        {activeTab === 'overview' && (
                                                                                                                                       <div>
                                                                                                                                                      <p style={{ color: '#374151', lineHeight: 1.7 }}>
                                                                                                                                                                     {research.overview || research.summary || 'No overview available.'}
                                                                                                                                                      </p>
                                                                                                                                                      {research.key_facts && (
                                                                                                                                                                     <div style={{ marginTop: '1.5rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                                                                                                                                                                                    {Object.entries(research.key_facts).map(([key, value]) => (
                                                                                                                                                                                                   <div key={key} style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
                                                                                                                                                                                                                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: '0.25rem' }}>{key}</div>
                                                                                                                                                                                                                  <div style={{ fontWeight: 600, color: '#1e293b' }}>{value}</div>
                                                                                                                                                                                                   </div>
                                                                                                                                                                                    ))}
                                                                                                                                                                     </div>
                                                                                                                                                      )}
                                                                                                                                       </div>
                                                                                                                        )}

                                                                                                                        {activeTab === 'culture' && (
                                                                                                                                       <div>
                                                                                                                                                      <p style={{ color: '#374151', lineHeight: 1.7 }}>
                                                                                                                                                                     {research.culture || 'Culture information not available.'}
                                                                                                                                                      </p>
                                                                                                                                                      {research.values && (
                                                                                                                                                                     <div style={{ marginTop: '1rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                                                                                                                                                                                    {research.values.map((v, idx) => (
                                                                                                                                                                                                   <span key={idx} style={{ padding: '0.375rem 0.75rem', background: '#eff6ff', color: '#3b82f6', borderRadius: '9999px', fontSize: '0.875rem' }}>
                                                                                                                                                                                                                  {v}
                                                                                                                                                                                                   </span>
                                                                                                                                                                                    ))}
                                                                                                                                                                     </div>
                                                                                                                                                      )}
                                                                                                                                       </div>
                                                                                                                        )}

                                                                                                                        {activeTab === 'interview' && (
                                                                                                                                       <div>
                                                                                                                                                      <p style={{ color: '#374151', lineHeight: 1.7, marginBottom: '1rem' }}>
                                                                                                                                                                     {research.interview_process || 'Interview process details not available.'}
                                                                                                                                                      </p>
                                                                                                                                                      {research.interview_tips && research.interview_tips.length > 0 && (
                                                                                                                                                                     <div>
                                                                                                                                                                                    <h4 style={{ color: '#1e293b', marginBottom: '0.75rem' }}>💡 Interview Tips</h4>
                                                                                                                                                                                    <ul style={{ paddingLeft: '1.25rem', color: '#475569' }}>
                                                                                                                                                                                                   {research.interview_tips.map((tip, idx) => (
                                                                                                                                                                                                                  <li key={idx} style={{ marginBottom: '0.5rem' }}>{tip}</li>
                                                                                                                                                                                                   ))}
                                                                                                                                                                                    </ul>
                                                                                                                                                                     </div>
                                                                                                                                                      )}
                                                                                                                                                      {research.common_questions && research.common_questions.length > 0 && (
                                                                                                                                                                     <div style={{ marginTop: '1.5rem' }}>
                                                                                                                                                                                    <h4 style={{ color: '#1e293b', marginBottom: '0.75rem' }}>📝 Common Questions</h4>
                                                                                                                                                                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                                                                                                                                                                                   {research.common_questions.map((q, idx) => (
                                                                                                                                                                                                                  <div key={idx} style={{ padding: '0.75rem', background: '#f8fafc', borderRadius: '8px', borderLeft: '3px solid #3b82f6' }}>
                                                                                                                                                                                                                                 {q}
                                                                                                                                                                                                                  </div>
                                                                                                                                                                                                   ))}
                                                                                                                                                                                    </div>
                                                                                                                                                                     </div>
                                                                                                                                                      )}
                                                                                                                                       </div>
                                                                                                                        )}

                                                                                                                        {activeTab === 'tech' && (
                                                                                                                                       <div>
                                                                                                                                                      <p style={{ color: '#374151', lineHeight: 1.7, marginBottom: '1rem' }}>
                                                                                                                                                                     {research.tech_overview || 'Tech stack information not available.'}
                                                                                                                                                      </p>
                                                                                                                                                      {research.tech_stack && (
                                                                                                                                                                     <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                                                                                                                                                                                    {(Array.isArray(research.tech_stack) ? research.tech_stack : Object.keys(research.tech_stack)).map((tech, idx) => (
                                                                                                                                                                                                   <span
                                                                                                                                                                                                                  key={idx}
                                                                                                                                                                                                                  style={{
                                                                                                                                                                                                                                 padding: '0.5rem 1rem',
                                                                                                                                                                                                                                 background: 'linear-gradient(135deg, #667eea, #764ba2)',
                                                                                                                                                                                                                                 color: 'white',
                                                                                                                                                                                                                                 borderRadius: '8px',
                                                                                                                                                                                                                                 fontSize: '0.875rem',
                                                                                                                                                                                                                                 fontWeight: 500
                                                                                                                                                                                                                  }}
                                                                                                                                                                                                   >
                                                                                                                                                                                                                  {tech}
                                                                                                                                                                                                   </span>
                                                                                                                                                                                    ))}
                                                                                                                                                                     </div>
                                                                                                                                                      )}
                                                                                                                                       </div>
                                                                                                                        )}
                                                                                                         </div>

                                                                                                         {/* Action Buttons */}
                                                                                                         <div style={{ marginTop: '2rem', paddingTop: '1.5rem', borderTop: '1px solid #e2e8f0', display: 'flex', gap: '1rem' }}>
                                                                                                                        <button onClick={() => navigate('/mock-interview')} className="form-button" style={{ margin: 0 }}>
                                                                                                                                       Practice Interview for {company}
                                                                                                                        </button>
                                                                                                                        <button onClick={() => navigate('/opportunities')} className="edit-button" style={{ margin: 0 }}>
                                                                                                                                       Find Jobs at {company}
                                                                                                                        </button>
                                                                                                         </div>
                                                                                          </div>
                                                                           )}
                                                            </div>
                                             </div>
                              </div>
               );
};

export default CompanyResearch;
