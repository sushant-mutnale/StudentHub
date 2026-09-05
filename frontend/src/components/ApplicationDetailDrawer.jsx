import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { applicationService } from '../services/applicationService';
import { scorecardService } from '../services/scorecardService';
import { FaTimes, FaStar, FaUser, FaMapMarkerAlt, FaClock, FaPaperPlane, FaCalendarAlt, FaBriefcase, FaExternalLinkAlt } from 'react-icons/fa';
import InterviewModal from './interviews/InterviewModal';

const TABS = ['Fit & Profile', 'Timeline', 'Scorecards', 'Notes & Tags'];

const fitComponents = [
    { name: 'Skill Match', pct: '40%', score: '4.2/5', color: '#3b82f6' },
    { name: 'Proficiency Fit', pct: '20%', score: '3.8/5', color: '#8b5cf6' },
    { name: 'Freshness', pct: '15%', score: '4.0/5', color: '#10b981' },
    { name: 'Location', pct: '10%', score: '4.5/5', color: '#f59e0b' },
    { name: 'Career Alignment', pct: '10%', score: '3.9/5', color: '#ec4899' },
    { name: 'AI Readiness', pct: '5%', score: '4.1/5', color: '#06b6d4' },
];

const matchedSkills = ['Python', 'React'];
const missingSkills = ['Redis', 'Docker'];

