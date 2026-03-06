import React, { useState, useEffect } from 'react';

import { useNavigate, useSearchParams } from 'react-router-dom';
import { pipelineService } from '../services/pipelineService';
import { applicationService } from '../services/applicationService';
import { jobService } from '../services/jobService';
import { FaUser, FaEllipsisV, FaBriefcase, FaCalendarAlt, FaEnvelope } from 'react-icons/fa';
import SidebarLeft from './SidebarLeft';
import '../App.css';

const ApplicationPipeline = () => {
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();
    const urlJobId = searchParams.get('jobId');

    const [pipeline, setPipeline] = useState(null);
    const [stages, setStages] = useState([]);
    const [jobs, setJobs] = useState([]);
    const [selectedJobId, setSelectedJobId] = useState(urlJobId || null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadInitialData();
    }, []);

    useEffect(() => {
        if (selectedJobId && pipeline) {
            loadBoard(pipeline.id || pipeline._id, selectedJobId);
        }
    }, [selectedJobId, pipeline]);

    const loadInitialData = async () => {
        try {
            const activePipeline = await pipelineService.getActivePipeline();
            setPipeline(activePipeline);

            const myJobs = await jobService.getMyJobs();
            setJobs(myJobs);

            if (myJobs.length > 0) {
                if (urlJobId && myJobs.some(j => j.id === urlJobId)) {
                    setSelectedJobId(urlJobId);
                } else {
                    setSelectedJobId(myJobs[0].id);
                    setSearchParams({ jobId: myJobs[0].id }, { replace: true });
                }
            } else {
                setLoading(false);
            }
        } catch (error) {
            console.error("Failed to load pipeline data", error);
            setLoading(false);
        }
    };

    const loadBoard = async (pipelineId, jobId) => {
        setLoading(true);
        try {
            const boardData = await pipelineService.getPipelineBoard(pipelineId, jobId);
            setStages(boardData.columns);
        } catch (error) {
            console.error("Failed to load board", error);
        } finally {
            setLoading(false);
        }
    };

    const getStageStyle = (name) => {
        const lower = (name || '').toLowerCase();
        if (lower.includes('applied')) return { color: '#3b82f6', bgColor: 'rgba(59,130,246,0.08)', borderColor: '#3b82f6', emoji: '📥', description: 'New applications land here' };
        if (lower.includes('screen')) return { color: '#8b5cf6', bgColor: 'rgba(139,92,246,0.08)', borderColor: '#8b5cf6', emoji: '🔍', description: 'Resume screening & initial assessment' };
        if (lower.includes('interview')) return { color: '#f59e0b', bgColor: 'rgba(245,158,11,0.08)', borderColor: '#f59e0b', emoji: '🎙️', description: 'In-person or AI mock interviews' };
        if (lower.includes('offer')) return { color: '#10b981', bgColor: 'rgba(16,185,129,0.08)', borderColor: '#10b981', emoji: '📝', description: 'Offer extended to candidate' };
        if (lower.includes('hired')) return { color: '#059669', bgColor: 'rgba(5,150,105,0.10)', borderColor: '#059669', emoji: '🎉', description: 'Candidate accepted & onboarded' };
        if (lower.includes('reject')) return { color: '#ef4444', bgColor: 'rgba(239,68,68,0.08)', borderColor: '#ef4444', emoji: '❌', description: 'Application declined' };
        if (lower.includes('withdraw')) return { color: '#6b7280', bgColor: 'rgba(107,114,128,0.08)', borderColor: '#6b7280', emoji: '🚪', description: 'Candidate withdrew' };
        return { color: '#6b7280', bgColor: 'rgba(107,114,128,0.06)', borderColor: '#9ca3af', emoji: '📋', description: '' };
    };

    const getScoreStyle = (score) => {
        if (score >= 80) return { background: 'rgba(16,185,129,0.1)', color: '#059669' };
        if (score >= 60) return { background: 'rgba(245,158,11,0.1)', color: '#d97706' };
        return { background: 'rgba(239,68,68,0.1)', color: '#dc2626' };
    };

    if (loading && !pipeline) return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            <div className="animate-spin" style={{ borderRadius: '50%', height: '48px', width: '48px', borderBottom: '2px solid #3b82f6' }}></div>
        </div>
    );
    if (!pipeline) return <div style={{ padding: '2rem', textAlign: 'center', color: '#6b7280' }}>No active pipeline found.</div>;
    if (jobs.length === 0) return <div style={{ padding: '2rem', textAlign: 'center', color: '#6b7280' }}>No jobs found. Post a job to see the candidate pipeline.</div>;

    return (
        <div className="dashboard-container">
            <SidebarLeft />
            <div className="dashboard-main animate-fade-in" style={{ padding: 0, height: '100%', display: 'flex', flexDirection: 'column', background: '#f9fafb', overflow: 'hidden' }}>
                {/* Header */}
                <div style={{ padding: '1rem', borderBottom: '1px solid #e5e7eb', background: 'white', boxShadow: '0 1px 2px rgba(0,0,0,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', zIndex: 10, position: 'relative' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                        <h2 style={{ fontSize: '1.25rem', fontWeight: '700', background: 'var(--gradient-primary)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
                            {pipeline.name}
                        </h2>
                        <div style={{ display: 'flex', alignItems: 'center', background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: '8px', padding: '6px 12px' }}>
                            <FaBriefcase style={{ color: '#3b82f6', marginRight: '8px' }} />
                            <select
                                style={{ background: 'transparent', border: 'none', fontSize: '0.875rem', fontWeight: '500', color: '#374151', cursor: 'pointer', outline: 'none' }}
                                value={selectedJobId || ''}
                                onChange={(e) => {
                                    setSelectedJobId(e.target.value);
                                    setSearchParams({ jobId: e.target.value }, { replace: true });
                                }}
                            >
                                {jobs.map(job => (
                                    <option key={job.id} value={job.id}>{job.title}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                    <div style={{ fontSize: '0.875rem', color: '#6b7280', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ display: 'flex', height: '8px', width: '8px', borderRadius: '50%', background: '#10b981' }}></span>
                        Live Pipeline
                    </div>
                </div>

                {/* Kanban Board */}
                <div style={{ flex: 1, overflowX: 'auto', padding: '1.5rem', background: 'linear-gradient(135deg, #f9fafb 0%, #eef2ff 100%)' }}>
                    <div style={{ display: 'flex', height: '100%', gap: '1.5rem' }}>
                        {stages.map((stage, stageIdx) => {
                            const stStyle = getStageStyle(stage.stage_name);
                            return (
                                <div
                                    key={stage.stage_id}
                                    style={{
                                        width: '300px', flexShrink: 0, display: 'flex', flexDirection: 'column',
                                        background: 'rgba(249,250,251,0.7)',
                                        borderRadius: '12px', maxHeight: '100%', transition: 'background 0.2s ease',
                                        animation: `fadeIn 0.5s ease-out ${stageIdx * 0.1}s backwards`
                                    }}
                                >
                                    {/* Column Header */}
                                    <div title={stStyle.description} style={{ padding: '1rem', fontWeight: '600', background: 'white', borderRadius: '12px 12px 0 0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: `4px solid ${stStyle.borderColor}` }}>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                            <span style={{ textTransform: 'uppercase', fontSize: '0.7rem', letterSpacing: '0.05em', color: stStyle.color, display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                <span>{stStyle.emoji}</span> {stage.stage_name}
                                            </span>
                                            {stStyle.description && (
                                                <span style={{ fontSize: '0.7rem', color: '#9ca3af', fontWeight: '400' }}>{stStyle.description}</span>
                                            )}
                                        </div>
                                        <span style={{ background: `${stStyle.color}15`, color: stStyle.color, padding: '2px 10px', borderRadius: '20px', fontSize: '0.75rem', fontWeight: '700' }}>
                                            {stage.candidates.length}
                                        </span>
                                    </div>

                                    {/* Column Content */}
                                    <div className="custom-scrollbar" style={{ padding: '0.75rem', flex: 1, overflowY: 'auto' }}>
                                        {stage.candidates.map((candidate) => (
                                            <div
                                                key={candidate.application_id}
                                                style={{
                                                    background: 'white', padding: '1rem', marginBottom: '0.75rem', borderRadius: '10px',
                                                    border: '1px solid #f0f0f0',
                                                    boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                                                    transition: 'box-shadow 0.2s, border 0.2s'
                                                }}
                                            >
                                                {/* Candidate Header */}
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                                        <div style={{ height: '32px', width: '32px', borderRadius: '50%', background: 'linear-gradient(135deg, #dbeafe, #e0e7ff)', color: '#3b82f6', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: '700', fontSize: '0.75rem' }}>
                                                            {candidate.student_name.charAt(0)}
                                                        </div>
                                                        <div>
                                                            <h4 style={{ fontWeight: '600', color: '#1f2937', fontSize: '0.875rem', margin: 0 }}>{candidate.student_name}</h4>
                                                            {candidate.email && (
                                                                <div style={{ fontSize: '0.7rem', color: '#9ca3af', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                                                    <FaEnvelope size={10} />{candidate.email}
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>
                                                    <button style={{ background: 'none', border: 'none', color: '#d1d5db', cursor: 'pointer' }}>
                                                        <FaEllipsisV size={12} />
                                                    </button>
                                                </div>

                                                {/* Applied Date */}
                                                <div style={{ marginBottom: '0.75rem' }}>
                                                    <div style={{ fontSize: '0.75rem', color: '#6b7280', background: '#f9fafb', padding: '6px 8px', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                        <FaCalendarAlt style={{ color: '#9ca3af' }} />
                                                        Applied: {new Date(candidate.applied_at).toLocaleDateString()}
                                                    </div>
                                                </div>

                                                {/* Score + Actions */}
                                                <div style={{ borderTop: '1px solid #f3f4f6', paddingTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                        {candidate.overall_score ? (
                                                            <div style={{ display: 'flex', alignItems: 'center', fontSize: '0.75rem', fontWeight: '600', padding: '3px 8px', borderRadius: '20px', ...getScoreStyle(candidate.overall_score) }}>
                                                                <FaUser style={{ marginRight: '4px' }} size={10} />
                                                                {candidate.overall_score}% Match
                                                            </div>
                                                        ) : (
                                                            <span style={{ fontSize: '0.75rem', color: '#9ca3af', fontStyle: 'italic' }}>Pending Score</span>
                                                        )}
                                                        <div
                                                            style={{ fontSize: '0.75rem', color: '#3b82f6', fontWeight: '500', cursor: 'pointer', padding: '4px' }}
                                                            onClick={() => navigate(`/profile/${candidate.student_id}`)}
                                                        >
                                                            View Profile
                                                        </div>
                                                    </div>
                                                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', justifyContent: 'flex-start' }}>
                                                        <button
                                                            title="Quick Reject"
                                                            style={{ background: 'white', border: '1px solid #fca5a5', color: '#ef4444', cursor: 'pointer', padding: '4px 8px', borderRadius: '4px', display: 'flex', alignItems: 'center', transition: 'background 0.2s', ':hover': { background: '#fef2f2' } }}
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                const rejectStage = stages.find(s => s.stage_type === 'rejected' || (s.stage_name || '').toLowerCase().includes('reject'));
                                                                if (rejectStage) {
                                                                    applicationService.moveStage(candidate.application_id, rejectStage.stage_id)
                                                                        .then(() => loadBoard(pipeline.id || pipeline._id, selectedJobId))
                                                                        .catch(err => console.error("Failed to reject", err));
                                                                } else {
                                                                    alert("No Rejected stage found in this pipeline!");
                                                                }
                                                            }}
                                                        >
                                                            <span style={{ fontSize: '0.75rem', fontWeight: '600' }}>❌ Reject</span>
                                                        </button>

                                                        {stageIdx < stages.length - 1 && !(stage.stage_name || '').toLowerCase().includes('reject') && !(stage.stage_name || '').toLowerCase().includes('hired') && (
                                                            <button
                                                                title="Advance to Next Stage"
                                                                style={{ background: '#eff6ff', border: '1px solid #bfdbfe', color: '#3b82f6', cursor: 'pointer', padding: '4px 10px', borderRadius: '4px', display: 'flex', alignItems: 'center', flex: 1, justifyContent: 'center', transition: 'background 0.2s', ':hover': { background: '#dbeafe' } }}
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    const nextStage = stages[stageIdx + 1];
                                                                    if (nextStage) {
                                                                        applicationService.moveStage(candidate.application_id, nextStage.stage_id)
                                                                            .then(() => loadBoard(pipeline.id || pipeline._id, selectedJobId))
                                                                            .catch(err => console.error("Failed to advance", err));
                                                                    }
                                                                }}
                                                            >
                                                                <span style={{ fontSize: '0.75rem', fontWeight: '600' }}>Advance ➔</span>
                                                            </button>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ApplicationPipeline;
