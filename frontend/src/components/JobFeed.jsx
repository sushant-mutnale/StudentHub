import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { FiMapPin } from 'react-icons/fi';
import { useAuth } from '../contexts/AuthContext';
import { jobService } from '../services/jobService';
import '../App.css';

const PAGE_SIZE = 20;

const JobFeed = ({ refreshTrigger = 0 }) => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(false);

  useEffect(() => {
    // Reset and load from the beginning whenever the refresh trigger changes
    setPage(0);
    loadJobs(0, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshTrigger]);

  const loadJobs = async (pageToLoad = page, replace = false) => {
    setLoading(true);
    try {
      const skip = pageToLoad * PAGE_SIZE;
      const data = await jobService.getJobs({ limit: PAGE_SIZE, skip });
      setJobs((prev) => (replace ? data : [...prev, ...data]));
      setHasMore(data.length === PAGE_SIZE);
      setError('');
    } catch (err) {
      setError(err.message || 'Unable to load jobs');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    loadJobs(nextPage);
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  if (!user || user.role !== 'student') {
    return null;
  }

  return (
    <div className="jobs-section student-jobs">
      <div className="jobs-section-header">
        <h2>Latest Jobs</h2>
        <span>{jobs.length} visible</span>
      </div>

      {loading && jobs.length === 0 && (
        <div className="empty-state">Loading jobs...</div>
      )}

      {error && (
        <div className="error-message" style={{ marginBottom: '0.75rem' }}>
          {error}
        </div>
      )}

      {!loading && jobs.length === 0 && !error && (
        <div className="empty-state">
          No jobs yet — check back later.
        </div>
      )}

      {jobs.map((job) => (
        <div key={job.id} className="job-item">
          <div className="job-header">
            <div>
              <div className="job-title">{job.title}</div>
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
            </div>
            <div className="job-timestamp">{formatTimestamp(job.created_at)}</div>
          </div>

          <div className="job-description">
            {job.description.length > 220
              ? `${job.description.slice(0, 220)}…`
              : job.description}
          </div>

          <div className="job-details">
            <div className="job-detail">
              <FiMapPin />
              <span>{job.location}</span>
            </div>
          </div>

          <div className="job-skills">
            {job.skills_required?.map((skill) => (
              <span key={skill} className="skill-tag">
                {skill}
              </span>
            ))}
          </div>

          <div className="job-actions">
            <button
              type="button"
              className="form-button outline"
              style={{ width: 'fit-content' }}
              onClick={() => navigate(`/jobs/${job.id}`)}
            >
              Apply / View Details
            </button>
          </div>
        </div>
      ))}

      {hasMore && !loading && (
        <div style={{ textAlign: 'center', marginTop: '1rem' }}>
          <button type="button" className="form-button outline" onClick={handleLoadMore}>
            Load more
          </button>
        </div>
      )}
    </div>
  );
};

export default JobFeed;