const ApplicationDetailDrawer = ({ isOpen, candidate, onClose, pipelineId, jobId, stages, jobTitle }) => {
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState(0);
    const [loading, setLoading] = useState(false);
    const [appData, setAppData] = useState(null);
    const [timeline, setTimeline] = useState(null);
    const [scorecards, setScorecards] = useState([]);
    const [templates, setTemplates] = useState([]);
    const [selectedTemplate, setSelectedTemplate] = useState(null);
    const [scores, setScores] = useState({});
    const [decision, setDecision] = useState('hold');
    const [feedback, setFeedback] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [noteContent, setNoteContent] = useState('');
    const [addingNote, setAddingNote] = useState(false);
    const [tags, setTags] = useState(candidate?.tags || []);
    const [interviewModalOpen, setInterviewModalOpen] = useState(false);

    useEffect(() => {
        if (isOpen && candidate?.application_id) {
            loadApplicationData();
        }
        if (!isOpen) {
            setActiveTab(0);
            setAppData(null);
            setTimeline(null);
            setScorecards([]);
        }
    }, [isOpen, candidate?.application_id]);

    const loadApplicationData = async () => {
        setLoading(true);
        try {
            const [app, tl, sc, tpl] = await Promise.all([
                applicationService.getApplication(candidate.application_id),
                applicationService.getTimeline(candidate.application_id).catch(() => null),
                scorecardService.getApplicationScorecards(candidate.application_id).catch(() => []),
                scorecardService.getTemplates().catch(() => []),
            ]);
            setAppData(app);
            setTimeline(tl);
            setScorecards(Array.isArray(sc) ? sc : (sc?.scorecards || []));
            setTemplates(Array.isArray(tpl) ? tpl : []);
            setTags(app?.tags || candidate?.tags || []);
            if (Array.isArray(tpl) && tpl.length > 0) setSelectedTemplate(tpl[0]);
            else if (tpl?.scorecards && tpl.scorecards.length > 0) setSelectedTemplate(tpl.scorecards[0]);
        } catch (error) {
            console.error('Failed to load application data', error);
        } finally {
            setLoading(false);
        }
    };

    const handleScoreChange = (criteriaName, value) => {
        setScores(prev => ({ ...prev, [criteriaName]: parseInt(value) }));
    };

    const handleScorecardSubmit = async (e) => {
        e.preventDefault();
        if (!selectedTemplate) return;
        setSubmitting(true);
        const criteriaScores = Object.entries(scores).map(([name, score]) => ({
            name,
            score,
            weight: selectedTemplate.criteria.find(c => c.name === name)?.weight || 1,
        }));
        const payload = {
            template_id: selectedTemplate.id,
            scores: criteriaScores,
            decision,
            overall_notes: feedback,
        };
        try {
            await scorecardService.submitScorecard(payload);
            setScores({});
            setFeedback('');
            setDecision('hold');
            const sc = await scorecardService.getApplicationScorecards(candidate.application_id).catch(() => []);
            setScorecards(Array.isArray(sc) ? sc : (sc?.scorecards || []));
        } catch (error) {
            console.error('Failed to submit scorecard', error);
        } finally {
            setSubmitting(false);
        }
    };

    const handleAddNote = async () => {
        if (!noteContent.trim()) return;
        setAddingNote(true);
        try {
            await applicationService.addNote(candidate.application_id, noteContent);
            setNoteContent('');
            const app = await applicationService.getApplication(candidate.application_id);
            setAppData(app);
        } catch (error) {
            console.error('Failed to add note', error);
        } finally {
            setAddingNote(false);
        }
    };

    const handleRemoveTag = async (tag) => {
        try {
            await fetch(`/api/applications/${candidate.application_id}/tags/${encodeURIComponent(tag)}`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
            });
            setTags(prev => prev.filter(t => t !== tag));
        } catch (error) {
            console.error('Failed to remove tag', error);
        }
    };

    const handleReject = async () => {
        const rejectStage = stages.find(s => s.stage_type === 'rejected' || (s.stage_name || '').toLowerCase().includes('reject'));
        if (!rejectStage) {
            alert('No Rejected stage found in this pipeline!');
            return;
        }
        try {
            await applicationService.moveStage(candidate.application_id, rejectStage.stage_id);
            onClose();
        } catch (error) {
            console.error('Failed to reject application', error);
        }
    };

    const handleExtendOffer = async () => {
        const offerStage = stages.find(s => (s.stage_name || '').toLowerCase().includes('offer'));
        if (!offerStage) {
            alert('No Offer stage found in this pipeline!');
            return;
        }
        try {
            await applicationService.moveStage(candidate.application_id, offerStage.stage_id);
            onClose();
        } catch (error) {
            console.error('Failed to extend offer', error);
        }
    };

    if (!isOpen || !candidate) return null;

    const score = candidate.overall_score;
    const scoreLabel = score >= 80 ? 'Strong Fit' : score >= 60 ? 'Good Fit' : score >= 40 ? 'Moderate' : 'Weak Fit';
    const scoreColor = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';
    const stageHistory = appData?.stage_history || timeline?.events || [];
    const notes = appData?.notes || [];

    return (
        <>
            {/* Backdrop */}
            <div
                onClick={onClose}
                style={{
                    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
                    zIndex: 1000, transition: 'opacity 0.3s ease',
                }}
            />

            {/* Drawer */}
            <div
                style={{
                    position: 'fixed', top: 0, right: 0, width: '520px', maxWidth: '95vw',
                    height: '100vh', background: '#fff', zIndex: 1001,
                    boxShadow: '-8px 0 30px rgba(0,0,0,0.15)',
                    display: 'flex', flexDirection: 'column',
                    transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
                    transition: 'transform 0.3s cubic-bezier(0.4,0,0.2,1)',
                }}
            >
                {/* Header */}
                <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid #e5e7eb', background: 'linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                            <div style={{ height: '48px', width: '48px', borderRadius: '50%', background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: '700', fontSize: '1.25rem', flexShrink: 0 }}>
                                {(candidate.student_name || '?').charAt(0).toUpperCase()}
                            </div>
                            <div>
                                <h2 style={{ fontSize: '1.1rem', fontWeight: '700', color: '#1f2937', margin: 0 }}>{candidate.student_name}</h2>
                                <div style={{ fontSize: '0.8rem', color: '#6b7280', marginTop: '2px' }}>{candidate.email}</div>
                                {(jobTitle || candidate.job_title) && (
                                    <div style={{ fontSize: '0.75rem', color: '#3b82f6', fontWeight: '500', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                        <FaBriefcase size={10} /> {jobTitle || candidate.job_title}
                                    </div>
                                )}
                            </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            {score != null && (
                                <span style={{
                                    padding: '4px 12px', borderRadius: '20px', fontSize: '0.75rem',
                                    fontWeight: '600', background: `${scoreColor}15`, color: scoreColor,
                                    border: `1px solid ${scoreColor}30`,
                                }}>
                                    {score}% — {scoreLabel}
                                </span>
                            )}
                            <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', padding: '4px' }}>
                                <FaTimes size={18} />
                            </button>
                        </div>
                    </div>
                    <a
                        href={`/profile/${candidate.student_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ fontSize: '0.8rem', color: '#3b82f6', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                    >
                        View Public Profile <FaExternalLinkAlt size={10} />
                    </a>
                </div>

                {/* Tabs */}
                <div style={{ display: 'flex', borderBottom: '1px solid #e5e7eb', background: '#fafafa' }}>
                    {TABS.map((tab, i) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(i)}
                            style={{
                                flex: 1, padding: '0.75rem 0.5rem', border: 'none', background: 'none',
                                fontSize: '0.8rem', fontWeight: activeTab === i ? '600' : '400',
                                color: activeTab === i ? '#3b82f6' : '#6b7280',
                                borderBottom: activeTab === i ? '2px solid #3b82f6' : '2px solid transparent',
                                cursor: 'pointer', transition: 'all 0.2s',
                            }}
                        >
                            {tab}
                        </button>
                    ))}
                </div>

                {/* Content */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem 1.5rem' }}>
                    {loading && (
                        <div style={{ textAlign: 'center', padding: '2rem', color: '#9ca3af' }}>
                            <div style={{ display: 'inline-block', width: '32px', height: '32px', border: '3px solid #e5e7eb', borderTopColor: '#3b82f6', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
                            <div style={{ marginTop: '0.75rem', fontSize: '0.85rem' }}>Loading details...</div>
                        </div>
                    )}

                    {!loading && activeTab === 0 && (
                        <div>
                            <h3 style={{ fontSize: '0.95rem', fontWeight: '600', color: '#1f2937', marginBottom: '1rem' }}>Shared Fit Score Breakdown</h3>
                            <div style={{ display: 'grid', gap: '0.75rem' }}>
                                {fitComponents.map((fc) => (
                                    <div key={fc.name} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem', background: '#f9fafb', borderRadius: '8px', border: '1px solid #f3f4f6' }}>
                                        <div style={{ width: '100px', fontSize: '0.8rem', fontWeight: '500', color: '#374151' }}>{fc.name}</div>
                                        <div style={{ flex: 1, height: '8px', background: '#e5e7eb', borderRadius: '4px', overflow: 'hidden' }}>
                                            <div style={{ height: '100%', width: `${parseInt(fc.score) / 5 * 100}%`, background: fc.color, borderRadius: '4px', transition: 'width 0.5s ease' }} />
                                        </div>
                                        <div style={{ width: '50px', fontSize: '0.75rem', fontWeight: '600', color: fc.color, textAlign: 'right' }}>{fc.score}</div>
                                        <div style={{ width: '40px', fontSize: '0.65rem', color: '#9ca3af', textAlign: 'right' }}>{fc.pct}</div>
                                    </div>
                                ))}
                            </div>

                            <h3 style={{ fontSize: '0.95rem', fontWeight: '600', color: '#1f2937', marginTop: '1.5rem', marginBottom: '0.75rem' }}>Skills Assessment</h3>
                            <div style={{ marginBottom: '0.75rem' }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: '500', color: '#059669', marginBottom: '0.5rem' }}>Matched Skills</div>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                                    {matchedSkills.map(skill => (
                                        <span key={skill} style={{ padding: '4px 12px', borderRadius: '20px', fontSize: '0.75rem', background: '#ecfdf5', color: '#059669', border: '1px solid #a7f3d0' }}>{skill}</span>
                                    ))}
                                </div>
                            </div>
                            <div>
                                <div style={{ fontSize: '0.75rem', fontWeight: '500', color: '#ef4444', marginBottom: '0.5rem' }}>Missing Skills</div>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                                    {missingSkills.map(skill => (
                                        <span key={skill} style={{ padding: '4px 12px', borderRadius: '20px', fontSize: '0.75rem', background: '#fef2f2', color: '#ef4444', border: '1px solid #fecaca' }}>{skill}</span>
                                    ))}
                                </div>
                            </div>
                            <p style={{ fontSize: '0.7rem', color: '#9ca3af', marginTop: '1rem', fontStyle: 'italic' }}>
                                Detailed scores will populate when the ranked-candidates endpoint is wired.
                            </p>
                        </div>
                    )}

                    {!loading && activeTab === 1 && (
                        <div>
                            <h3 style={{ fontSize: '0.95rem', fontWeight: '600', color: '#1f2937', marginBottom: '1rem' }}>Stage History</h3>
                            {stageHistory.length === 0 ? (
                                <div style={{ textAlign: 'center', padding: '2rem', color: '#9ca3af', fontSize: '0.85rem' }}>Stage history not available</div>
                            ) : (
                                <div style={{ position: 'relative', paddingLeft: '1.5rem' }}>
                                    <div style={{ position: 'absolute', left: '7px', top: '4px', bottom: '4px', width: '2px', background: '#e5e7eb' }} />
                                    {stageHistory.map((entry, idx) => (
                                        <div key={idx} style={{ position: 'relative', marginBottom: '1.25rem', paddingBottom: '0.5rem' }}>
                                            <div style={{ position: 'absolute', left: '-1.5rem', top: '4px', width: '12px', height: '12px', borderRadius: '50%', background: idx === stageHistory.length - 1 ? '#3b82f6' : '#d1d5db', border: '2px solid white', boxShadow: '0 0 0 2px #e5e7eb' }} />
                                            <div style={{ fontSize: '0.85rem', fontWeight: '600', color: '#1f2937' }}>{entry.stage_name || entry.stage || 'Unknown'}</div>
                                            <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '2px' }}>
                                                {entry.changed_by && <span>By {entry.changed_by} &middot; </span>}
                                                {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : entry.date || ''}
                                            </div>
                                            {entry.reason && (
                                                <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '4px', fontStyle: 'italic' }}>"{entry.reason}"</div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {!loading && activeTab === 2 && (
                        <div>
                            <h3 style={{ fontSize: '0.95rem', fontWeight: '600', color: '#1f2937', marginBottom: '1rem' }}>Submit Scorecard</h3>
                            {!selectedTemplate ? (
                                <div style={{ padding: '1rem', background: '#f9fafb', borderRadius: '8px', color: '#9ca3af', fontSize: '0.85rem', textAlign: 'center' }}>No templates available</div>
                            ) : (
                                <form onSubmit={handleScorecardSubmit} style={{ marginBottom: '1.5rem' }}>
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>Template</label>
                                        <select
                                            value={selectedTemplate.id}
                                            onChange={(e) => {
                                                const t = templates.find(t => t.id === e.target.value);
                                                if (t) { setSelectedTemplate(t); setScores({}); }
                                            }}
                                            style={{ width: '100%', padding: '0.5rem', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '0.85rem' }}
                                        >
                                            {templates.map(t => (
                                                <option key={t.id} value={t.id}>{t.name}</option>
                                            ))}
                                        </select>
                                    </div>

                                    <div style={{ display: 'grid', gap: '1rem', marginBottom: '1rem' }}>
                                        {selectedTemplate.criteria.map((criterion) => (
                                            <div key={criterion.name} style={{ padding: '0.75rem', background: '#f9fafb', borderRadius: '8px', border: '1px solid #f3f4f6' }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                                                    <span style={{ fontSize: '0.8rem', fontWeight: '500', color: '#1f2937' }}>{criterion.name}</span>
                                                    <span style={{ fontSize: '0.7rem', color: '#9ca3af' }}>Weight: {criterion.weight}x</span>
                                                </div>
                                                {criterion.description && (
                                                    <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.5rem' }}>{criterion.description}</div>
                                                )}
                                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                                    {[1, 2, 3, 4, 5].map(rating => (
                                                        <button
                                                            key={rating}
                                                            type="button"
                                                            onClick={() => handleScoreChange(criterion.name, rating)}
                                                            style={{
                                                                width: '36px', height: '36px', borderRadius: '50%', border: '2px solid',
                                                                borderColor: scores[criterion.name] === rating ? '#3b82f6' : '#e5e7eb',
                                                                background: scores[criterion.name] === rating ? '#3b82f6' : 'white',
                                                                color: scores[criterion.name] === rating ? 'white' : '#6b7280',
                                                                fontWeight: '600', fontSize: '0.8rem', cursor: 'pointer',
                                                                transition: 'all 0.15s',
                                                            }}
                                                        >
                                                            {rating}
                                                        </button>
                                                    ))}
                                                </div>
                                            </div>
                                        ))}
                                    </div>

                                    <div style={{ marginBottom: '1rem' }}>
                                        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>Decision</label>
                                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                                            {['pass', 'hold', 'reject'].map(d => (
                                                <button
                                                    key={d}
                                                    type="button"
                                                    onClick={() => setDecision(d)}
                                                    style={{
                                                        flex: 1, padding: '0.5rem', borderRadius: '6px', border: '2px solid',
                                                        borderColor: decision === d
                                                            ? (d === 'pass' ? '#10b981' : d === 'reject' ? '#ef4444' : '#f59e0b')
                                                            : '#e5e7eb',
                                                        background: decision === d
                                                            ? (d === 'pass' ? '#ecfdf5' : d === 'reject' ? '#fef2f2' : '#fffbeb')
                                                            : 'white',
                                                        color: decision === d
                                                            ? (d === 'pass' ? '#059669' : d === 'reject' ? '#dc2626' : '#d97706')
                                                            : '#6b7280',
                                                        fontWeight: '600', fontSize: '0.8rem', cursor: 'pointer', textTransform: 'capitalize',
                                                    }}
                                                >
                                                    {d}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    <div style={{ marginBottom: '1rem' }}>
                                        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem' }}>Overall Notes</label>
                                        <textarea
                                            value={feedback}
                                            onChange={(e) => setFeedback(e.target.value)}
                                            placeholder="Write your evaluation notes..."
                                            rows={3}
                                            style={{ width: '100%', padding: '0.5rem', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '0.85rem', resize: 'vertical' }}
                                        />
                                    </div>

                                    <button
                                        type="submit"
                                        disabled={submitting}
                                        style={{
                                            width: '100%', padding: '0.6rem', borderRadius: '6px', border: 'none',
                                            background: '#3b82f6', color: 'white', fontWeight: '600', fontSize: '0.85rem',
                                            cursor: submitting ? 'not-allowed' : 'pointer', opacity: submitting ? 0.6 : 1,
                                        }}
                                    >
                                        {submitting ? 'Submitting...' : 'Submit Scorecard'}
                                    </button>
                                </form>
                            )}

                            <h3 style={{ fontSize: '0.95rem', fontWeight: '600', color: '#1f2937', marginBottom: '0.75rem' }}>Submitted Scorecards</h3>
                            {scorecards.length === 0 ? (
                                <div style={{ padding: '1rem', background: '#f9fafb', borderRadius: '8px', color: '#9ca3af', fontSize: '0.85rem', textAlign: 'center' }}>No scorecards yet</div>
                            ) : (
                                <div style={{ display: 'grid', gap: '0.5rem' }}>
                                    {scorecards.map((sc, idx) => (
                                        <div key={sc.id || idx} style={{ padding: '0.75rem', background: '#f9fafb', borderRadius: '8px', border: '1px solid #f3f4f6', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <div>
                                                <div style={{ fontSize: '0.85rem', fontWeight: '500', color: '#1f2937' }}>{sc.template_name || sc.template_id || 'Scorecard'}</div>
                                                <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '2px' }}>
                                                    {sc.created_at ? new Date(sc.created_at).toLocaleString() : ''}
                                                </div>
                                            </div>
                                            <span style={{
                                                padding: '2px 10px', borderRadius: '20px', fontSize: '0.7rem', fontWeight: '600',
                                                background: sc.decision === 'pass' ? '#ecfdf5' : sc.decision === 'reject' ? '#fef2f2' : '#fffbeb',
                                                color: sc.decision === 'pass' ? '#059669' : sc.decision === 'reject' ? '#dc2626' : '#d97706',
                                                textTransform: 'capitalize',
                                            }}>
                                                {sc.decision}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {!loading && activeTab === 3 && (
                        <div>
                            <h3 style={{ fontSize: '0.95rem', fontWeight: '600', color: '#1f2937', marginBottom: '0.75rem' }}>Tags</h3>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1.5rem' }}>
                                {(tags || []).length === 0 ? (
                                    <span style={{ fontSize: '0.8rem', color: '#9ca3af' }}>No tags</span>
                                ) : (
                                    tags.map(tag => (
                                        <span key={tag} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 12px', borderRadius: '20px', fontSize: '0.75rem', background: '#eff6ff', color: '#3b82f6', border: '1px solid #bfdbfe' }}>
                                            {tag}
                                            <button onClick={() => handleRemoveTag(tag)} style={{ background: 'none', border: 'none', color: '#3b82f6', cursor: 'pointer', padding: 0, fontSize: '0.8rem', lineHeight: 1 }}>
                                                &times;
                                            </button>
                                        </span>
                                    ))
                                )}
                            </div>

                            <h3 style={{ fontSize: '0.95rem', fontWeight: '600', color: '#1f2937', marginBottom: '0.75rem' }}>Add Note</h3>
                            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
                                <textarea
                                    value={noteContent}
                                    onChange={(e) => setNoteContent(e.target.value)}
                                    placeholder="Add a note about this candidate..."
                                    rows={3}
                                    style={{ flex: 1, padding: '0.5rem', border: '1px solid #d1d5db', borderRadius: '6px', fontSize: '0.85rem', resize: 'vertical' }}
                                />
                            </div>
                            <button
                                onClick={handleAddNote}
                                disabled={addingNote || !noteContent.trim()}
                                style={{
                                    width: '100%', padding: '0.6rem', borderRadius: '6px', border: 'none',
                                    background: '#3b82f6', color: 'white', fontWeight: '600', fontSize: '0.85rem',
                                    cursor: addingNote || !noteContent.trim() ? 'not-allowed' : 'pointer',
                                    opacity: addingNote || !noteContent.trim() ? 0.6 : 1, marginBottom: '1.5rem',
                                }}
                            >
                                {addingNote ? 'Adding...' : 'Add Note'}
                            </button>

                            <h3 style={{ fontSize: '0.95rem', fontWeight: '600', color: '#1f2937', marginBottom: '0.75rem' }}>Notes</h3>
                            {notes.length === 0 ? (
                                <div style={{ padding: '1rem', background: '#f9fafb', borderRadius: '8px', color: '#9ca3af', fontSize: '0.85rem', textAlign: 'center' }}>No notes yet</div>
                            ) : (
                                <div style={{ display: 'grid', gap: '0.75rem' }}>
                                    {notes.map((note, idx) => (
                                        <div key={note.id || idx} style={{ padding: '0.75rem', background: '#f9fafb', borderRadius: '8px', border: '1px solid #f3f4f6' }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                                                <span style={{ fontSize: '0.8rem', fontWeight: '500', color: '#1f2937' }}>{note.author_name || 'Recruiter'}</span>
                                                <span style={{ fontSize: '0.7rem', color: '#9ca3af' }}>{note.created_at ? new Date(note.created_at).toLocaleString() : ''}</span>
                                            </div>
                                            <div style={{ fontSize: '0.8rem', color: '#374151', lineHeight: '1.5' }}>{note.content}</div>
                                            {note.is_private && (
                                                <span style={{ fontSize: '0.65rem', color: '#9ca3af', fontStyle: 'italic' }}>Private</span>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Quick Action Bar */}
                <div style={{ padding: '1rem 1.5rem', borderTop: '1px solid #e5e7eb', background: '#fafafa', display: 'flex', gap: '0.75rem' }}>
                    <button
                        onClick={() => setInterviewModalOpen(true)}
                        style={{
                            flex: 1, padding: '0.6rem', borderRadius: '8px', border: '1px solid #bfdbfe',
                            background: 'white', color: '#3b82f6', fontWeight: '600', fontSize: '0.8rem',
                            cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                        }}
                    >
                        <FaCalendarAlt size={12} /> Schedule Interview
                    </button>
                    <button
                        onClick={handleExtendOffer}
                        style={{
                            flex: 1, padding: '0.6rem', borderRadius: '8px', border: '1px solid #a7f3d0',
                            background: 'white', color: '#059669', fontWeight: '600', fontSize: '0.8rem',
                            cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                        }}
                    >
                        <FaPaperPlane size={12} /> Extend Offer
                    </button>
                    <button
                        onClick={handleReject}
                        style={{
                            flex: 1, padding: '0.6rem', borderRadius: '8px', border: '1px solid #fecaca',
                            background: 'white', color: '#ef4444', fontWeight: '600', fontSize: '0.8rem',
                            cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                        }}
                    >
                        <FaTimes size={12} /> Reject Application
                    </button>
                </div>
            </div>

            {/* Interview Modal */}
            {interviewModalOpen && (
                <InterviewModal
                    isOpen={interviewModalOpen}
                    onClose={() => setInterviewModalOpen(false)}
                    candidateId={candidate.student_id}
                    jobId={jobId}
                />
            )}

            <style>{`
                @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
            `}</style>
        </>
    );
};

export default ApplicationDetailDrawer;
