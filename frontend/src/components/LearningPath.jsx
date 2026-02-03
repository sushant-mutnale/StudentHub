import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { learningService } from '../services/learningService';
import SidebarLeft from './SidebarLeft';
import { FiBook, FiCheckCircle, FiCircle, FiPlay, FiAward, FiClock, FiExternalLink } from 'react-icons/fi';
import '../App.css';

const LearningPath = () => {
               const navigate = useNavigate();
               const { user } = useAuth();
               const [paths, setPaths] = useState([]);
               const [activePath, setActivePath] = useState(null);
               const [loading, setLoading] = useState(true);
               const [newSkill, setNewSkill] = useState('');
               const [generating, setGenerating] = useState(false);

               useEffect(() => {
                              if (!user) {
                                             navigate('/');
                                             return;
                              }
                              loadPaths();
               }, [user, navigate]);

               const loadPaths = async () => {
                              try {
                                             const data = await learningService.getMyPaths();
                                             setPaths(data.paths || data || []);
                                             if (data.paths?.length > 0 || data?.length > 0) {
                                                            setActivePath((data.paths || data)[0]);
                                             }
                              } catch (err) {
                                             console.error('Failed to load paths:', err);
                              } finally {
                                             setLoading(false);
                              }
               };

               const handleGeneratePath = async () => {
                              if (!newSkill.trim()) return;
                              setGenerating(true);
                              try {
                                             const newPath = await learningService.generatePath(newSkill);
                                             setPaths([newPath, ...paths]);
                                             setActivePath(newPath);
                                             setNewSkill('');
                              } catch (err) {
                                             console.error('Failed to generate path:', err);
                              } finally {
                                             setGenerating(false);
                              }
               };

               const handleCompleteStage = async (stageIndex) => {
                              if (!activePath) return;
                              try {
                                             const updated = await learningService.completeStage(activePath._id || activePath.id, stageIndex);
                                             setActivePath(updated);
                                             setPaths(paths.map(p => (p._id || p.id) === (activePath._id || activePath.id) ? updated : p));
                              } catch (err) {
                                             console.error('Failed to complete stage:', err);
                              }
               };

               const getProgress = (path) => {
                              if (!path?.stages) return 0;
                              const completed = path.stages.filter(s => s.completed).length;
                              return Math.round((completed / path.stages.length) * 100);
               };

               if (!user) return null;

               return (
                              <div className="dashboard-container">
                                             <SidebarLeft />
                                             <div className="dashboard-main">
                                                            <div className="dashboard-header">
                                                                           <h1 className="dashboard-title">Learning Paths</h1>
                                                            </div>
                                                            <div className="dashboard-content">
                                                                           {/* Generate New Path */}
                                                                           <div className="card" style={{ marginBottom: '1.5rem' }}>
                                                                                          <h3 style={{ marginBottom: '1rem', color: '#2c3e50', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                                                         <FiBook />
                                                                                                         Start a New Learning Path
                                                                                          </h3>
                                                                                          <div style={{ display: 'flex', gap: '1rem' }}>
                                                                                                         <input
                                                                                                                        type="text"
                                                                                                                        value={newSkill}
                                                                                                                        onChange={(e) => setNewSkill(e.target.value)}
                                                                                                                        placeholder="e.g., Docker, System Design, React"
                                                                                                                        className="form-input"
                                                                                                                        style={{ flex: 1, marginBottom: 0 }}
                                                                                                                        onKeyDown={(e) => e.key === 'Enter' && handleGeneratePath()}
                                                                                                         />
                                                                                                         <button
                                                                                                                        onClick={handleGeneratePath}
                                                                                                                        disabled={generating || !newSkill.trim()}
                                                                                                                        className="form-button"
                                                                                                                        style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                                                                                                         >
                                                                                                                        <FiPlay />
                                                                                                                        {generating ? 'Creating...' : 'Generate Path'}
                                                                                                         </button>
                                                                                          </div>
                                                                           </div>

                                                                           <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: '1.5rem' }}>
                                                                                          {/* Path List */}
                                                                                          <div className="card" style={{ height: 'fit-content' }}>
                                                                                                         <h4 style={{ marginBottom: '1rem', color: '#374151' }}>Your Paths</h4>
                                                                                                         {loading ? (
                                                                                                                        <div style={{ textAlign: 'center', padding: '1rem', color: '#64748b' }}>Loading...</div>
                                                                                                         ) : paths.length === 0 ? (
                                                                                                                        <div style={{ textAlign: 'center', padding: '1rem', color: '#64748b' }}>
                                                                                                                                       No learning paths yet. Create one above!
                                                                                                                        </div>
                                                                                                         ) : (
                                                                                                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                                                                                                                       {paths.map((path, idx) => (
                                                                                                                                                      <div
                                                                                                                                                                     key={path._id || path.id || idx}
                                                                                                                                                                     onClick={() => setActivePath(path)}
                                                                                                                                                                     style={{
                                                                                                                                                                                    padding: '1rem',
                                                                                                                                                                                    background: activePath === path ? '#eff6ff' : '#f8fafc',
                                                                                                                                                                                    border: `1px solid ${activePath === path ? '#3b82f6' : '#e2e8f0'}`,
                                                                                                                                                                                    borderRadius: '8px',
                                                                                                                                                                                    cursor: 'pointer',
                                                                                                                                                                                    transition: 'all 0.2s'
                                                                                                                                                                     }}
                                                                                                                                                      >
                                                                                                                                                                     <div style={{ fontWeight: 600, color: '#1e293b', marginBottom: '0.5rem' }}>
                                                                                                                                                                                    {path.skill || path.name}
                                                                                                                                                                     </div>
                                                                                                                                                                     <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                                                                                                                                    <div style={{
                                                                                                                                                                                                   flex: 1,
                                                                                                                                                                                                   height: '6px',
                                                                                                                                                                                                   background: '#e2e8f0',
                                                                                                                                                                                                   borderRadius: '3px',
                                                                                                                                                                                                   overflow: 'hidden'
                                                                                                                                                                                    }}>
                                                                                                                                                                                                   <div style={{
                                                                                                                                                                                                                  height: '100%',
                                                                                                                                                                                                                  width: `${getProgress(path)}%`,
                                                                                                                                                                                                                  background: 'linear-gradient(90deg, #3b82f6, #8b5cf6)',
                                                                                                                                                                                                                  borderRadius: '3px',
                                                                                                                                                                                                                  transition: 'width 0.3s'
                                                                                                                                                                                                   }} />
                                                                                                                                                                                    </div>
                                                                                                                                                                                    <span style={{ fontSize: '0.75rem', color: '#64748b', minWidth: '35px' }}>
                                                                                                                                                                                                   {getProgress(path)}%
                                                                                                                                                                                    </span>
                                                                                                                                                                     </div>
                                                                                                                                                      </div>
                                                                                                                                       ))}
                                                                                                                        </div>
                                                                                                         )}
                                                                                          </div>

                                                                                          {/* Active Path Details */}
                                                                                          <div className="card">
                                                                                                         {!activePath ? (
                                                                                                                        <div style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
                                                                                                                                       <FiBook size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                                                                                                                                       <p>Select a path or create a new one to get started</p>
                                                                                                                        </div>
                                                                                                         ) : (
                                                                                                                        <>
                                                                                                                                       <div style={{ marginBottom: '1.5rem' }}>
                                                                                                                                                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                                                                                                                                     <h2 style={{ color: '#1e293b', margin: 0 }}>{activePath.skill || activePath.name}</h2>
                                                                                                                                                                     <span style={{
                                                                                                                                                                                    padding: '0.5rem 1rem',
                                                                                                                                                                                    background: 'linear-gradient(135deg, #667eea, #764ba2)',
                                                                                                                                                                                    color: 'white',
                                                                                                                                                                                    borderRadius: '9999px',
                                                                                                                                                                                    fontWeight: 600
                                                                                                                                                                     }}>
                                                                                                                                                                                    {getProgress(activePath)}% Complete
                                                                                                                                                                     </span>
                                                                                                                                                      </div>
                                                                                                                                                      {activePath.description && (
                                                                                                                                                                     <p style={{ color: '#64748b', marginTop: '0.5rem' }}>{activePath.description}</p>
                                                                                                                                                      )}
                                                                                                                                       </div>

                                                                                                                                       {/* Timeline */}
                                                                                                                                       <div style={{ position: 'relative' }}>
                                                                                                                                                      {(activePath.stages || []).map((stage, idx) => (
                                                                                                                                                                     <div
                                                                                                                                                                                    key={idx}
                                                                                                                                                                                    style={{
                                                                                                                                                                                                   display: 'flex',
                                                                                                                                                                                                   gap: '1.5rem',
                                                                                                                                                                                                   marginBottom: idx < activePath.stages.length - 1 ? '2rem' : 0,
                                                                                                                                                                                                   position: 'relative'
                                                                                                                                                                                    }}
                                                                                                                                                                     >
                                                                                                                                                                                    {/* Timeline line */}
                                                                                                                                                                                    {idx < activePath.stages.length - 1 && (
                                                                                                                                                                                                   <div style={{
                                                                                                                                                                                                                  position: 'absolute',
                                                                                                                                                                                                                  left: '19px',
                                                                                                                                                                                                                  top: '40px',
                                                                                                                                                                                                                  width: '2px',
                                                                                                                                                                                                                  height: 'calc(100% + 0.5rem)',
                                                                                                                                                                                                                  background: stage.completed ? '#10b981' : '#e2e8f0'
                                                                                                                                                                                                   }} />
                                                                                                                                                                                    )}

                                                                                                                                                                                    {/* Status icon */}
                                                                                                                                                                                    <div
                                                                                                                                                                                                   onClick={() => !stage.completed && handleCompleteStage(idx)}
                                                                                                                                                                                                   style={{
                                                                                                                                                                                                                  width: '40px',
                                                                                                                                                                                                                  height: '40px',
                                                                                                                                                                                                                  borderRadius: '50%',
                                                                                                                                                                                                                  background: stage.completed ? '#10b981' : '#f1f5f9',
                                                                                                                                                                                                                  border: `2px solid ${stage.completed ? '#10b981' : '#e2e8f0'}`,
                                                                                                                                                                                                                  display: 'flex',
                                                                                                                                                                                                                  alignItems: 'center',
                                                                                                                                                                                                                  justifyContent: 'center',
                                                                                                                                                                                                                  cursor: stage.completed ? 'default' : 'pointer',
                                                                                                                                                                                                                  flexShrink: 0,
                                                                                                                                                                                                                  zIndex: 1
                                                                                                                                                                                                   }}
                                                                                                                                                                                    >
                                                                                                                                                                                                   {stage.completed ? (
                                                                                                                                                                                                                  <FiCheckCircle style={{ color: 'white' }} />
                                                                                                                                                                                                   ) : (
                                                                                                                                                                                                                  <FiCircle style={{ color: '#94a3b8' }} />
                                                                                                                                                                                                   )}
                                                                                                                                                                                    </div>

                                                                                                                                                                                    {/* Stage content */}
                                                                                                                                                                                    <div style={{
                                                                                                                                                                                                   flex: 1,
                                                                                                                                                                                                   padding: '1rem',
                                                                                                                                                                                                   background: stage.completed ? '#f0fdf4' : '#f8fafc',
                                                                                                                                                                                                   borderRadius: '12px',
                                                                                                                                                                                                   border: `1px solid ${stage.completed ? '#bbf7d0' : '#e2e8f0'}`
                                                                                                                                                                                    }}>
                                                                                                                                                                                                   <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                                                                                                                                                                                                                  <h4 style={{ margin: 0, color: '#1e293b' }}>{stage.title || stage.name}</h4>
                                                                                                                                                                                                                  {stage.duration && (
                                                                                                                                                                                                                                 <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.875rem', color: '#64748b' }}>
                                                                                                                                                                                                                                                <FiClock /> {stage.duration}
                                                                                                                                                                                                                                 </span>
                                                                                                                                                                                                                  )}
                                                                                                                                                                                                   </div>
                                                                                                                                                                                                   <p style={{ color: '#64748b', fontSize: '0.875rem', marginBottom: '0.75rem' }}>
                                                                                                                                                                                                                  {stage.description}
                                                                                                                                                                                                   </p>

                                                                                                                                                                                                   {/* Resources */}
                                                                                                                                                                                                   {stage.resources && stage.resources.length > 0 && (
                                                                                                                                                                                                                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                                                                                                                                                                                                                                 {stage.resources.map((resource, rIdx) => (
                                                                                                                                                                                                                                                <a
                                                                                                                                                                                                                                                               key={rIdx}
                                                                                                                                                                                                                                                               href={resource.url}
                                                                                                                                                                                                                                                               target="_blank"
                                                                                                                                                                                                                                                               rel="noopener noreferrer"
                                                                                                                                                                                                                                                               style={{
                                                                                                                                                                                                                                                                              display: 'flex',
                                                                                                                                                                                                                                                                              alignItems: 'center',
                                                                                                                                                                                                                                                                              gap: '0.375rem',
                                                                                                                                                                                                                                                                              padding: '0.375rem 0.75rem',
                                                                                                                                                                                                                                                                              background: '#eff6ff',
                                                                                                                                                                                                                                                                              color: '#3b82f6',
                                                                                                                                                                                                                                                                              borderRadius: '6px',
                                                                                                                                                                                                                                                                              fontSize: '0.875rem',
                                                                                                                                                                                                                                                                              textDecoration: 'none'
                                                                                                                                                                                                                                                               }}
                                                                                                                                                                                                                                                >
                                                                                                                                                                                                                                                               <FiExternalLink size={14} />
                                                                                                                                                                                                                                                               {resource.title || resource.name || 'Resource'}
                                                                                                                                                                                                                                                </a>
                                                                                                                                                                                                                                 ))}
                                                                                                                                                                                                                  </div>
                                                                                                                                                                                                   )}

                                                                                                                                                                                                   {!stage.completed && (
                                                                                                                                                                                                                  <button
                                                                                                                                                                                                                                 onClick={() => handleCompleteStage(idx)}
                                                                                                                                                                                                                                 className="edit-button"
                                                                                                                                                                                                                                 style={{ marginTop: '1rem', marginBottom: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                                                                                                                                                                                                                  >
                                                                                                                                                                                                                                 <FiAward />
                                                                                                                                                                                                                                 Mark Complete
                                                                                                                                                                                                                  </button>
                                                                                                                                                                                                   )}
                                                                                                                                                                                    </div>
                                                                                                                                                                     </div>
                                                                                                                                                      ))}
                                                                                                                                       </div>
                                                                                                                        </>
                                                                                                         )}
                                                                                          </div>
                                                                           </div>
                                                            </div>
                                             </div>
                              </div>
               );
};

export default LearningPath;
