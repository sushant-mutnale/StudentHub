import { useEffect, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { jobService } from '../services/jobService';
import SidebarLeft from './SidebarLeft';
import { FiMapPin, FiBriefcase, FiDollarSign, FiClock, FiCheckCircle, FiSend, FiLoader, FiArrowLeft, FiUser, FiInfo } from 'react-icons/fi';
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
      setApplySuccess('Application submitted successfully!');
    } catch (err) {
      setError(err.message || 'Failed to submit application');
    } finally {
      setApplyLoading(false);
    }
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
  };

  if (loading) {
    return (
      <div className="dashboard-container">
        <SidebarLeft />
        <div className="dashboard-main" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <div style={{ textAlign: 'center', color: 'var(--color-text-muted)' }}>
            <FiLoader className="animate-spin" size={32} />
            <p style={{ marginTop: '1rem' }}>Loading job details...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error && !job) {
    return (
      <div className="dashboard-container">
        <SidebarLeft />
        <div className="dashboard-main">
          <div style={{ padding: '2rem' }}>
            <button onClick={() => navigate(-1)} className="btn-ghost" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <FiArrowLeft /> Back
            </button>
            <div className="error-message">{error}</div>
          </div>
        </div>
      </div>
    );
  }

  if (!job) return null;

  const isStudent = user?.role === 'student';
  const isRecruiter = user?.role === 'recruiter';

  return (
    <div className="dashboard-container">
      <SidebarLeft />
      <div className="dashboard-main custom-scrollbar">
        <div className="dashboard-header animate-fade-in-down">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <button
              onClick={() => navigate(-1)}
              className="btn-icon hover-scale"
              style={{ color: 'var(--color-text)' }}
            >
              <FiArrowLeft size={20} />
            </button>
            <h1 className="dashboard-title" style={{ fontSize: '1.25rem', margin: 0 }}>Job Details</h1>
          </div>
        </div>

        <div className="dashboard-content" style={{ maxWidth: '900px', margin: '0 auto' }}>
          {/* Hero Section */}
          <div className="glass-card animate-fade-in-up" style={{ padding: '2rem', marginBottom: '2rem', borderRadius: 'var(--radius-lg)' }}>
            <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
              <div style={{
                width: '80px',
                height: '80px',
                background: 'linear-gradient(135deg, #f0f4ff 0%, #e0e7ff 100%)',
                borderRadius: '16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '2rem',
                color: 'var(--color-primary)',
                fontWeight: '700',
                boxShadow: 'var(--shadow-sm)'
              }}>
                {job.company_name ? job.company_name[0].toUpperCase() : <FiBriefcase />}
              </div>

              <div style={{ flex: 1 }}>
                <h1 style={{
                  margin: '0 0 0.5rem 0',
                  fontSize: '1.75rem',
                  color: 'var(--color-text)',
                  lineHeight: '1.2'
                }}>
                  {job.title}
                </h1>

                <div style={{
                  color: 'var(--color-primary)',
                  fontWeight: '600',
                  fontSize: '1.1rem',
                  marginBottom: '1rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}>
                  {job.company_name || 'Hidden Company'}
                </div>

                <div style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '1.5rem',
                  fontSize: '0.95rem',
                  color: 'var(--color-text-secondary)',
                  marginTop: '1rem'
                }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <FiMapPin className="text-primary" /> {job.location || 'Remote'}
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <FiClock className="text-primary" /> {job.type || 'Full-time'}
                  </span>
                  {job.salary_range && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <FiDollarSign className="text-primary" /> {job.salary_range}
                    </span>
                  )}
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <FiInfo className="text-primary" /> Posted {formatTimestamp(job.created_at)}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) minmax(0, 1fr)', gap: '2rem', alignItems: 'start' }}>
            {/* Left Column: Description & Application */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>

              {/* Description */}
              <div className="glass-card animate-fade-in-up delay-100" style={{ padding: '2rem', borderRadius: 'var(--radius-lg)' }}>
                <h3 style={{ marginBottom: '1.5rem', color: 'var(--color-text)' }}>About the Role</h3>
                <div style={{
                  color: 'var(--color-text-secondary)',
                  lineHeight: '1.8',
                  fontSize: '1.05rem',
                  whiteSpace: 'pre-wrap'
                }}>
                  {job.description}
                </div>
              </div>

              {/* Skills */}
              <div className="glass-card animate-fade-in-up delay-200" style={{ padding: '2rem', borderRadius: 'var(--radius-lg)' }}>
                <h3 style={{ marginBottom: '1.5rem', color: 'var(--color-text)' }}>Required Skills</h3>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
                  {job.skills_required?.map((skill, idx) => (
                    <span key={idx} style={{
                      padding: '0.5rem 1rem',
                      background: 'var(--gradient-primary)',
                      color: 'white',
                      borderRadius: 'var(--radius-full)',
                      fontWeight: '500',
                      boxShadow: 'var(--shadow-sm)'
                    }}>
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              {/* AI Interview Agent Promo */}
              {isStudent && (
                <div className="glass-card animate-fade-in-up delay-300" style={{
                  padding: '2rem',
                  borderRadius: 'var(--radius-lg)',
                  background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.05) 0%, rgba(37, 99, 235, 0.05) 100%)',
                  border: '1px solid rgba(59, 130, 246, 0.2)'
                }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1.5rem' }}>
                    <div style={{
                      width: '56px',
                      height: '56px',
                      background: 'var(--gradient-info)',
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '1.75rem',
                      color: 'white',
                      flexShrink: 0
                    }}>
                      🤖
                    </div>
                    <div>
                      <h3 style={{ marginBottom: '0.5rem', color: 'var(--color-info)' }}>Prepare with AI</h3>
                      <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1.5rem', lineHeight: '1.6' }}>
                        Stand out from other candidates by practicing with our AI Interviewer tailored specifically to this job description.
                      </p>
                      <Link
                        to={`/interviews/agent/${jobId}`}
                        className="btn-glow hover-lift"
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.5rem',
                          background: 'var(--gradient-info)',
                          color: 'white',
                          padding: '0.75rem 1.5rem',
                          borderRadius: 'var(--radius-md)',
                          textDecoration: 'none',
                          fontWeight: '600'
                        }}
                      >
                        <FiUser /> Start AI Interview
                      </Link>
                    </div>
                  </div>
                </div>
              )}

              {/* Application Form */}
              {isStudent && (
                <div className="glass-card animate-fade-in-up delay-300" style={{ padding: '2rem', borderRadius: 'var(--radius-lg)' }}>
                  <h3 style={{ marginBottom: '1.5rem', color: 'var(--color-text)' }}>Apply Now</h3>

                  {applySuccess ? (
                    <div className="animate-scale-in" style={{
                      padding: '1.5rem',
                      background: 'rgba(16, 185, 129, 0.1)',
                      borderRadius: 'var(--radius-md)',
                      color: 'var(--color-success)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '1rem'
                    }}>
                      <FiCheckCircle size={24} />
                      <div>
                        <strong>Success!</strong>
                        <div>{applySuccess}</div>
                      </div>
                    </div>
                  ) : (
                    <form onSubmit={handleApply}>
                      <div style={{ marginBottom: '1.5rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: 'var(--color-text)' }}>
                          Message to Recruiter <span style={{ color: 'var(--color-danger)' }}>*</span>
                        </label>
                        <textarea
                          className="form-textarea"
                          rows="5"
                          value={applyMessage}
                          onChange={(e) => setApplyMessage(e.target.value)}
                          placeholder="Briefly explain why you're a good fit for this role..."
                          required
                          style={{
                            width: '100%',
                            padding: '1rem',
                            border: '1px solid var(--color-border)',
                            borderRadius: 'var(--radius-md)',
                            fontFamily: 'inherit',
                            fontSize: '1rem',
                            outline: 'none',
                            transition: 'border-color 0.2s'
                          }}
                          onFocus={(e) => e.target.style.borderColor = 'var(--color-primary)'}
                          onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'}
                        />
                      </div>

                      <div style={{ marginBottom: '2rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: 'var(--color-text)' }}>
                          Resume URL (Optional)
                        </label>
                        <input
                          type="url"
                          value={applyResumeUrl}
                          onChange={(e) => setApplyResumeUrl(e.target.value)}
                          placeholder="https://drive.google.com/your-resume"
                          style={{
                            width: '100%',
                            padding: '0.75rem',
                            border: '1px solid var(--color-border)',
                            borderRadius: 'var(--radius-md)',
                            fontFamily: 'inherit',
                            fontSize: '1rem',
                            outline: 'none',
                            transition: 'border-color 0.2s'
                          }}
                          onFocus={(e) => e.target.style.borderColor = 'var(--color-primary)'}
                          onBlur={(e) => e.target.style.borderColor = 'var(--color-border)'}
                        />
                      </div>

                      {error && (
                        <div style={{
                          padding: '0.75rem',
                          background: 'rgba(239, 68, 68, 0.1)',
                          color: 'var(--color-danger)',
                          borderRadius: 'var(--radius-md)',
                          marginBottom: '1rem'
                        }}>
                          {error}
                        </div>
                      )}

                      <button
                        type="submit"
                        className="btn-glow hover-lift"
                        disabled={applyLoading || !applyMessage.trim()}
                        style={{
                          width: '100%',
                          padding: '1rem',
                          background: 'var(--gradient-primary)',
                          color: 'white',
                          border: 'none',
                          borderRadius: 'var(--radius-md)',
                          fontWeight: '600',
                          fontSize: '1.05rem',
                          cursor: applyLoading || !applyMessage.trim() ? 'not-allowed' : 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '0.75rem',
                          opacity: applyLoading || !applyMessage.trim() ? 0.7 : 1
                        }}
                      >
                        {applyLoading ? (
                          <>
                            <FiLoader className="animate-spin" /> Submitting...
                          </>
                        ) : (
                          <>
                            <FiSend /> Submit Application
                          </>
                        )}
                      </button>
                    </form>
                  )}
                </div>
              )}

              {/* Recruiter View: Applications */}
              {isRecruiter && (
                <div className="glass-card animate-fade-in-up delay-300" style={{ padding: '2rem', borderRadius: 'var(--radius-lg)' }}>
                  <h3 style={{ marginBottom: '1.5rem', color: 'var(--color-text)' }}>
                    Applications ({applications.length})
                  </h3>

                  {appsLoading && <div style={{ textAlign: 'center', padding: '1rem' }}><FiLoader className="animate-spin" /> Loading...</div>}
                  {appsError && <div className="error-message">{appsError}</div>}

                  {!appsLoading && applications.length === 0 && !appsError && (
                    <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--color-text-muted)' }}>
                      No applications yet.
                    </div>
                  )}

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {applications.map((app) => (
                      <div key={app.id} className="interactive-card" style={{
                        padding: '1.5rem',
                        background: 'var(--color-bg-alt)',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--color-border-light)'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                          <div>
                            <div style={{ fontWeight: '700', fontSize: '1.1rem', color: 'var(--color-text)' }}>{app.student_name || 'Student'}</div>
                            <div style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>@{app.student_username || 'unknown'}</div>
                          </div>
                          <Link
                            to={`/profile/${app.student_id}`}
                            className="btn-ghost"
                            style={{ fontSize: '0.9rem', padding: '0.3rem 0.75rem' }}
                          >
                            View Profile
                          </Link>
                        </div>

                        <div style={{
                          background: 'white',
                          padding: '1rem',
                          borderRadius: 'var(--radius-md)',
                          marginBottom: '1rem',
                          fontStyle: 'italic',
                          color: 'var(--color-text-secondary)'
                        }}>
                          "{app.message}"
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
                          <span style={{ color: 'var(--color-text-muted)' }}>Applied {formatTimestamp(app.created_at)}</span>
                          {app.resume_url && (
                            <a
                              href={app.resume_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{ color: 'var(--color-primary)', fontWeight: '600', textDecoration: 'none' }}
                            >
                              View Resume →
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Right Column: Company Info (Sticky) */}
            <div style={{ position: 'sticky', top: '90px' }}>
              <div className="glass-card animate-fade-in-up delay-200" style={{ padding: '2rem', borderRadius: 'var(--radius-lg)' }}>
                <h4 style={{ marginBottom: '1rem', color: 'var(--color-text)' }}>About the Company</h4>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                  <div style={{
                    width: '48px',
                    height: '48px',
                    background: 'var(--color-bg-alt)',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--color-text-muted)'
                  }}>
                    {job.company_name ? job.company_name[0].toUpperCase() : <FiBriefcase />}
                  </div>
                  <div>
                    <div style={{ fontWeight: '700', color: 'var(--color-text)' }}>{job.company_name || 'Company'}</div>
                    <Link to={`/profile/${job.recruiter_id}`} style={{ fontSize: '0.9rem', color: 'var(--color-primary)', textDecoration: 'none' }}>
                      View Company Profile
                    </Link>
                  </div>
                </div>

                <div style={{ height: '1px', background: 'var(--color-border-light)', margin: '1rem 0' }} />

                <h4 style={{ marginBottom: '1rem', color: 'var(--color-text)' }}>Similar Roles</h4>
                <div style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', fontStyle: 'italic' }}>
                  More opportunities from this company will appear here.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default JobDetail;
