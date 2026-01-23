import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import SidebarLeft from './SidebarLeft';
import SidebarRight from './SidebarRight';
import PostBox from './PostBox';
import PostFeed from './PostFeed';
import JobFeed from './JobFeed';
import '../App.css';

const StudentDashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  useEffect(() => {
    if (!user || user.role !== 'student') {
      navigate('/');
      return;
    }
  }, [user, navigate]);

  const handlePostCreated = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  if (!user || user.role !== 'student') {
    return null;
  }

  return (
    <div className="dashboard-container">
      <SidebarLeft />
      <div className="dashboard-main">
        <div className="dashboard-header">
          <h1 className="dashboard-title">Home</h1>
        </div>
        <div className="dashboard-content">
          <PostBox onPostCreated={handlePostCreated} />
          <PostFeed refreshTrigger={refreshTrigger} />
          {/* Jobs appear below the social feed to keep the original UX focused on posts */}
          <JobFeed refreshTrigger={refreshTrigger} />
        </div>
      </div>
      <SidebarRight />
    </div>
  );
};

export default StudentDashboard;

