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
      skills: user.skills || [],
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

  const handleSkillChange = (index, field, value) => {
    const newSkills = [...formData.skills];
    newSkills[index] = { ...newSkills[index], [field]: value };
    setFormData({ ...formData, skills: newSkills });
  };

  const addSkill = () => {
    setFormData({
      ...formData,
      skills: [...formData.skills, { name: '', level: 50, proficiency: 'Intermediate' }]
    });
  };

  const removeSkill = (index) => {
    const newSkills = formData.skills.filter((_, i) => i !== index);
    setFormData({ ...formData, skills: newSkills });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        full_name: formData.fullName,
        college: formData.college,
        year: formData.year,
        branch: formData.branch,
        bio: formData.bio,
        skills: formData.skills,
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

  const renderAiProfile = () => {
    if (!user.ai_profile) return null;
    const scores = user.ai_profile;

    return (
      <div className="ai-profile-section" style={{ marginTop: '2rem', padding: '1.5rem', background: 'rgba(52, 152, 219, 0.05)', borderRadius: '12px', border: '1px solid rgba(52, 152, 219, 0.1)' }}>
        <h3 style={{ marginBottom: '1rem', color: '#2c3e50', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          🚀 AI Career Profile
          <span style={{ fontSize: '0.8rem', fontWeight: 'normal', color: '#7f8c8d' }}>(Last updated: {new Date(scores.last_computed_at).toLocaleDateString()})</span>
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '1rem' }}>
          {[
            { label: 'Overall Score', value: scores.overall_score, color: '#3498db' },
            { label: 'Skill Match', value: scores.skill_score, color: '#2ecc71' },
            { label: 'Activity', value: scores.activity_score, color: '#f1c40f' },
            { label: 'Interviews', value: scores.interview_score, color: '#9b59b6' },
            { label: 'Completeness', value: scores.profile_completeness, color: '#e67e22' }
          ].map((item, idx) => (
            <div key={idx} style={{ textAlign: 'center', padding: '1rem', background: 'white', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
              <div style={{ fontSize: '0.75rem', color: '#7f8c8d', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{item.label}</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: item.color }}>{Math.round(item.value)}%</div>
              <div style={{ height: '4px', width: '100%', background: '#eee', borderRadius: '2px', marginTop: '0.5rem' }}>
                <div style={{ height: '100%', width: `${item.value}%`, background: item.color, borderRadius: '2px' }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

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
                    size={100}
                    className="profile-avatar-large"
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div>
                        <h2 className="profile-name">{user.fullName}</h2>
                        <div className="profile-username">@{user.username}</div>
                      </div>
                      <button
                        className="edit-button"
                        onClick={() => setIsEditing(true)}
                        style={{ margin: 0 }}
                      >
                        Edit Profile
                      </button>
                    </div>
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
                    <div className="profile-detail-label" style={{ marginBottom: '0.8rem' }}>
                      Verified Skills
                    </div>
                    <div className="profile-skills" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.8rem' }}>
                      {user.skills.map((skill, index) => (
                        <div key={index} style={{ padding: '0.6rem 1rem', background: '#f8f9fa', border: '1px solid #e9ecef', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '0.2rem', minWidth: '100px' }}>
                          <span style={{ fontWeight: '600', color: '#2c3e50' }}>{skill.name}</span>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem' }}>
                            <span style={{ color: '#34495e' }}>{skill.proficiency}</span>
                            <span style={{ color: '#3498db', fontWeight: 'bold' }}>{skill.level}%</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {renderAiProfile()}
              </div>
            ) : (
              <div className="profile-form">
                {message && (
                  <div className={message.includes('success') ? 'success-message' : 'error-message'}>
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
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
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
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
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
                  </div>

                  <div className="form-group">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem' }}>
                      <label className="form-label" style={{ margin: 0 }}>Structured Skills</label>
                      <button type="button" onClick={addSkill} className="edit-button" style={{ margin: 0, padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}>+ Add Skill</button>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                      {formData.skills.map((skill, index) => (
                        <div key={index} style={{ display: 'grid', gridTemplateColumns: '2fr 1.5fr 1fr 40px', gap: '0.8rem', alignItems: 'center', background: '#f8f9fa', padding: '0.8rem', borderRadius: '8px' }}>
                          <input
                            type="text"
                            placeholder="Skill Name"
                            className="form-input"
                            style={{ marginBottom: 0 }}
                            value={skill.name}
                            onChange={(e) => handleSkillChange(index, 'name', e.target.value)}
                            required
                          />
                          <select
                            className="form-input"
                            style={{ marginBottom: 0 }}
                            value={skill.proficiency}
                            onChange={(e) => handleSkillChange(index, 'proficiency', e.target.value)}
                          >
                            <option value="Beginner">Beginner</option>
                            <option value="Intermediate">Intermediate</option>
                            <option value="Advanced">Advanced</option>
                          </select>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <input
                              type="number"
                              min="0"
                              max="100"
                              className="form-input"
                              style={{ marginBottom: 0, padding: '0.4rem' }}
                              value={skill.level}
                              onChange={(e) => handleSkillChange(index, 'level', parseInt(e.target.value))}
                            />
                            <span style={{ fontSize: '0.8rem' }}>%</span>
                          </div>
                          <button type="button" onClick={() => removeSkill(index)} style={{ border: 'none', background: 'none', color: '#e74c3c', cursor: 'pointer', fontSize: '1.2rem' }}>×</button>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Bio</label>
                    <textarea
                      name="bio"
                      className="form-textarea"
                      value={formData.bio}
                      onChange={handleChange}
                      rows="3"
                    />
                  </div>

                  <div style={{ display: 'flex', gap: '1rem' }}>
                    <button type="submit" className="form-button">
                      Save Profile & Recalculate AI Score
                    </button>
                    <button
                      type="button"
                      className="form-button"
                      style={{ backgroundColor: '#95a5a6' }}
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

