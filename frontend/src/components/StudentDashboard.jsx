import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import SidebarLeft from './SidebarLeft';
import SidebarRight from './SidebarRight';
import PostBox from './PostBox';
import PostFeed from './PostFeed';
import FloatingActionButton from './FloatingActionButton';
import { FiHome, FiGrid } from 'react-icons/fi';
import '../App.css';

const StudentDashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [isComposeOpen, setIsComposeOpen] = useState(false);

  useEffect(() => {
    if (!user || user.role !== 'student') {
      navigate('/');
      return;
    }
  }, [user, navigate]);

  const handlePostCreated = () => {
    setRefreshTrigger((prev) => prev + 1);
    setIsComposeOpen(false); // Close modal on success
  };

  if (!user || user.role !== 'student') {
    return null;
  }

  return (
    <div className="dashboard-container" style={{ background: 'var(--color-bg)' }}>
      <SidebarLeft />

      <div className="dashboard-main custom-scrollbar">
        <div className="dashboard-header glass-panel" style={{
          position: 'sticky',
          top: 0,
          zIndex: 10,
          marginBottom: '1.5rem',
          borderRadius: '0 0 var(--radius-lg) var(--radius-lg)',
          borderBottom: '1px solid rgba(255,255,255,0.5)',
          background: 'rgba(255, 255, 255, 0.8)'
        }}>
          <h1 className="dashboard-title" style={{
            background: 'var(--gradient-primary)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            fontSize: '1.5rem'
          }}>
            <FiHome size={24} style={{ color: '#667eea' }} />
            Home Feed
          </h1>
        </div>

        <div className="dashboard-content" style={{ maxWidth: '800px', margin: '0 auto' }}>

          <div className={`compose-section ${isComposeOpen ? 'mobile-open' : ''} animate-fade-in-up delay-100`}>
            <div className="compose-header-mobile">
              <h3 style={{ margin: 0 }}>Create Post</h3>
              <button onClick={() => setIsComposeOpen(false)} className="btn-icon">×</button>
            </div>
            <h3 className="compose-title-desktop" style={{
              marginBottom: '1rem',
              color: 'var(--color-text)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '1.2rem'
            }}>
              Community Updates
            </h3>
            <PostBox onPostCreated={handlePostCreated} />
          </div>

          <div className="animate-fade-in-up delay-100">
            <PostFeed refreshTrigger={refreshTrigger} />
          </div>
        </div>
      </div>

      <SidebarRight />

      <FloatingActionButton
        onClick={() => setIsComposeOpen(!isComposeOpen)}
        isOpen={isComposeOpen}
      />
    </div>
  );
};

export default StudentDashboard;
