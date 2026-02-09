import { useEffect, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { jobService } from '../services/jobService';
import '../App.css';

const JobDetail = () => {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [applyMessage, setApplyMessage] = useState('');
  const [applyResumeUrl, setApplyResumeUrl] = useState('');
  const [applyLoading, setApplyLoading] = useState(false);
  const [applySuccess, setApplySuccess] = useState('');

  const [applications, setApplications] = useState([]);
  const [appsLoading, setAppsLoading] = useState(false);
  const [appsError, setAppsError] = useState('');

  useEffect(() => {
    if (!user) {
      navigate('/');
      return;
    }
    loadJob();
    if (user.role === 'recruiter') {
      loadApplications();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, jobId]);

  const loadJob = async () => {
    setLoading(true);
    try {
      const data = await jobService.getJob(jobId);
      setJob(data);
      setError('');
    } catch (err) {
      setError(err.message || 'Unable to load job');
    } finally {
      setLoading(false);
    }
  };

  const loadApplications = async () => {
    if (!user || user.role !== 'recruiter') return;
    setAppsLoading(true);
    try {
      const data = await jobService.getJobApplications(jobId);
      setApplications(data);
      setAppsError('');
    } catch (err) {
      setAppsError(err.message || 'Unable to load applications');
    } finally {
      setAppsLoading(false);
    }
  };

  const handleApply = async (e) => {
    e.preventDefault();
    if (!applyMessage.trim()) return;
    setApplyLoading(true);
    setApplySuccess('');
    setError('');
    try {
      await jobService.applyToJob(jobId, {
        message: applyMessage,
        resume_url: applyResumeUrl || undefined,
      });
      setApplyMessage('');
      setApplyResumeUrl('');
      setApplySuccess('Application submitted successfully.');
    } catch (err) {
      setError(err.message || 'Failed to submit application');
    } finally {
      setApplyLoading(false);
    }
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  if (loading) {
    return (
      <div className="dashboard-container">
        <div className="dashboard-main">
          <div style={{ padding: '2rem', textAlign: 'center' }}>Loading job...</div>
        </div>
      </div>
    );
  }

  if (error && !job) {
    return (
      <div className="dashboard-container">
        <div className="dashboard-main">
          <div className="error-message" style={{ margin: '2rem auto', maxWidth: 600 }}>
            {error}
          </div>
        </div>
      </div>
    );
  }

  if (!job) {
    return null;
  }

  const isStudent = user?.role === 'student';
  const isRecruiter = user?.role === 'recruiter';

  return (
    <div className="dashboard-container">
      <div className="dashboard-main">
        <div className="dashboard-header">
          <h1 className="dashboard-title">{job.title}</h1>
        </div>
        <div className="dashboard-content">
          <div className="job-item" style={{ maxWidth: 800, margin: '0 auto' }}>
            <div className="job-header">
              <div>
                <div className="job-company">
                  {job.company_name ? (
                    <Link to={`/profile/${job.recruiter_id}`} className="post-author-link">
                      {job.company_name}
                    </Link>
                  ) : (
                    <Link to={`/profile/${job.recruiter_id}`} className="post-author-link">
                      View recruiter
                    </Link>
                  )}
                </div>
                <div className="job-detail">
                  <span>{job.location}</span>
                </div>
              </div>
              <div className="job-timestamp">{formatTimestamp(job.created_at)}</div>
            </div>

            <div className="job-description" style={{ marginTop: '1rem' }}>
              {job.description}
            </div>

            <div className="job-skills" style={{ marginTop: '0.75rem' }}>
              {job.skills_required?.map((skill) => (
                <span key={skill} className="skill-tag">
                  {skill}
                </span>
              ))}
            </div>
          </div>

          {isStudent && (
            <>
              <div className="job-item" style={{ maxWidth: 800, margin: '1.5rem auto 0', padding: '1.5rem', textAlign: 'center', backgroundColor: '#f0f9ff', borderColor: '#bae6fd', borderLeft: '4px solid #0284c7' }}>
                <h3 style={{ color: '#0f172a', marginBottom: '0.5rem', fontSize: '1.1rem' }}>🤖 Prepare for this Role</h3>
                <p style={{ marginBottom: '1rem', color: '#64748b', fontSize: '0.95rem' }}>Practice with our AI Interviewer tailored to this job description.</p>
                <Link
                  to={`/interviews/agent/${jobId}`}
                  className="form-button"
                  style={{ backgroundColor: '#0284c7', display: 'inline-block', width: 'auto', padding: '0.75rem 1.5rem', textDecoration: 'none' }}
                >
                  Start AI Interview
                </Link>
              </div>

              <div className="job-item" style={{ maxWidth: 800, margin: '1.5rem auto 0' }}>
                <h2 style={{ marginBottom: '0.75rem' }}>Apply to this job</h2>
                {applySuccess && (
                  <div className="success-message" style={{ marginBottom: '0.5rem' }}>
                    {applySuccess}
                  </div>
                )}
                {error && (
                  <div className="error-message" style={{ marginBottom: '0.5rem' }}>
                    {error}
                  </div>
                )}
                <form onSubmit={handleApply} className="auth-form">
                  <div className="form-group">
                    <label className="form-label">Message to recruiter *</label>
                    <textarea
                      className="form-textarea"
                      rows="4"
                      value={applyMessage}
                      onChange={(e) => setApplyMessage(e.target.value)}
                      placeholder="Briefly explain why you're a good fit for this role..."
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Resume URL (optional)</label>
                    <input
                      type="url"
                      className="form-input"
                      value={applyResumeUrl}
                      onChange={(e) => setApplyResumeUrl(e.target.value)}
                      placeholder="https://drive.google.com/your-resume"
                    />
                  </div>
                  <button
                    type="submit"
                    className="form-button"
                    disabled={applyLoading || !applyMessage.trim()}
                  >
                    {applyLoading ? 'Submitting...' : 'Submit Application'}
                  </button>
                </form>
              </div>
            </>
          )}

          {isRecruiter && (
            <div className="job-item" style={{ maxWidth: 800, margin: '1.5rem auto 0' }}>
              <div className="jobs-section-header">
                <h2>Applications</h2>
                <span>{applications.length}</span>
              </div>
              {appsLoading && (
                <div className="empty-state">Loading applications...</div>
              )}
              {appsError && (
                <div className="error-message" style={{ marginBottom: '0.5rem' }}>
                  {appsError}
                </div>
              )}
              {!appsLoading && applications.length === 0 && !appsError && (
                <div className="empty-state">
                  No applications yet.
                </div>
              )}
              {!appsLoading && applications.length > 0 && (
                <div className="matches-list">
                  {applications.map((app) => (
                    <div key={app.id} className="match-item">
                      <div>
                        <strong>{app.student_name || 'Student'}</strong>
                        <div className="match-username">
                          @{app.student_username || 'unknown'}
                        </div>
                        <div style={{ fontSize: '0.85rem', color: '#666' }}>
                          Applied at {formatTimestamp(app.created_at)}
                        </div>
                        <p style={{ marginTop: '0.5rem' }}>{app.message}</p>
                        {app.resume_url && (
                          <a
                            href={app.resume_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="home-link"
                          >
                            View resume
                          </a>
                        )}
                      </div>
                      <div className="match-actions">
                        <Link
                          to={`/profile/${app.student_id}`}
                          className="form-button outline"
                        >
                          View Profile
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default JobDetail;


