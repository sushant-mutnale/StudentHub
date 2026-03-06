import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { userService } from '../services/userService';
import Avatar from './Avatar';
import { FiEdit3, FiSave, FiX, FiPlus, FiTrash2, FiAward, FiTrendingUp, FiActivity, FiUser, FiCheckCircle } from 'react-icons/fi';
import '../App.css';

// Animated Progress Ring Component
const ProgressRing = ({ value, color, size = 80, strokeWidth = 6 }) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (value / 100) * circumference;

  return (
    <svg width={size} height={size} className="progress-ring">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="rgba(0,0,0,0.05)"
        strokeWidth={strokeWidth}
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        style={{
          transition: 'stroke-dashoffset 1s ease-out',
          transform: 'rotate(-90deg)',
          transformOrigin: '50% 50%'
        }}
      />
    </svg>
  );
};

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
  const [saving, setSaving] = useState(false);

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
    setSaving(true);
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
    } finally {
      setSaving(false);
    }
  };

  if (!user || user.role !== 'student') {
    return null;
  }

  const renderAiProfile = () => {
    if (!user.ai_profile) return null;
    const scores = user.ai_profile;

    const scoreItems = [
      {
        label: 'Overall Score',
        value: scores.overall_score,
        color: '#667eea',
        icon: <FiAward />,
        description: 'Weighted combination: Skills (35%), Activity (30%), Interviews (25%), Profile (10%)'
      },
      {
        label: 'Skill Match',
        value: scores.skill_score,
        color: '#10b981',
        icon: <FiCheckCircle />,
        description: 'Based on self-assessed proficiency, verified via resume parsing.'
      },
      {
        label: 'Activity',
        value: scores.activity_score,
        color: '#f59e0b',
        icon: <FiActivity />,
        description: 'Based on recent learning progress and platform engagement.'
      },
      {
        label: 'Interviews',
        value: scores.interview_score,
        color: '#8b5cf6',
        icon: <FiTrendingUp />,
        description: 'Calculated from AI Mock Assessment ratings & feedback.'
      },
      {
        label: 'Completeness',
        value: scores.profile_completeness,
        color: '#ec4899',
        icon: <FiUser />,
        description: 'Measures how completely you have filled out your profile.'
      }
    ];

    return (
      <div className="animate-fade-in-up delay-300" style={{
        marginTop: '2rem',
        padding: '2rem',
        background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%)',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid rgba(102, 126, 234, 0.15)',
        position: 'relative',
        overflow: 'visible'
      }}>
        {/* Decorative background elements */}
        <div style={{
          position: 'absolute',
          top: '-50px',
          right: '-50px',
          width: '150px',
          height: '150px',
          background: 'radial-gradient(circle, rgba(102, 126, 234, 0.1) 0%, transparent 70%)',
          borderRadius: '50%'
        }} />

        <h3 style={{
          marginBottom: '1.5rem',
          color: 'var(--color-text)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          fontSize: '1.25rem'
        }}>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '36px',
            height: '36px',
            background: 'var(--gradient-primary)',
            borderRadius: 'var(--radius-md)',
            fontSize: '1.1rem'
          }}>🚀</span>
          AI Career Profile
          <span style={{
            fontSize: '0.75rem',
            fontWeight: 'normal',
            color: 'var(--color-text-muted)',
            marginLeft: 'auto'
          }}>
            Updated: {new Date(scores.last_computed_at).toLocaleDateString()}
          </span>
        </h3>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
          gap: '1.25rem'
        }}>
          {scoreItems.map((item, idx) => (
            <div
              key={idx}
              className="interactive-card glass-card animate-scale-in tooltip-trigger"
              style={{
                textAlign: 'center',
                padding: '1.25rem 1rem',
                borderRadius: 'var(--radius-md)',
                animationDelay: `${idx * 100}ms`,
                position: 'relative'
              }}
              title={item.description}
            >
              <div style={{
                position: 'relative',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '0.75rem'
              }}>
                <ProgressRing value={item.value} color={item.color} size={72} strokeWidth={5} />
                <div style={{
                  position: 'absolute',
                  fontSize: '1.25rem',
                  fontWeight: '700',
                  color: item.color
                }}>
                  {Math.round(item.value)}%
                </div>
              </div>
              <div style={{
                fontSize: '0.8rem',
                color: 'var(--color-text-secondary)',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.4rem'
              }}>
                <span style={{ color: item.color }}>{item.icon}</span>
                {item.label}
              </div>

              <div style={{
                fontSize: '0.7rem',
                color: 'var(--color-text-muted)',
                marginTop: '0.5rem',
                lineHeight: '1.4'
              }}>
                {item.description}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <>
      
      <div className="dashboard-main">
        <div className="dashboard-header animate-fade-in">
          <h1 className="dashboard-title" style={{
            background: 'var(--gradient-primary)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text'
          }}>Profile</h1>
        </div>
        <div className="dashboard-content">
          <div className="profile-container glass-card animate-fade-in-up" style={{
            padding: '2rem',
            borderRadius: 'var(--radius-lg)',
            position: 'relative',
            overflow: 'hidden'
          }}>
            {/* Success/Error Message Toast */}
            {message && (
              <div className="animate-slide-down" style={{
                position: 'fixed',
                top: '20px',
                right: '20px',
                padding: '1rem 1.5rem',
                borderRadius: 'var(--radius-md)',
                background: message.includes('success') ? 'var(--gradient-success)' : 'var(--gradient-danger)',
                color: 'white',
                fontWeight: '600',
                boxShadow: 'var(--shadow-lg)',
                zIndex: 1000,
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}>
                {message.includes('success') ? <FiCheckCircle /> : <FiX />}
                {message}
              </div>
            )}

            {!isEditing ? (
              <div className="profile-header">
                {/* Profile Header with Avatar */}
                <div style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '2rem',
                  marginBottom: '2rem',
                  paddingBottom: '2rem',
                  borderBottom: '1px solid var(--color-border-light)'
                }}>
                  <div className="animate-bounce-in" style={{ position: 'relative' }}>
                    <div style={{
                      padding: '4px',
                      background: 'var(--gradient-primary)',
                      borderRadius: '50%',
                      boxShadow: 'var(--shadow-glow)'
                    }}>
                      <Avatar
                        src={user.avatar_url}
                        alt={user.fullName || user.username}
                        size={100}
                        style={{ border: '3px solid white' }}
                      />
                    </div>
                    <div style={{
                      position: 'absolute',
                      bottom: '5px',
                      right: '5px',
                      width: '24px',
                      height: '24px',
                      background: 'var(--color-success)',
                      borderRadius: '50%',
                      border: '3px solid white',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}>
                      <FiCheckCircle size={12} color="white" />
                    </div>
                  </div>

                  <div style={{ flex: 1 }} className="animate-fade-in-right delay-100">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div>
                        <h2 style={{
                          fontSize: '1.75rem',
                          fontWeight: '700',
                          color: 'var(--color-text)',
                          marginBottom: '0.25rem'
                        }}>{user.fullName}</h2>
                        <div style={{
                          color: 'var(--color-primary)',
                          fontWeight: '500',
                          fontSize: '1rem'
                        }}>@{user.username}</div>
                      </div>
                      <button
                        className="btn-glow hover-lift"
                        onClick={() => setIsEditing(true)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.5rem',
                          padding: '0.75rem 1.5rem',
                          background: 'var(--gradient-primary)',
                          color: 'white',
                          border: 'none',
                          borderRadius: 'var(--radius-full)',
                          fontWeight: '600',
                          cursor: 'pointer',
                          boxShadow: 'var(--shadow-md)'
                        }}
                      >
                        <FiEdit3 size={16} />
                        Edit Profile
                      </button>
                    </div>

                    {user.bio && (
                      <p style={{
                        marginTop: '1rem',
                        color: 'var(--color-text-secondary)',
                        lineHeight: '1.6'
                      }}>{user.bio}</p>
                    )}
                  </div>
                </div>

                {/* Profile Details Grid */}
                <div className="animate-fade-in-up delay-200" style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: '1.25rem',
                  marginBottom: '1.5rem'
                }}>
                  {[
                    { label: 'College', value: user.college, icon: '🎓' },
                    { label: 'Year', value: user.year, icon: '📅' },
                    { label: 'Branch', value: user.branch, icon: '💻' },
                    { label: 'PRN', value: user.prn, icon: '🆔' }
                  ].map((item, idx) => (
                    <div
                      key={idx}
                      className="hover-lift"
                      style={{
                        padding: '1.25rem',
                        background: 'var(--color-bg-alt)',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--color-border-light)'
                      }}
                    >
                      <div style={{
                        fontSize: '0.75rem',
                        color: 'var(--color-text-muted)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                        marginBottom: '0.5rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem'
                      }}>
                        <span>{item.icon}</span>
                        {item.label}
                      </div>
                      <div style={{
                        fontSize: '1.1rem',
                        fontWeight: '600',
                        color: 'var(--color-text)'
                      }}>
                        {item.value || 'Not specified'}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Skills Section */}
                {user.skills && user.skills.length > 0 && (
                  <div className="animate-fade-in-up delay-300" style={{ marginTop: '2rem' }}>
                    <h3 style={{
                      marginBottom: '1rem',
                      color: 'var(--color-text)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}>
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: '28px',
                        height: '28px',
                        background: 'var(--gradient-success)',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '0.9rem'
                      }}>✨</span>
                      Verified Skills
                    </h3>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
                      {user.skills.map((skill, index) => (
                        <div
                          key={index}
                          className="interactive-card tooltip-trigger"
                          title={`Self-Assessed Level: ${skill.level}%\nVerification Confidence: ${skill.confidence || 30}%\n\nComplete mock assessments and learning modules to increase your verified confidence and boost your overall Skill Match score!`}
                          style={{
                            padding: '0.75rem 1.25rem',
                            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(5, 150, 105, 0.08) 100%)',
                            border: '1px solid rgba(16, 185, 129, 0.2)',
                            borderRadius: 'var(--radius-full)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                            cursor: 'help'
                          }}
                        >
                          <span style={{ fontWeight: '600', color: 'var(--color-text)' }}>{skill.name}</span>
                          <span style={{
                            fontSize: '0.7rem',
                            padding: '0.2rem 0.6rem',
                            background: 'var(--gradient-success)',
                            color: 'white',
                            borderRadius: 'var(--radius-full)',
                            fontWeight: '700'
                          }}>{skill.level}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {renderAiProfile()}
              </div>
            ) : (
              /* Edit Form */
              <div className="profile-form animate-fade-in">
                <form className="auth-form" onSubmit={handleSubmit}>
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '2rem',
                    paddingBottom: '1rem',
                    borderBottom: '1px solid var(--color-border-light)'
                  }}>
                    <h2 style={{ fontSize: '1.5rem', color: 'var(--color-text)' }}>Edit Profile</h2>
                    <button
                      type="button"
                      onClick={() => { setIsEditing(false); setMessage(''); }}
                      style={{
                        padding: '0.5rem',
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        color: 'var(--color-text-muted)'
                      }}
                    >
                      <FiX size={24} />
                    </button>
                  </div>

                  {/* Avatar URL */}
                  <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                    <label className="form-label" style={{ marginBottom: '0.75rem', display: 'block', fontWeight: '600' }}>Profile Picture URL</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                      <div style={{
                        padding: '3px',
                        background: 'var(--gradient-primary)',
                        borderRadius: '50%'
                      }}>
                        <Avatar
                          src={formData.avatar_url}
                          alt={formData.fullName || 'User'}
                          size={70}
                          style={{ border: '2px solid white' }}
                        />
                      </div>
                      <input
                        type="url"
                        name="avatar_url"
                        className="form-input"
                        value={formData.avatar_url}
                        onChange={handleChange}
                        placeholder="https://example.com/avatar.jpg"
                        style={{
                          flex: 1,
                          padding: '1rem',
                          borderRadius: 'var(--radius-md)',
                          border: '2px solid var(--color-border)',
                          transition: 'var(--transition-normal)'
                        }}
                      />
                    </div>
                  </div>

                  {/* Name & College */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                    <div className="form-group">
                      <label className="form-label" style={{ marginBottom: '0.5rem', display: 'block', fontWeight: '600' }}>Full Name</label>
                      <input
                        type="text"
                        name="fullName"
                        className="form-input"
                        value={formData.fullName}
                        onChange={handleChange}
                        required
                        style={{
                          width: '100%',
                          padding: '1rem',
                          borderRadius: 'var(--radius-md)',
                          border: '2px solid var(--color-border)',
                          transition: 'var(--transition-normal)'
                        }}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label" style={{ marginBottom: '0.5rem', display: 'block', fontWeight: '600' }}>College</label>
                      <input
                        type="text"
                        name="college"
                        className="form-input"
                        value={formData.college}
                        onChange={handleChange}
                        required
                        style={{
                          width: '100%',
                          padding: '1rem',
                          borderRadius: 'var(--radius-md)',
                          border: '2px solid var(--color-border)',
                          transition: 'var(--transition-normal)'
                        }}
                      />
                    </div>
                  </div>

                  {/* Year & Branch */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
                    <div className="form-group">
                      <label className="form-label" style={{ marginBottom: '0.5rem', display: 'block', fontWeight: '600' }}>Year</label>
                      <select
                        name="year"
                        className="form-input"
                        value={formData.year}
                        onChange={handleChange}
                        required
                        style={{
                          width: '100%',
                          padding: '1rem',
                          borderRadius: 'var(--radius-md)',
                          border: '2px solid var(--color-border)',
                          transition: 'var(--transition-normal)',
                          cursor: 'pointer'
                        }}
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
                      <label className="form-label" style={{ marginBottom: '0.5rem', display: 'block', fontWeight: '600' }}>Branch</label>
                      <input
                        type="text"
                        name="branch"
                        className="form-input"
                        value={formData.branch}
                        onChange={handleChange}
                        required
                        style={{
                          width: '100%',
                          padding: '1rem',
                          borderRadius: 'var(--radius-md)',
                          border: '2px solid var(--color-border)',
                          transition: 'var(--transition-normal)'
                        }}
                      />
                    </div>
                  </div>

                  {/* Skills Section */}
                  <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '1rem'
                    }}>
                      <label className="form-label" style={{ margin: 0, fontWeight: '600' }}>Skills</label>
                      <button
                        type="button"
                        onClick={addSkill}
                        className="btn-glow"
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.4rem',
                          padding: '0.5rem 1rem',
                          background: 'var(--gradient-success)',
                          color: 'white',
                          border: 'none',
                          borderRadius: 'var(--radius-full)',
                          fontSize: '0.85rem',
                          fontWeight: '600',
                          cursor: 'pointer'
                        }}
                      >
                        <FiPlus size={14} />
                        Add Skill
                      </button>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                      {formData.skills.map((skill, index) => (
                        <div
                          key={index}
                          className="animate-fade-in-up"
                          style={{
                            display: 'grid',
                            gridTemplateColumns: '2fr 1.5fr 80px 40px',
                            gap: '0.75rem',
                            alignItems: 'center',
                            background: 'var(--color-bg-alt)',
                            padding: '1rem',
                            borderRadius: 'var(--radius-md)',
                            border: '1px solid var(--color-border-light)'
                          }}
                        >
                          <input
                            type="text"
                            placeholder="Skill Name (e.g., Python, React)"
                            value={skill.name}
                            onChange={(e) => handleSkillChange(index, 'name', e.target.value)}
                            required
                            style={{
                              padding: '0.75rem',
                              borderRadius: 'var(--radius-sm)',
                              border: '2px solid var(--color-border)',
                              transition: 'var(--transition-normal)'
                            }}
                          />
                          <select
                            value={skill.proficiency}
                            onChange={(e) => handleSkillChange(index, 'proficiency', e.target.value)}
                            style={{
                              padding: '0.75rem',
                              borderRadius: 'var(--radius-sm)',
                              border: '2px solid var(--color-border)',
                              cursor: 'pointer'
                            }}
                          >
                            <option value="Beginner">Beginner</option>
                            <option value="Intermediate">Intermediate</option>
                            <option value="Advanced">Advanced</option>
                          </select>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                            <input
                              type="number"
                              min="0"
                              max="100"
                              value={skill.level}
                              onChange={(e) => handleSkillChange(index, 'level', parseInt(e.target.value) || 0)}
                              style={{
                                width: '60px',
                                padding: '0.75rem 0.5rem',
                                borderRadius: 'var(--radius-sm)',
                                border: '2px solid var(--color-border)',
                                textAlign: 'center'
                              }}
                            />
                            <span style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>%</span>
                          </div>
                          <button
                            type="button"
                            onClick={() => removeSkill(index)}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              width: '36px',
                              height: '36px',
                              background: 'rgba(239, 68, 68, 0.1)',
                              border: 'none',
                              borderRadius: 'var(--radius-sm)',
                              color: 'var(--color-danger)',
                              cursor: 'pointer',
                              transition: 'var(--transition-fast)'
                            }}
                          >
                            <FiTrash2 size={16} />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Bio */}
                  <div className="form-group" style={{ marginBottom: '2rem' }}>
                    <label className="form-label" style={{ marginBottom: '0.5rem', display: 'block', fontWeight: '600' }}>Bio</label>
                    <textarea
                      name="bio"
                      value={formData.bio}
                      onChange={handleChange}
                      rows="3"
                      placeholder="Tell us about yourself..."
                      style={{
                        width: '100%',
                        padding: '1rem',
                        borderRadius: 'var(--radius-md)',
                        border: '2px solid var(--color-border)',
                        transition: 'var(--transition-normal)',
                        resize: 'vertical',
                        fontFamily: 'inherit'
                      }}
                    />
                  </div>

                  {/* Action Buttons */}
                  <div style={{ display: 'flex', gap: '1rem' }}>
                    <button
                      type="submit"
                      disabled={saving}
                      className="btn-glow"
                      style={{
                        flex: 1,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.5rem',
                        padding: '1rem 2rem',
                        background: 'var(--gradient-primary)',
                        color: 'white',
                        border: 'none',
                        borderRadius: 'var(--radius-md)',
                        fontSize: '1rem',
                        fontWeight: '600',
                        cursor: saving ? 'not-allowed' : 'pointer',
                        opacity: saving ? 0.7 : 1,
                        boxShadow: 'var(--shadow-md)'
                      }}
                    >
                      {saving ? (
                        <>
                          <div className="animate-spin" style={{
                            width: '18px',
                            height: '18px',
                            border: '2px solid rgba(255,255,255,0.3)',
                            borderTopColor: 'white',
                            borderRadius: '50%'
                          }} />
                          Saving...
                        </>
                      ) : (
                        <>
                          <FiSave size={18} />
                          Save Profile & Recalculate AI Score
                        </>
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => { setIsEditing(false); setMessage(''); }}
                      style={{
                        padding: '1rem 2rem',
                        background: 'var(--color-bg-alt)',
                        color: 'var(--color-text-secondary)',
                        border: '2px solid var(--color-border)',
                        borderRadius: 'var(--radius-md)',
                        fontSize: '1rem',
                        fontWeight: '600',
                        cursor: 'pointer',
                        transition: 'var(--transition-normal)'
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
    </>
  );
};

export default Profile;
