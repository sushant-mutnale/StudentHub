import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { FiMapPin, FiTrash2, FiUsers, FiLogOut, FiPlus, FiMessageSquare, FiCalendar } from 'react-icons/fi';
import { useAuth } from '../contexts/AuthContext';
import { jobService } from '../services/jobService';
import InterviewModal from './interviews/InterviewModal';
import '../App.css';

const RecruiterDashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [jobs, setJobs] = useState([]);
  const [matches, setMatches] = useState({});
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [message, setMessage] = useState('');
  const [showInterviewModal, setShowInterviewModal] = useState(false);
  const [activeCandidate, setActiveCandidate] = useState(null);
  const [activeJobId, setActiveJobId] = useState(null);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    requiredSkills: '',
    location: '',
  });

  useEffect(() => {
    if (!user || user.role !== 'recruiter') {
      navigate('/');
      return;
    }
    loadJobs();
  }, [user, navigate]);

  const loadJobs = async () => {
    setLoadingJobs(true);
    try {
      const data = await jobService.getMyJobs();
      setJobs(data);
    } catch (err) {
      setMessage(err.message || 'Failed to load jobs');
    } finally {
      setLoadingJobs(false);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const skillsArray = formData.requiredSkills
        .split(',')
        .map((skill) => skill.trim())
        .filter((skill) => skill.length > 0);
      await jobService.createJob({
        title: formData.title,
        description: formData.description,
        skills_required: skillsArray,
        location: formData.location,
      });
      setFormData({
        title: '',
        description: '',
        requiredSkills: '',
        location: '',
      });
      setMessage('Job posted successfully');
      loadJobs();
    } catch (err) {
      setMessage(err.message || 'Error posting job');
    }
  };

  const handleDeleteJob = async (jobId) => {
    if (!window.confirm('Delete this job posting?')) return;
    try {
      await jobService.deleteJob(jobId);
      setMatches((prev) => {
        const copy = { ...prev };
        delete copy[jobId];
        return copy;
      });
      loadJobs();
    } catch (err) {
      setMessage(err.message || 'Failed to delete job');
    }
  };

  const fetchMatches = async (jobId) => {
    setMatches((prev) => ({
      ...prev,
      [jobId]: { ...(prev[jobId] || {}), loading: true },
    }));
    try {
      const data = await jobService.getJobMatches(jobId);
      setMatches((prev) => ({
        ...prev,
        [jobId]: { loading: false, data },
      }));
    } catch (err) {
      setMatches((prev) => ({
        ...prev,
        [jobId]: { loading: false, error: err.message || 'Failed to load matches' },
      }));
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const openInterviewModal = (student, jobId) => {
    setActiveCandidate(student);
    setActiveJobId(jobId);
    setShowInterviewModal(true);
  };

  const handleInterviewCreated = () => {
    setShowInterviewModal(false);
    setActiveCandidate(null);
    setMessage('Interview proposal sent!');
  };

  if (!user || user.role !== 'recruiter') {
    return null;
  }

  return (
    <div className="dashboard-container recruiter-only">
      <div className="sidebar-left" style={{ width: '220px' }}>
        <div className="sidebar-logo">Student Hub</div>
        <nav className="sidebar-nav">
          <div className="nav-item active">
            <FiUsers />
            <span>Matches</span>
          </div>
          <div className="nav-item" onClick={() => navigate('/messages')}>
            <FiMessageSquare />
            <span>Messages</span>
          </div>
          <div className="nav-item" onClick={() => navigate('/interviews')}>
            <FiCalendar />
            <span>Interviews</span>
          </div>
          <div className="nav-item logout" onClick={handleLogout}>
            <FiLogOut />
            <span>Logout</span>
          </div>
        </nav>
      </div>
      <div className="dashboard-main">
        <div className="dashboard-header">
          <h1 className="dashboard-title">Recruiter Workspace</h1>
        </div>
        <div className="dashboard-content">
          {message && (
            <div
              className={
                message.toLowerCase().includes('success')
                  ? 'success-message'
                  : 'error-message'
              }
              style={{ marginBottom: '1rem' }}
            >
              {message}
            </div>
          )}
          <div className="job-form">
            <div className="job-form-header">
              <FiPlus />
              <h2>Post a New Job</h2>
            </div>
            <form className="auth-form" onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label">Job Title *</label>
                <input
                  type="text"
                  name="title"
                  className="form-input"
                  value={formData.title}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Description *</label>
                <textarea
                  name="description"
                  className="form-textarea"
                  value={formData.description}
                  onChange={handleChange}
                  rows="4"
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Required Skills *</label>
                <input
                  type="text"
                  name="requiredSkills"
                  className="form-input"
                  value={formData.requiredSkills}
                  onChange={handleChange}
                  placeholder="React, Node, MongoDB"
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Location *</label>
                <input
                  type="text"
                  name="location"
                  className="form-input"
                  value={formData.location}
                  onChange={handleChange}
                  placeholder="Remote / City, Country"
                  required
                />
              </div>

              <button type="submit" className="form-button">
                Publish Job
              </button>
            </form>
          </div>

          <div className="jobs-section">
            <div className="jobs-section-header">
              <h2>My Jobs</h2>
              <span>{jobs.length} active</span>
            </div>

            {loadingJobs ? (
              <div className="empty-state">Loading your jobs...</div>
            ) : jobs.length === 0 ? (
              <div className="empty-state">
                No jobs yet. Start by posting a role to see matching students.
              </div>
            ) : (
              jobs.map((job) => (
                <div key={job.id} className="job-item">
                  <div className="job-header">
                    <div>
                      <div className="job-title">{job.title}</div>
                      <div className="job-company">{job.company_name || user.companyName}</div>
                    </div>
                    <button
                      className="delete-button"
                      type="button"
                      onClick={() => handleDeleteJob(job.id)}
                    >
                      <FiTrash2 /> Delete
                    </button>
                  </div>
                  <div className="job-description">{job.description}</div>
                  <div className="job-details">
                    <div className="job-detail">
                      <FiMapPin />
                      <span>{job.location}</span>
                    </div>
                  </div>
                  <div className="job-skills">
                    {job.skills_required.map((skill) => (
                      <span key={skill} className="skill-tag">
                        {skill}
                      </span>
                    ))}
                  </div>
                  <button
                    className="form-button"
                    type="button"
                    onClick={() => fetchMatches(job.id)}
                    style={{ width: 'fit-content', marginTop: '1rem' }}
                  >
                    View Matching Students
                  </button>

                  {matches[job.id]?.loading && (
                    <div className="matches-list">Loading matches...</div>
                  )}
                  {matches[job.id]?.error && (
                    <div className="error-message" style={{ marginTop: '0.5rem' }}>
                      {matches[job.id].error}
                    </div>
                  )}
                  {matches[job.id]?.data && matches[job.id].data.length === 0 && (
                    <div className="matches-list empty-state">
                      No matching students yet. Try broadening the skill set.
                    </div>
                  )}
                  {matches[job.id]?.data && matches[job.id].data.length > 0 && (
                    <div className="matches-list">
                      {matches[job.id].data.map((student) => (
                        <div key={student.id} className="match-item">
                          <div>
                            <strong>{student.full_name}</strong>
                            <div className="match-username">@{student.username}</div>
                            <div className="match-skills">
                              {student.skills.map((skill) => (
                                <span key={skill} className="skill-tag">
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </div>
                          <div className="match-actions">
                            <button
                              type="button"
                              className="form-button"
                              aria-label={`Propose interview to ${student.full_name}`}
                              onClick={() => openInterviewModal(student, job.id)}
                            >
                              Propose Interview
                            </button>
                            <Link to={`/profile/${student.id}`} className="form-button outline">
                              View Profile
                            </Link>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
      {showInterviewModal && (
        <InterviewModal
          isOpen
          onClose={() => setShowInterviewModal(false)}
          candidateId={activeCandidate?.id}
          initialCandidate={activeCandidate}
          jobId={activeJobId}
          onCreated={handleInterviewCreated}
        />
      )}
    </div>
  );
};

export default RecruiterDashboard;
