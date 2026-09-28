import { useState, useEffect } from 'react';
import { FiSearch, FiBell, FiBellOff, FiTrash2, FiUsers, FiPlus, FiMapPin, FiBookOpen } from 'react-icons/fi';
import { Link } from 'react-router-dom';
import { savedSearchService } from '../services/savedSearchService';

const SavedSearchesSection = ({ onError, onSuccess }) => {
  const [searches, setSearches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [activeSearchId, setActiveSearchId] = useState(null);
  const [candidates, setCandidates] = useState({});
  const [loadingCandidates, setLoadingCandidates] = useState({});

  const [formData, setFormData] = useState({
    name: '',
    skill: '',
    location: '',
    college: '',
    min_score: '',
    alert_enabled: true,
  });

  useEffect(() => {
    loadSearches();
  }, []);

  const loadSearches = async () => {
    setLoading(true);
    try {
      const data = await savedSearchService.listSavedSearches();
      setSearches(data);
    } catch (err) {
      onError?.(err.message || 'Failed to load saved searches');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleCreateSearch = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        name: formData.name,
        skill: formData.skill || null,
        location: formData.location || null,
        college: formData.college || null,
        min_score: formData.min_score ? parseFloat(formData.min_score) : null,
        alert_enabled: formData.alert_enabled,
      };
      await savedSearchService.createSavedSearch(payload);
      setFormData({
        name: '',
        skill: '',
        location: '',
        college: '',
        min_score: '',
        alert_enabled: true,
      });
      setShowCreateModal(false);
      onSuccess?.('Saved search created successfully');
      loadSearches();
    } catch (err) {
      onError?.(err.message || 'Failed to create saved search');
    }
  };

  const handleToggleAlert = async (search) => {
    try {
      await savedSearchService.updateSavedSearch(search.id, {
        alert_enabled: !search.alert_enabled,
      });
      setSearches((prev) =>
        prev.map((s) =>
          s.id === search.id ? { ...s, alert_enabled: !s.alert_enabled } : s
        )
      );
      onSuccess?.(
        `Alerts ${!search.alert_enabled ? 'enabled' : 'disabled'} for ${search.name}`
      );
    } catch (err) {
      onError?.(err.message || 'Failed to update alert setting');
    }
  };

  const handleDeleteSearch = async (id) => {
    if (!window.confirm('Are you sure you want to delete this saved search?')) return;
    try {
      await savedSearchService.deleteSavedSearch(id);
      setSearches((prev) => prev.filter((s) => s.id !== id));
      onSuccess?.('Saved search deleted');
    } catch (err) {
      onError?.(err.message || 'Failed to delete saved search');
    }
  };

  const handleViewCandidates = async (searchId) => {
    if (activeSearchId === searchId) {
      setActiveSearchId(null);
      return;
    }
    setActiveSearchId(searchId);
    if (!candidates[searchId]) {
      setLoadingCandidates((prev) => ({ ...prev, [searchId]: true }));
      try {
        const list = await savedSearchService.getSavedSearchCandidates(searchId);
        setCandidates((prev) => ({ ...prev, [searchId]: list }));
      } catch (err) {
        onError?.(err.message || 'Failed to fetch matching candidates');
      } finally {
        setLoadingCandidates((prev) => ({ ...prev, [searchId]: false }));
      }
    }
  };

  return (
    <div className="saved-searches-section" style={{ marginTop: '2.5rem' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.5rem',
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: '1.4rem', color: '#1e293b', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FiSearch style={{ color: '#3b82f6' }} /> Saved Searches & Alerts
          </h2>
          <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: '0.9rem' }}>
            Save candidate filters to get automated alerts when matching students join.
          </p>
        </div>
        <button
          type="button"
          className="form-button"
          onClick={() => setShowCreateModal(true)}
          style={{ display: 'flex', alignItems: 'center', gap: '6px', margin: 0 }}
        >
          <FiPlus /> New Search Alert
        </button>
      </div>

      {showCreateModal && (
        <div
          style={{
            background: '#ffffff',
            borderRadius: '12px',
            padding: '1.5rem',
            border: '1px solid #e2e8f0',
            boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
            marginBottom: '1.5rem',
          }}
        >
          <h3 style={{ margin: '0 0 1rem', fontSize: '1.1rem', color: '#0f172a' }}>
            Create Candidate Search Alert
          </h3>
          <form onSubmit={handleCreateSearch}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Search Name *</label>
                <input
                  type="text"
                  name="name"
                  className="form-input"
                  value={formData.name}
                  onChange={handleInputChange}
                  placeholder="e.g. Python Backend Interns"
                  required
                />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Required Skill</label>
                <input
                  type="text"
                  name="skill"
                  className="form-input"
                  value={formData.skill}
                  onChange={handleInputChange}
                  placeholder="e.g. Python, React"
                />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Location</label>
                <input
                  type="text"
                  name="location"
                  className="form-input"
                  value={formData.location}
                  onChange={handleInputChange}
                  placeholder="e.g. Remote, New York"
                />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">College / University</label>
                <input
                  type="text"
                  name="college"
                  className="form-input"
                  value={formData.college}
                  onChange={handleInputChange}
                  placeholder="e.g. Stanford, MIT"
                />
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', marginBottom: '1rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.9rem', color: '#334155', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  name="alert_enabled"
                  checked={formData.alert_enabled}
                  onChange={handleInputChange}
                />
                Receive automated alerts for new matching candidates
              </label>
            </div>
            <div style={{ display: 'flex', gap: '0.8rem' }}>
              <button type="submit" className="form-button" style={{ margin: 0 }}>
                Save Search
              </button>
              <button
                type="button"
                className="form-button outline"
                onClick={() => setShowCreateModal(false)}
                style={{ margin: 0 }}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="empty-state">Loading saved searches...</div>
      ) : searches.length === 0 ? (
        <div className="empty-state" style={{ padding: '2rem', textAlign: 'center', background: '#f8fafc', borderRadius: '12px', border: '1px dashed #cbd5e1' }}>
          <FiSearch style={{ fontSize: '2rem', color: '#94a3b8', marginBottom: '0.5rem' }} />
          <p style={{ margin: 0, color: '#64748b' }}>
            No saved searches yet. Create one to automatically track matching talent.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {searches.map((search) => (
            <div
              key={search.id}
              style={{
                background: '#ffffff',
                borderRadius: '12px',
                padding: '1.2rem',
                border: '1px solid #e2e8f0',
                boxShadow: '0 2px 6px rgba(0,0,0,0.03)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.8rem' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <h3 style={{ margin: 0, fontSize: '1.15rem', color: '#1e293b' }}>{search.name}</h3>
                    <span
                      style={{
                        fontSize: '0.75rem',
                        padding: '2px 8px',
                        borderRadius: '9999px',
                        fontWeight: '600',
                        backgroundColor: search.alert_enabled ? '#dcfce7' : '#f1f5f9',
                        color: search.alert_enabled ? '#166534' : '#64748b',
                      }}
                    >
                      {search.alert_enabled ? 'Alerts Active' : 'Alerts Paused'}
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.6rem' }}>
                    {search.filters?.skill && (
                      <span className="skill-tag" style={{ fontSize: '0.8rem' }}>
                        Skill: {search.filters.skill}
                      </span>
                    )}
                    {search.filters?.location && (
                      <span className="skill-tag" style={{ fontSize: '0.8rem' }}>
                        <FiMapPin style={{ marginRight: '3px' }} /> {search.filters.location}
                      </span>
                    )}
                    {search.filters?.college && (
                      <span className="skill-tag" style={{ fontSize: '0.8rem' }}>
                        <FiBookOpen style={{ marginRight: '3px' }} /> {search.filters.college}
                      </span>
                    )}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <button
                    type="button"
                    onClick={() => handleToggleAlert(search)}
                    title={search.alert_enabled ? 'Pause alerts' : 'Enable alerts'}
                    style={{
                      padding: '0.4rem 0.8rem',
                      borderRadius: '8px',
                      border: '1px solid #cbd5e1',
                      background: search.alert_enabled ? '#f0fdf4' : '#f8fafc',
                      color: search.alert_enabled ? '#166534' : '#64748b',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      fontSize: '0.85rem',
                      cursor: 'pointer',
                    }}
                  >
                    {search.alert_enabled ? <FiBell /> : <FiBellOff />}
                    {search.alert_enabled ? 'Alert On' : 'Alert Off'}
                  </button>

                  <button
                    type="button"
                    className="form-button outline"
                    onClick={() => handleViewCandidates(search.id)}
                    style={{ margin: 0, padding: '0.4rem 0.8rem', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                  >
                    <FiUsers />
                    {activeSearchId === search.id ? 'Hide Candidates' : 'Find Candidates'}
                  </button>

                  <button
                    type="button"
                    className="delete-button"
                    onClick={() => handleDeleteSearch(search.id)}
                    style={{ margin: 0, padding: '0.4rem 0.6rem' }}
                    title="Delete saved search"
                  >
                    <FiTrash2 />
                  </button>
                </div>
              </div>

              {activeSearchId === search.id && (
                <div style={{ marginTop: '1.2rem', paddingTop: '1.2rem', borderTop: '1px solid #f1f5f9' }}>
                  {loadingCandidates[search.id] ? (
                    <div className="empty-state">Searching matching students...</div>
                  ) : candidates[search.id]?.length === 0 ? (
                    <div className="empty-state" style={{ padding: '1rem', color: '#64748b' }}>
                      No candidates currently match these filters.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
                      {candidates[search.id]?.map((student) => (
                        <div
                          key={student.id}
                          style={{
                            background: '#f8fafc',
                            borderRadius: '8px',
                            padding: '1rem',
                            border: '1px solid #e2e8f0',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'space-between',
                          }}
                        >
                          <div>
                            <h4 style={{ margin: '0 0 0.3rem', color: '#1e293b' }}>{student.name}</h4>
                            {student.college && (
                              <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.3rem' }}>
                                🎓 {student.college}
                              </div>
                            )}
                            {student.location && (
                              <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.5rem' }}>
                                📍 {student.location}
                              </div>
                            )}
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '0.8rem' }}>
                              {student.skills?.slice(0, 4).map((s, idx) => (
                                <span key={idx} className="skill-tag" style={{ fontSize: '0.7rem', padding: '2px 6px' }}>
                                  {typeof s === 'object' ? s.name : s}
                                </span>
                              ))}
                            </div>
                          </div>
                          <Link
                            to={`/profile/${student.id}`}
                            className="form-button outline"
                            style={{ margin: 0, padding: '0.4rem', textAlign: 'center', fontSize: '0.8rem' }}
                          >
                            View Profile
                          </Link>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SavedSearchesSection;
