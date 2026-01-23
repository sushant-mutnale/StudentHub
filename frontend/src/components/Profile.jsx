import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { userService } from '../services/userService';
import SidebarLeft from './SidebarLeft';
import Avatar from './Avatar';
import '../App.css';

const Profile = () => {
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    fullName: '',
    college: '',
    year: '',
    branch: '',
    skills: '',
    bio: '',
    avatar_url: '',
  });
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!user || user.role !== 'student') {
      navigate('/');
      return;
    }

    setFormData({
      fullName: user.fullName || '',
      college: user.college || '',
      year: user.year || '',
      branch: user.branch || '',
      skills: user.skills ? user.skills.join(', ') : '',
      bio: user.bio || '',
      avatar_url: user.avatar_url || '',
    });
  }, [user, navigate]);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const skillsArray = formData.skills
        .split(',')
        .map((skill) => skill.trim())
        .filter((skill) => skill.length > 0);

      const payload = {
        full_name: formData.fullName,
        college: formData.college,
        year: formData.year,
        branch: formData.branch,
        bio: formData.bio,
        skills: skillsArray,
        avatar_url: formData.avatar_url || null,
      };

      await userService.updateMe(payload);
      await refreshUser();
      setMessage('Profile updated successfully!');
      setIsEditing(false);
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      setMessage('Error updating profile. Please try again.');
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
          <h1 className="dashboard-title">Profile</h1>
        </div>
        <div className="dashboard-content">
          <div className="profile-container">
            {!isEditing ? (
              <div className="profile-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', marginBottom: '1.5rem' }}>
                  <Avatar
                    src={user.avatar_url}
                    alt={user.fullName || user.username}
                    size={120}
                    className="profile-avatar-large"
                  />
                  <div>
                    <h2 className="profile-name">{user.fullName}</h2>
                    <div className="profile-username">@{user.username}</div>
                  </div>
                </div>
                {user.bio && <div className="profile-bio">{user.bio}</div>}
                
                <div className="profile-details">
                  <div className="profile-detail">
                    <div className="profile-detail-label">College</div>
                    <div className="profile-detail-value">{user.college || 'Not specified'}</div>
                  </div>
                  <div className="profile-detail">
                    <div className="profile-detail-label">Year</div>
                    <div className="profile-detail-value">{user.year || 'Not specified'}</div>
                  </div>
                  <div className="profile-detail">
                    <div className="profile-detail-label">Branch</div>
                    <div className="profile-detail-value">{user.branch || 'Not specified'}</div>
                  </div>
                  <div className="profile-detail">
                    <div className="profile-detail-label">PRN</div>
                    <div className="profile-detail-value">{user.prn || 'Not specified'}</div>
                  </div>
                </div>

                {user.skills && user.skills.length > 0 && (
                  <div style={{ marginTop: '1.5rem' }}>
                    <div className="profile-detail-label" style={{ marginBottom: '0.5rem' }}>
                      Skills
                    </div>
                    <div className="profile-skills">
                      {user.skills.map((skill, index) => (
                        <span key={index} className="skill-tag">
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <button
                  className="edit-button"
                  onClick={() => setIsEditing(true)}
                >
                  Edit Profile
                </button>
              </div>
            ) : (
              <div className="profile-form">
                {message && (
                  <div
                    className={
                      message.includes('success')
                        ? 'success-message'
                        : 'error-message'
                    }
                  >
                    {message}
                  </div>
                )}

                <form className="auth-form" onSubmit={handleSubmit}>
                  <div className="form-group">
                    <label className="form-label">Profile Picture URL</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                      <Avatar
                        src={formData.avatar_url}
                        alt={formData.fullName || 'User'}
                        size={80}
                      />
                      <input
                        type="url"
                        name="avatar_url"
                        className="form-input"
                        value={formData.avatar_url}
                        onChange={handleChange}
                        placeholder="https://example.com/avatar.jpg"
                        style={{ flex: 1 }}
                      />
                    </div>
                    <p style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.25rem' }}>
                      Paste an image URL to set your profile picture
                    </p>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Full Name</label>
                    <input
                      type="text"
                      name="fullName"
                      className="form-input"
                      value={formData.fullName}
                      onChange={handleChange}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">College</label>
                    <input
                      type="text"
                      name="college"
                      className="form-input"
                      value={formData.college}
                      onChange={handleChange}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Year</label>
                    <select
                      name="year"
                      className="form-input"
                      value={formData.year}
                      onChange={handleChange}
                      required
                    >
                      <option value="">Select Year</option>
                      <option value="1st Year">1st Year</option>
                      <option value="2nd Year">2nd Year</option>
                      <option value="3rd Year">3rd Year</option>
                      <option value="4th Year">4th Year</option>
                      <option value="Graduate">Graduate</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Branch</label>
                    <input
                      type="text"
                      name="branch"
                      className="form-input"
                      value={formData.branch}
                      onChange={handleChange}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Skills</label>
                    <input
                      type="text"
                      name="skills"
                      className="form-input"
                      value={formData.skills}
                      onChange={handleChange}
                      placeholder="Comma-separated: React, Node.js, Python"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Bio</label>
                    <textarea
                      name="bio"
                      className="form-textarea"
                      value={formData.bio}
                      onChange={handleChange}
                      rows="4"
                    />
                  </div>

                  <div style={{ display: 'flex', gap: '1rem' }}>
                    <button type="submit" className="form-button">
                      Save Changes
                    </button>
                    <button
                      type="button"
                      className="form-button"
                      style={{ backgroundColor: '#999' }}
                      onClick={() => {
                        setIsEditing(false);
                        setMessage('');
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;

