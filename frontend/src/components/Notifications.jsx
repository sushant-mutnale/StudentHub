import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { notificationService } from '../services/notificationService';
import SidebarLeft from './SidebarLeft';
import { FiBell, FiAward, FiBriefcase, FiUsers, FiCalendar, FiMessageSquare, FiCheckCircle } from 'react-icons/fi';
import '../App.css';

const Notifications = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      navigate('/');
      return;
    }
    loadNotifications();
  }, [user, navigate]);

  const loadNotifications = async () => {
    setLoading(true);
    try {
      const data = await notificationService.getNotifications();
      setNotifications(data);
    } catch (err) {
      console.error('Error loading notifications:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkAsRead = async (id) => {
    try {
      await notificationService.markAsRead(id);
      setNotifications(notifications.map(n => n.id === id ? { ...n, is_read: true } : n));
    } catch (err) {
      console.error('Error marking as read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationService.markAllAsRead();
      setNotifications(notifications.map(n => ({ ...n, is_read: true })));
    } catch (err) {
      console.error('Error marking all as read:', err);
    }
  };

  const getNotificationIcon = (kind) => {
    switch (kind) {
      case 'interview_proposed':
      case 'interview_scheduled':
      case 'interview_rescheduled':
        return FiCalendar;
      case 'offer_sent':
      case 'offer_accepted':
      case 'offer_updated':
        return FiBriefcase;
      case 'message':
        return FiMessageSquare;
      default:
        return FiBell;
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high': return '#e74c3c';
      case 'medium': return '#3498db';
      default: return '#95a5a6';
    }
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);

    if (diffInSeconds < 60) return 'Just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    return date.toLocaleDateString();
  };

  if (!user) return null;

  return (
    <div className="dashboard-container">
      <SidebarLeft />
      <div className="dashboard-main">
        <div className="dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1 className="dashboard-title">Notifications</h1>
          {notifications.some(n => !n.is_read) && (
            <button onClick={handleMarkAllRead} className="edit-button" style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem', margin: 0 }}>
              Mark all as read
            </button>
          )}
        </div>
        <div className="dashboard-content">
          <div className="notifications-container">
            {loading ? (
              <div className="empty-state">Loading your feed...</div>
            ) : notifications.length === 0 ? (
              <div className="empty-state">No notifications yet. You are all caught up!</div>
            ) : (
              notifications.map((notification) => {
                const Icon = getNotificationIcon(notification.kind);
                return (
                  <div
                    key={notification.id}
                    className={`notification-item ${notification.is_read ? 'read' : 'unread'}`}
                    style={{
                      position: 'relative',
                      borderLeft: `4px solid ${notification.is_read ? 'transparent' : getPriorityColor(notification.priority)}`,
                      opacity: notification.is_read ? 0.7 : 1,
                      transition: 'all 0.3s ease'
                    }}
                  >
                    <div className="notification-icon" style={{ backgroundColor: notification.is_read ? '#f8f9fa' : 'rgba(52, 152, 219, 0.1)' }}>
                      <Icon style={{ color: notification.is_read ? '#95a5a6' : '#3498db' }} />
                    </div>
                    <div className="notification-content" style={{ flex: 1 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                        <div className="notification-title" style={{ fontWeight: notification.is_read ? '500' : '700' }}>
                          {notification.kind.replace(/_/g, ' ').toUpperCase()}
                        </div>
                        {!notification.is_read && (
                          <button
                            onClick={() => handleMarkAsRead(notification.id)}
                            style={{ border: 'none', background: 'none', color: '#2ecc71', cursor: 'pointer', fontSize: '1.2rem' }}
                            title="Mark as read"
                          >
                            <FiCheckCircle />
                          </button>
                        )}
                      </div>
                      <div className="notification-message">
                        {notification.kind === 'interview_proposed' ? 'New interview proposal received.' :
                          notification.kind === 'offer_sent' ? 'Congratulations! You received a new job offer.' :
                            'System update regarding your account activity.'}
                      </div>
                      <div className="notification-time">
                        {formatTimestamp(notification.created_at)} • <span style={{ textTransform: 'capitalize' }}>{notification.category}</span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Notifications;


