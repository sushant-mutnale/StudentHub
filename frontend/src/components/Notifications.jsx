import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import SidebarLeft from './SidebarLeft';
import { FiBell, FiAward, FiBriefcase, FiUsers } from 'react-icons/fi';
import '../App.css';

const Notifications = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [notifications] = useState([
    {
      id: 1,
      type: 'contest',
      title: 'New Contest Available',
      message: 'Weekly Coding Challenge is now open. Join now!',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      icon: FiAward,
    },
    {
      id: 2,
      type: 'job',
      title: 'Job Match Found',
      message: 'A new job posting matches your skills: Frontend Developer at Tech Corp',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      icon: FiBriefcase,
    },
    {
      id: 3,
      type: 'update',
      title: 'Profile Update',
      message: 'Your profile has been viewed by 5 recruiters this week',
      timestamp: new Date(Date.now() - 86400000).toISOString(),
      icon: FiUsers,
    },
    {
      id: 4,
      type: 'contest',
      title: 'Contest Results',
      message: 'Results for Data Science Competition are out. Check your ranking!',
      timestamp: new Date(Date.now() - 172800000).toISOString(),
      icon: FiAward,
    },
  ]);

  useEffect(() => {
    if (!user || user.role !== 'student') {
      navigate('/');
    }
  }, [user, navigate]);

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);

    if (diffInSeconds < 60) {
      return 'Just now';
    } else if (diffInSeconds < 3600) {
      const minutes = Math.floor(diffInSeconds / 60);
      return `${minutes} minutes ago`;
    } else if (diffInSeconds < 86400) {
      const hours = Math.floor(diffInSeconds / 3600);
      return `${hours} hours ago`;
    } else {
      const days = Math.floor(diffInSeconds / 86400);
      return `${days} days ago`;
    }
  };

  if (!user || user.role !== 'student') {
    return null;
  }

  return (
    <div className="dashboard-container">
      <SidebarLeft />
      <div className="dashboard-main">
        <div className="dashboard-header">
          <h1 className="dashboard-title">Notifications</h1>
        </div>
        <div className="dashboard-content">
          <div className="notifications-container">
            {notifications.length === 0 ? (
              <div
                style={{
                  textAlign: 'center',
                  padding: '2rem',
                  color: '#666',
                }}
              >
                No notifications yet.
              </div>
            ) : (
              notifications.map((notification) => {
                const Icon = notification.icon;
                return (
                  <div key={notification.id} className="notification-item">
                    <div className="notification-icon">
                      <Icon />
                    </div>
                    <div className="notification-content">
                      <div className="notification-title">
                        {notification.title}
                      </div>
                      <div className="notification-message">
                        {notification.message}
                      </div>
                      <div className="notification-time">
                        {formatTimestamp(notification.timestamp)}
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


