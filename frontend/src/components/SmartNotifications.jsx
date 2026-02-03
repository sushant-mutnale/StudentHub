import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { smartNotificationService } from '../services/smartNotificationService';
import SidebarLeft from './SidebarLeft';
import { FiBell, FiBriefcase, FiClock, FiBook, FiUsers, FiAward, FiCheckCircle, FiSettings, FiX, FiChevronRight, FiFilter } from 'react-icons/fi';
import '../App.css';

const SmartNotifications = () => {
               const navigate = useNavigate();
               const { user } = useAuth();
               const [notifications, setNotifications] = useState([]);
               const [stats, setStats] = useState(null);
               const [loading, setLoading] = useState(true);
               const [filter, setFilter] = useState('all');
               const [showSettings, setShowSettings] = useState(false);
               const [settings, setSettings] = useState(null);

               useEffect(() => {
                              if (!user) {
                                             navigate('/');
                                             return;
                              }
                              loadNotifications();
                              loadStats();
               }, [user, navigate, filter]);

               const loadNotifications = async () => {
                              try {
                                             const type = filter === 'all' ? null : filter;
                                             const data = await smartNotificationService.getNotifications(false, 30, type);
                                             setNotifications(data.notifications || data || []);
                              } catch (err) {
                                             console.error('Failed to load notifications:', err);
                              } finally {
                                             setLoading(false);
                              }
               };

               const loadStats = async () => {
                              try {
                                             const data = await smartNotificationService.getStats();
                                             setStats(data.stats || data);
                              } catch (err) {
                                             console.error('Failed to load stats:', err);
                              }
               };

               const loadSettings = async () => {
                              try {
                                             const data = await smartNotificationService.getSettings();
                                             setSettings(data.settings || data);
                                             setShowSettings(true);
                              } catch (err) {
                                             console.error('Failed to load settings:', err);
                              }
               };

               const handleMarkAsRead = async (id) => {
                              try {
                                             await smartNotificationService.markAsRead(id);
                                             setNotifications(notifications.map(n =>
                                                            (n._id || n.id) === id ? { ...n, read: true, is_read: true } : n
                                             ));
                              } catch (err) {
                                             console.error('Failed to mark as read:', err);
                              }
               };

               const handleMarkAllRead = async () => {
                              try {
                                             await smartNotificationService.markAllAsRead();
                                             setNotifications(notifications.map(n => ({ ...n, read: true, is_read: true })));
                              } catch (err) {
                                             console.error('Failed to mark all as read:', err);
                              }
               };

               const handleClick = async (notification) => {
                              try {
                                             await smartNotificationService.clickNotification(notification._id || notification.id);

                                             // Navigate based on type
                                             if (notification.action_url) {
                                                            navigate(notification.action_url);
                                             } else if (notification.type === 'opportunity_match') {
                                                            navigate('/opportunities');
                                             } else if (notification.type === 'learning_reminder') {
                                                            navigate('/learning');
                                             } else if (notification.type === 'deadline_reminder') {
                                                            navigate('/opportunities');
                                             }
                              } catch (err) {
                                             console.error('Failed to record click:', err);
                              }
               };

               const handleDismiss = async (id, e) => {
                              e.stopPropagation();
                              try {
                                             await smartNotificationService.dismissNotification(id);
                                             setNotifications(notifications.filter(n => (n._id || n.id) !== id));
                              } catch (err) {
                                             console.error('Failed to dismiss:', err);
                              }
               };

               const getIcon = (type) => {
                              switch (type) {
                                             case 'opportunity_match': return FiBriefcase;
                                             case 'deadline_reminder': return FiClock;
                                             case 'learning_reminder': return FiBook;
                                             case 'recruiter_activity': return FiUsers;
                                             case 'achievement': return FiAward;
                                             default: return FiBell;
                              }
               };

               const getPriorityStyle = (priority) => {
                              switch (priority) {
                                             case 'urgent': return { bg: '#fef2f2', border: '#fecaca', dot: '#dc2626' };
                                             case 'high': return { bg: '#fff7ed', border: '#fed7aa', dot: '#ea580c' };
                                             case 'medium': return { bg: '#eff6ff', border: '#bfdbfe', dot: '#3b82f6' };
                                             default: return { bg: '#f8fafc', border: '#e2e8f0', dot: '#94a3b8' };
                              }
               };

               const filterOptions = [
                              { value: 'all', label: 'All' },
                              { value: 'opportunity_match', label: 'Job Matches' },
                              { value: 'deadline_reminder', label: 'Deadlines' },
                              { value: 'learning_reminder', label: 'Learning' },
                              { value: 'achievement', label: 'Achievements' },
               ];

               if (!user) return null;

               const unreadCount = notifications.filter(n => !n.read && !n.is_read).length;

               return (
                              <div className="dashboard-container">
                                             <SidebarLeft />
                                             <div className="dashboard-main">
                                                            <div className="dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                                           <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                                                                          <h1 className="dashboard-title">Smart Notifications</h1>
                                                                                          {unreadCount > 0 && (
                                                                                                         <span style={{
                                                                                                                        padding: '0.25rem 0.75rem',
                                                                                                                        background: '#ef4444',
                                                                                                                        color: 'white',
                                                                                                                        borderRadius: '9999px',
                                                                                                                        fontSize: '0.875rem',
                                                                                                                        fontWeight: 600
                                                                                                         }}>
                                                                                                                        {unreadCount} new
                                                                                                         </span>
                                                                                          )}
                                                                           </div>
                                                                           <div style={{ display: 'flex', gap: '0.5rem' }}>
                                                                                          {unreadCount > 0 && (
                                                                                                         <button onClick={handleMarkAllRead} className="edit-button" style={{ margin: 0 }}>
                                                                                                                        <FiCheckCircle style={{ marginRight: '0.375rem' }} />
                                                                                                                        Mark all read
                                                                                                         </button>
                                                                                          )}
                                                                                          <button onClick={loadSettings} className="edit-button" style={{ margin: 0 }}>
                                                                                                         <FiSettings />
                                                                                          </button>
                                                                           </div>
                                                            </div>

                                                            <div className="dashboard-content">
                                                                           {/* Stats */}
                                                                           {stats && (
                                                                                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
                                                                                                         <div className="card" style={{ padding: '1rem', textAlign: 'center' }}>
                                                                                                                        <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#3b82f6' }}>{stats.total || 0}</div>
                                                                                                                        <div style={{ fontSize: '0.875rem', color: '#64748b' }}>Total</div>
                                                                                                         </div>
                                                                                                         <div className="card" style={{ padding: '1rem', textAlign: 'center' }}>
                                                                                                                        <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#10b981' }}>{stats.read || 0}</div>
                                                                                                                        <div style={{ fontSize: '0.875rem', color: '#64748b' }}>Read</div>
                                                                                                         </div>
                                                                                                         <div className="card" style={{ padding: '1rem', textAlign: 'center' }}>
                                                                                                                        <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#f59e0b' }}>{stats.clicked || 0}</div>
                                                                                                                        <div style={{ fontSize: '0.875rem', color: '#64748b' }}>Clicked</div>
                                                                                                         </div>
                                                                                          </div>
                                                                           )}

                                                                           {/* Filter */}
                                                                           <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
                                                                                          {filterOptions.map(opt => (
                                                                                                         <button
                                                                                                                        key={opt.value}
                                                                                                                        onClick={() => setFilter(opt.value)}
                                                                                                                        style={{
                                                                                                                                       padding: '0.5rem 1rem',
                                                                                                                                       border: 'none',
                                                                                                                                       background: filter === opt.value ? 'linear-gradient(135deg, #3b82f6, #8b5cf6)' : '#f1f5f9',
                                                                                                                                       color: filter === opt.value ? 'white' : '#64748b',
                                                                                                                                       borderRadius: '8px',
                                                                                                                                       cursor: 'pointer',
                                                                                                                                       fontSize: '0.875rem',
                                                                                                                                       fontWeight: filter === opt.value ? 600 : 400
                                                                                                                        }}
                                                                                                         >
                                                                                                                        {opt.label}
                                                                                                         </button>
                                                                                          ))}
                                                                           </div>

                                                                           {/* Notifications List */}
                                                                           {loading ? (
                                                                                          <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
                                                                                                         <div className="loading-spinner" style={{ margin: '0 auto 1rem' }} />
                                                                                                         <p style={{ color: '#64748b' }}>Loading notifications...</p>
                                                                                          </div>
                                                                           ) : notifications.length === 0 ? (
                                                                                          <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
                                                                                                         <FiBell size={48} style={{ color: '#94a3b8', marginBottom: '1rem' }} />
                                                                                                         <p style={{ color: '#64748b' }}>No notifications yet. Check back later!</p>
                                                                                          </div>
                                                                           ) : (
                                                                                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                                                                                         {notifications.map((notif, idx) => {
                                                                                                                        const Icon = getIcon(notif.type);
                                                                                                                        const priority = getPriorityStyle(notif.priority);
                                                                                                                        const isUnread = !notif.read && !notif.is_read;

                                                                                                                        return (
                                                                                                                                       <div
                                                                                                                                                      key={notif._id || notif.id || idx}
                                                                                                                                                      onClick={() => handleClick(notif)}
                                                                                                                                                      style={{
                                                                                                                                                                     padding: '1rem',
                                                                                                                                                                     background: isUnread ? priority.bg : '#f8fafc',
                                                                                                                                                                     border: `1px solid ${isUnread ? priority.border : '#e2e8f0'}`,
                                                                                                                                                                     borderRadius: '12px',
                                                                                                                                                                     cursor: 'pointer',
                                                                                                                                                                     display: 'flex',
                                                                                                                                                                     alignItems: 'center',
                                                                                                                                                                     gap: '1rem',
                                                                                                                                                                     opacity: isUnread ? 1 : 0.7,
                                                                                                                                                                     transition: 'all 0.2s'
                                                                                                                                                      }}
                                                                                                                                       >
                                                                                                                                                      {/* Unread dot */}
                                                                                                                                                      {isUnread && (
                                                                                                                                                                     <div style={{
                                                                                                                                                                                    width: '8px',
                                                                                                                                                                                    height: '8px',
                                                                                                                                                                                    background: priority.dot,
                                                                                                                                                                                    borderRadius: '50%',
                                                                                                                                                                                    flexShrink: 0
                                                                                                                                                                     }} />
                                                                                                                                                      )}

                                                                                                                                                      {/* Icon */}
                                                                                                                                                      <div style={{
                                                                                                                                                                     width: '40px',
                                                                                                                                                                     height: '40px',
                                                                                                                                                                     background: isUnread ? 'white' : '#f1f5f9',
                                                                                                                                                                     borderRadius: '10px',
                                                                                                                                                                     display: 'flex',
                                                                                                                                                                     alignItems: 'center',
                                                                                                                                                                     justifyContent: 'center',
                                                                                                                                                                     flexShrink: 0
                                                                                                                                                      }}>
                                                                                                                                                                     <Icon style={{ color: isUnread ? priority.dot : '#94a3b8' }} />
                                                                                                                                                      </div>

                                                                                                                                                      {/* Content */}
                                                                                                                                                      <div style={{ flex: 1, minWidth: 0 }}>
                                                                                                                                                                     <div style={{ fontWeight: isUnread ? 600 : 400, color: '#1e293b', marginBottom: '0.25rem' }}>
                                                                                                                                                                                    {notif.title}
                                                                                                                                                                     </div>
                                                                                                                                                                     <div style={{ fontSize: '0.875rem', color: '#64748b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                                                                                                                                                                    {notif.message}
                                                                                                                                                                     </div>
                                                                                                                                                                     <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.25rem' }}>
                                                                                                                                                                                    {notif.created_at && new Date(notif.created_at).toLocaleString()}
                                                                                                                                                                     </div>
                                                                                                                                                      </div>

                                                                                                                                                      {/* Actions */}
                                                                                                                                                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                                                                                                                     {isUnread && (
                                                                                                                                                                                    <button
                                                                                                                                                                                                   onClick={(e) => { e.stopPropagation(); handleMarkAsRead(notif._id || notif.id); }}
                                                                                                                                                                                                   style={{ padding: '0.375rem', border: 'none', background: 'transparent', cursor: 'pointer', color: '#10b981' }}
                                                                                                                                                                                                   title="Mark as read"
                                                                                                                                                                                    >
                                                                                                                                                                                                   <FiCheckCircle />
                                                                                                                                                                                    </button>
                                                                                                                                                                     )}
                                                                                                                                                                     <button
                                                                                                                                                                                    onClick={(e) => handleDismiss(notif._id || notif.id, e)}
                                                                                                                                                                                    style={{ padding: '0.375rem', border: 'none', background: 'transparent', cursor: 'pointer', color: '#94a3b8' }}
                                                                                                                                                                                    title="Dismiss"
                                                                                                                                                                     >
                                                                                                                                                                                    <FiX />
                                                                                                                                                                     </button>
                                                                                                                                                                     <FiChevronRight style={{ color: '#94a3b8' }} />
                                                                                                                                                      </div>
                                                                                                                                       </div>
                                                                                                                        );
                                                                                                         })}
                                                                                          </div>
                                                                           )}
                                                            </div>
                                             </div>

                                             {/* Settings Modal */}
                                             {showSettings && settings && (
                                                            <div style={{
                                                                           position: 'fixed',
                                                                           inset: 0,
                                                                           background: 'rgba(0,0,0,0.5)',
                                                                           display: 'flex',
                                                                           alignItems: 'center',
                                                                           justifyContent: 'center',
                                                                           zIndex: 1000
                                                            }}>
                                                                           <div style={{
                                                                                          background: 'white',
                                                                                          borderRadius: '16px',
                                                                                          padding: '1.5rem',
                                                                                          maxWidth: '500px',
                                                                                          width: '90%',
                                                                                          maxHeight: '80vh',
                                                                                          overflow: 'auto'
                                                                           }}>
                                                                                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                                                                                                         <h3 style={{ margin: 0 }}>Notification Settings</h3>
                                                                                                         <button onClick={() => setShowSettings(false)} style={{ border: 'none', background: 'none', cursor: 'pointer' }}>
                                                                                                                        <FiX size={24} />
                                                                                                         </button>
                                                                                          </div>

                                                                                          {Object.entries(settings).map(([key, value]) => (
                                                                                                         <div key={key} style={{ marginBottom: '1rem', padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
                                                                                                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                                                                                                       <span style={{ fontWeight: 500, textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</span>
                                                                                                                                       <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                                                                                                                                                      <input
                                                                                                                                                                     type="checkbox"
                                                                                                                                                                     checked={value?.enabled !== false}
                                                                                                                                                                     onChange={() => { }}
                                                                                                                                                                     style={{ width: '18px', height: '18px' }}
                                                                                                                                                      />
                                                                                                                                       </label>
                                                                                                                        </div>
                                                                                                         </div>
                                                                                          ))}

                                                                                          <button onClick={() => setShowSettings(false)} className="form-button" style={{ width: '100%' }}>
                                                                                                         Save Settings
                                                                                          </button>
                                                                           </div>
                                                            </div>
                                             )}
                              </div>
               );
};

export default SmartNotifications;
