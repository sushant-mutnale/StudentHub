import { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { postService } from '../services/postService';
import { userService } from '../services/userService';
import Avatar from './Avatar';
import '../App.css';

const PublicProfile = () => {
  const { userId } = useParams();
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError('');
      try {
        const userData = await userService.getPublicProfile(userId);
        const userPosts = await postService.fetchUserPosts(userId);
        setProfile(userData);
        setPosts(userPosts);
      } catch (err) {
        console.error('PublicProfile load error:', {
          message: err.message,
          code: err.code,
          url: err.config?.url,
          baseURL: err.config?.baseURL,
          method: err.config?.method,
          responseStatus: err.response?.status,
          responseData: err.response?.data,
        });

        const msg =
          err.response?.data?.detail ||
          err.response?.data?.message ||
          err.message ||
          'Unable to load profile.';
        setError(msg);
      } finally {
        setLoading(false);
      }
    };

    if (userId) {
      loadData();
    }
  }, [userId]);

  const stats = useMemo(
    () => ({
      posts: posts.length,
      skills: profile?.skills?.length || 0,
    }),
    [posts, profile]
  );

  if (loading) {
    return (
      <div className="auth-container">
        <div className="auth-box">Loading profile...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="auth-container">
        <div className="auth-box">
          <p className="error-message" style={{ marginBottom: '1rem' }}>
            {error}
          </p>
          <button className="form-button" onClick={() => navigate(-1)}>
            Go Back
          </button>
        </div>
      </div>
    );
  }

  if (!profile) {
    return null;
  }

  const isStudent = profile.role === 'student';

  return (
    <div className="public-profile-page">
      <div className="profile-banner" />
      <div className="public-profile-card">
        <div className="public-profile-header">
          <Avatar
            src={profile.avatar_url}
            alt={profile.full_name || profile.company_name || profile.username}
            size={100}
            className="public-profile-avatar"
          />
          <div>
            <h1>{profile.full_name || profile.company_name}</h1>
            <p className="profile-handle">@{profile.username}</p>
            <p className="profile-role-tag">
              {isStudent ? 'Student' : 'Recruiter'}
            </p>
          </div>
        </div>

        {profile.bio && <p className="profile-bio">{profile.bio}</p>}

        <div className="profile-details-grid">
          {isStudent ? (
            <>
              <div>
                <span className="detail-label">College</span>
                <p>{profile.college || 'Not specified'}</p>
              </div>
              <div>
                <span className="detail-label">Branch</span>
                <p>{profile.branch || 'Not specified'}</p>
              </div>
              <div>
                <span className="detail-label">Year</span>
                <p>{profile.year || 'Not specified'}</p>
              </div>
              <div>
                <span className="detail-label">PRN</span>
                <p>{profile.prn || 'Not specified'}</p>
              </div>
            </>
          ) : (
            <>
              <div>
                <span className="detail-label">Company</span>
                <p>{profile.company_name}</p>
              </div>
              <div>
                <span className="detail-label">Contact</span>
                <p>{profile.contact_number || 'Not specified'}</p>
              </div>
              <div>
                <span className="detail-label">Website</span>
                {profile.website ? (
                  <a href={profile.website} target="_blank" rel="noreferrer">
                    {profile.website}
                  </a>
                ) : (
                  <p>Not specified</p>
                )}
              </div>
              <div>
                <span className="detail-label">About</span>
                <p>{profile.company_description || 'Not specified'}</p>
              </div>
            </>
          )}
        </div>

        {profile.skills?.length > 0 && (
          <div className="profile-skills-section">
            <span className="detail-label">Skills</span>
            <div className="profile-skills">
              {profile.skills.map((skill) => (
                <span key={skill} className="skill-tag">
                  {skill}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="profile-stats">
          <div>
            <span>Posts</span>
            <strong>{stats.posts}</strong>
          </div>
          <div>
            <span>Skills</span>
            <strong>{stats.skills}</strong>
          </div>
        </div>
      </div>

      <div className="public-posts-section">
        <h2>{profile.full_name || profile.company_name}'s Posts</h2>
        {posts.length === 0 ? (
          <div className="empty-state">No posts yet.</div>
        ) : (
          posts.map((post) => (
            <div key={post.id} className="post-item student-post">
              <div className="post-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <Link to={`/profile/${post.author_id}`}>
                    <Avatar
                      src={post.author_avatar_url}
                      alt={post.author_name}
                      size={40}
                    />
                  </Link>
                  <div>
                    <div className="post-author">
                      <Link
                        to={`/profile/${post.author_id}`}
                        className="post-author-link"
                      >
                        {post.author_name}
                      </Link>
                      {' '}
                      <Link
                        to={`/profile/${post.author_id}`}
                        className="post-username"
                      >
                        @{post.author_username}
                      </Link>
                    </div>
                    <div className="post-timestamp">
                      {new Date(post.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>
              </div>
              <div className="post-content">{post.content}</div>
              {post.tags?.length > 0 && (
                <div className="post-tags">
                  {post.tags.map((tag) => (
                    <span key={tag} className="skill-tag">
                      #{tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default PublicProfile;


