import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { resumeService } from '../services/resumeService';
import SidebarLeft from './SidebarLeft';
import { FiUpload, FiFile, FiCheck, FiAlertCircle, FiRefreshCw, FiLoader, FiArrowRight, FiTarget, FiBook, FiBriefcase, FiStar, FiAward } from 'react-icons/fi';
import '../App.css';

const ResumeUpload = () => {
    const navigate = useNavigate();
    const { user, refreshUser } = useAuth();
    const fileInputRef = useRef(null);

    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
    const [dragOver, setDragOver] = useState(false);

    const handleFileSelect = (e) => {
        const selectedFile = e.target.files?.[0];
        if (selectedFile) {
            validateAndSetFile(selectedFile);
        }
    };

    const validateAndSetFile = (selectedFile) => {
        const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
        if (!validTypes.includes(selectedFile.type)) {
            setError('Please upload a PDF or DOCX file');
            return;
        }
        if (selectedFile.size > 5 * 1024 * 1024) {
            setError('File size must be less than 5MB');
            return;
        }
        setFile(selectedFile);
        setError('');
        setResult(null);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setDragOver(false);
        const droppedFile = e.dataTransfer.files?.[0];
        if (droppedFile) {
            validateAndSetFile(droppedFile);
        }
    };

    const handleUpload = async () => {
        if (!file) return;

        setLoading(true);
        setError('');

        try {
            const data = await resumeService.uploadResume(file);
            setResult(data);
            await refreshUser();
        } catch (err) {
            setError(err.message || 'Failed to parse resume');
        } finally {
            setLoading(false);
        }
    };

    const handleRecalculate = async () => {
        setLoading(true);
        try {
            await resumeService.recalculate();
            await refreshUser();
            setResult({ ...result, recalculated: true });
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (!user) return null;

    return (
        <div className="dashboard-container">
            <SidebarLeft />
            <div className="dashboard-main">
                <div className="dashboard-header animate-fade-in">
                    <h1 className="dashboard-title" style={{
                        background: 'var(--gradient-primary)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        backgroundClip: 'text'
                    }}>Resume Analysis</h1>
                </div>

                <div className="dashboard-content">
                    {/* Upload Section */}
                    <div className="glass-card animate-fade-in-up" style={{
                        marginBottom: '2rem',
                        padding: '2rem',
                        borderRadius: 'var(--radius-lg)',
                        position: 'relative',
                        overflow: 'hidden'
                    }}>
                        {/* Decorative background */}
                        <div style={{
                            position: 'absolute',
                            top: '-40px',
                            right: '-40px',
                            width: '150px',
                            height: '150px',
                            background: 'radial-gradient(circle, rgba(102, 126, 234, 0.15) 0%, transparent 70%)',
                            borderRadius: '50%'
                        }} />

                        <h3 style={{
                            marginBottom: '1.5rem',
                            color: 'var(--color-text)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                            fontSize: '1.15rem'
                        }}>
                            <span style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                width: '36px',
                                height: '36px',
                                background: 'var(--gradient-primary)',
                                borderRadius: 'var(--radius-md)',
                                color: 'white'
                            }}>
                                <FiUpload size={18} />
                            </span>
                            Upload Your Resume
                        </h3>

                        {/* Drop Zone */}
                        <div
                            className={`drop-zone ${dragOver ? 'active' : ''} interactive-card`}
                            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                            onDragLeave={() => setDragOver(false)}
                            onDrop={handleDrop}
                            onClick={() => fileInputRef.current?.click()}
                            style={{
                                padding: '3.5rem 2rem',
                                textAlign: 'center',
                                position: 'relative',
                                overflow: 'hidden'
                            }}
                        >
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".pdf,.docx"
                                onChange={handleFileSelect}
                                style={{ display: 'none' }}
                            />

                            {/* Animated icon wrapper */}
                            <div className={dragOver ? 'animate-bounce-in' : 'animate-float'} style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                width: '80px',
                                height: '80px',
                                background: dragOver ? 'var(--gradient-primary)' : 'var(--color-bg-alt)',
                                borderRadius: '50%',
                                marginBottom: '1.5rem',
                                transition: 'var(--transition-normal)',
                                boxShadow: dragOver ? 'var(--shadow-glow)' : 'none'
                            }}>
                                <FiFile size={36} style={{
                                    color: dragOver ? 'white' : 'var(--color-text-muted)',
                                    transition: 'var(--transition-normal)'
                                }} />
                            </div>

                            <p style={{
                                color: 'var(--color-text)',
                                fontSize: '1.1rem',
                                marginBottom: '0.5rem',
                                fontWeight: '500'
                            }}>
                                Drag & drop your resume or{' '}
                                <span style={{
                                    color: 'var(--color-primary)',
                                    fontWeight: '600'
                                }}>click to browse</span>
                            </p>
                            <p style={{
                                fontSize: '0.9rem',
                                color: 'var(--color-text-muted)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '1rem'
                            }}>
                                <span style={{
                                    padding: '0.3rem 0.75rem',
                                    background: 'rgba(102, 126, 234, 0.1)',
                                    borderRadius: 'var(--radius-full)',
                                    fontSize: '0.8rem',
                                    fontWeight: '500'
                                }}>PDF</span>
                                <span style={{
                                    padding: '0.3rem 0.75rem',
                                    background: 'rgba(102, 126, 234, 0.1)',
                                    borderRadius: 'var(--radius-full)',
                                    fontSize: '0.8rem',
                                    fontWeight: '500'
                                }}>DOCX</span>
                                <span style={{ color: 'var(--color-text-muted)' }}>Max 5MB</span>
                            </p>
                        </div>

                        {/* File Selected */}
                        {file && (
                            <div className="animate-fade-in-up" style={{
                                marginTop: '1.5rem',
                                padding: '1.25rem 1.5rem',
                                background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(37, 99, 235, 0.08) 100%)',
                                border: '1px solid rgba(59, 130, 246, 0.2)',
                                borderRadius: 'var(--radius-md)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                gap: '1rem'
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                    <div style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        width: '44px',
                                        height: '44px',
                                        background: 'var(--gradient-primary)',
                                        borderRadius: 'var(--radius-md)',
                                        color: 'white'
                                    }}>
                                        <FiFile size={20} />
                                    </div>
                                    <div>
                                        <div style={{ fontWeight: '600', color: 'var(--color-text)' }}>{file.name}</div>
                                        <div style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                                            {(file.size / 1024).toFixed(1)} KB
                                        </div>
                                    </div>
                                </div>
                                <button
                                    onClick={handleUpload}
                                    disabled={loading}
                                    className="btn-glow"
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.5rem',
                                        padding: '0.875rem 1.75rem',
                                        background: 'var(--gradient-primary)',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: 'var(--radius-md)',
                                        fontWeight: '600',
                                        cursor: loading ? 'not-allowed' : 'pointer',
                                        opacity: loading ? 0.7 : 1,
                                        boxShadow: 'var(--shadow-md)'
                                    }}
                                >
                                    {loading ? (
                                        <>
                                            <FiLoader className="animate-spin" size={18} />
                                            Analyzing...
                                        </>
                                    ) : (
                                        <>
                                            <FiUpload size={18} />
                                            Analyze Resume
                                        </>
                                    )}
                                </button>
                            </div>
                        )}

                        {/* Error Message */}
                        {error && (
                            <div className="animate-fade-in" style={{
                                marginTop: '1.25rem',
                                padding: '1rem 1.25rem',
                                background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.08) 0%, rgba(220, 38, 38, 0.08) 100%)',
                                border: '1px solid rgba(239, 68, 68, 0.2)',
                                borderRadius: 'var(--radius-md)',
                                color: 'var(--color-danger)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.75rem',
                                fontWeight: '500'
                            }}>
                                <FiAlertCircle size={20} />
                                {error}
                            </div>
                        )}
                    </div>

                    {/* Results Section */}
                    {result && (
                        <div className="glass-card animate-fade-in-up delay-100" style={{
                            padding: '2rem',
                            borderRadius: 'var(--radius-lg)'
                        }}>
                            {/* Success Header */}
                            <div style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'flex-start',
                                marginBottom: '2rem',
                                paddingBottom: '1.5rem',
                                borderBottom: '1px solid var(--color-border-light)'
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                    <div style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        width: '48px',
                                        height: '48px',
                                        background: 'var(--gradient-success)',
                                        borderRadius: '50%',
                                        boxShadow: 'var(--shadow-glow-success)'
                                    }}>
                                        <FiCheck size={24} color="white" />
                                    </div>
                                    <div>
                                        <h3 style={{
                                            color: 'var(--color-text)',
                                            margin: 0,
                                            fontSize: '1.25rem'
                                        }}>Resume Parsed Successfully</h3>
                                        <p style={{
                                            color: 'var(--color-text-muted)',
                                            margin: 0,
                                            fontSize: '0.9rem',
                                            marginTop: '0.25rem'
                                        }}>Your skills and experience have been extracted</p>
                                    </div>
                                </div>
                                <button
                                    onClick={handleRecalculate}
                                    disabled={loading}
                                    className="btn-glow hover-lift"
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.5rem',
                                        padding: '0.75rem 1.25rem',
                                        background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: 'var(--radius-md)',
                                        fontWeight: '600',
                                        cursor: loading ? 'not-allowed' : 'pointer',
                                        boxShadow: 'var(--shadow-md)'
                                    }}
                                >
                                    <FiRefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                                    Recalculate AI Profile
                                </button>
                            </div>

                            {/* AI Feedback Section */}
                            {result.feedback && (
                                <div className="animate-fade-in-up">
                                    {/* Summary */}
                                    {result.feedback.summary && (
                                        <div style={{
                                            padding: '1.5rem',
                                            background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(37, 99, 235, 0.08) 100%)',
                                            borderRadius: 'var(--radius-lg)',
                                            marginBottom: '2rem',
                                            borderLeft: '4px solid var(--color-info)'
                                        }}>
                                            <h4 style={{
                                                color: 'var(--color-info)',
                                                marginBottom: '0.75rem',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '0.5rem'
                                            }}>
                                                <FiStar size={18} />
                                                AI Executive Summary
                                            </h4>
                                            <p style={{
                                                color: 'var(--color-text)',
                                                lineHeight: '1.7',
                                                margin: 0
                                            }}>{result.feedback.summary}</p>
                                        </div>
                                    )}

                                    {/* Ratings */}
                                    {result.feedback.rating && (
                                        <div style={{ marginBottom: '2rem' }} className="animate-fade-in-up delay-100">
                                            <h4 style={{
                                                marginBottom: '1.25rem',
                                                color: 'var(--color-text)',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '0.75rem'
                                            }}>
                                                <span style={{
                                                    display: 'inline-flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    padding: '0.5rem 1rem',
                                                    background: 'var(--gradient-primary)',
                                                    color: 'white',
                                                    borderRadius: 'var(--radius-full)',
                                                    fontWeight: '700',
                                                    fontSize: '1.1rem'
                                                }}>
                                                    {result.feedback.rating.overall}/10
                                                </span>
                                                Overall Score
                                            </h4>
                                            <div style={{
                                                display: 'grid',
                                                gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
                                                gap: '1rem'
                                            }}>
                                                {result.feedback.rating.breakdown.map((item, idx) => {
                                                    const scoreColor = item.score >= 8 ? 'var(--color-success)' :
                                                        item.score >= 6 ? 'var(--color-warning)' : 'var(--color-danger)';
                                                    return (
                                                        <div
                                                            key={idx}
                                                            className="interactive-card animate-scale-in"
                                                            style={{
                                                                padding: '1.25rem',
                                                                background: 'var(--color-bg-alt)',
                                                                border: '1px solid var(--color-border-light)',
                                                                borderRadius: 'var(--radius-md)',
                                                                animationDelay: `${idx * 80}ms`
                                                            }}
                                                        >
                                                            <div style={{
                                                                fontSize: '0.85rem',
                                                                color: 'var(--color-text-muted)',
                                                                marginBottom: '0.5rem',
                                                                textTransform: 'uppercase',
                                                                letterSpacing: '0.5px'
                                                            }}>{item.aspect}</div>
                                                            <div style={{
                                                                fontSize: '1.5rem',
                                                                fontWeight: '700',
                                                                color: scoreColor
                                                            }}>
                                                                {item.score}
                                                                <span style={{
                                                                    fontSize: '1rem',
                                                                    color: 'var(--color-text-muted)',
                                                                    fontWeight: '400'
                                                                }}> / {item.max}</span>
                                                            </div>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}

                                    {/* Strengths & Issues Grid */}
                                    <div style={{
                                        display: 'grid',
                                        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                                        gap: '1.5rem',
                                        marginBottom: '2rem'
                                    }}>
                                        {/* Strengths */}
                                        {result.feedback.strengths && (
                                            <div className="animate-fade-in-up delay-200">
                                                <h4 style={{
                                                    marginBottom: '1rem',
                                                    color: 'var(--color-success)',
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
                                                    What's Excellent
                                                </h4>
                                                {result.feedback.strengths.map((str, idx) => (
                                                    <div
                                                        key={idx}
                                                        className="hover-lift"
                                                        style={{
                                                            padding: '1.25rem',
                                                            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(5, 150, 105, 0.08) 100%)',
                                                            border: '1px solid rgba(16, 185, 129, 0.2)',
                                                            borderRadius: 'var(--radius-md)',
                                                            marginBottom: '0.75rem'
                                                        }}
                                                    >
                                                        <div style={{
                                                            fontWeight: '600',
                                                            color: 'var(--color-success)',
                                                            marginBottom: '0.35rem'
                                                        }}>{str.title}</div>
                                                        <div style={{
                                                            fontSize: '0.9rem',
                                                            color: 'var(--color-text-secondary)',
                                                            lineHeight: '1.5'
                                                        }}>{str.description}</div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}

                                        {/* Issues */}
                                        {result.feedback.issues && (
                                            <div className="animate-fade-in-up delay-300">
                                                <h4 style={{
                                                    marginBottom: '1rem',
                                                    color: 'var(--color-danger)',
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
                                                        background: 'var(--gradient-danger)',
                                                        borderRadius: 'var(--radius-sm)',
                                                        fontSize: '0.9rem'
                                                    }}>⚠️</span>
                                                    Needs Improvement
                                                </h4>
                                                {result.feedback.issues.map((iss, idx) => (
                                                    <div
                                                        key={idx}
                                                        className="hover-lift"
                                                        style={{
                                                            padding: '1.25rem',
                                                            background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.08) 0%, rgba(220, 38, 38, 0.08) 100%)',
                                                            border: '1px solid rgba(239, 68, 68, 0.2)',
                                                            borderRadius: 'var(--radius-md)',
                                                            marginBottom: '0.75rem'
                                                        }}
                                                    >
                                                        <div style={{
                                                            fontWeight: '600',
                                                            color: 'var(--color-danger)',
                                                            marginBottom: '0.35rem'
                                                        }}>{iss.title}</div>
                                                        <div style={{
                                                            fontSize: '0.9rem',
                                                            color: 'var(--color-text-secondary)',
                                                            lineHeight: '1.5'
                                                        }}>{iss.description}</div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>

                                    {/* Action Plan */}
                                    {result.feedback.action_plan && (
                                        <div className="animate-fade-in-up delay-300" style={{
                                            padding: '1.5rem',
                                            background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(217, 119, 6, 0.08) 100%)',
                                            border: '1px solid rgba(245, 158, 11, 0.2)',
                                            borderRadius: 'var(--radius-lg)',
                                            marginBottom: '2rem'
                                        }}>
                                            <h4 style={{
                                                marginBottom: '1rem',
                                                color: 'var(--color-warning)',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '0.5rem'
                                            }}>
                                                <FiAward size={18} />
                                                Actionable Improvement Plan
                                            </h4>
                                            <ul style={{ paddingLeft: '1.5rem', margin: 0 }}>
                                                {result.feedback.action_plan.map((action, idx) => (
                                                    <li key={idx} style={{
                                                        marginBottom: '0.6rem',
                                                        color: 'var(--color-text)',
                                                        lineHeight: '1.5'
                                                    }}>{action}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Extracted Info */}
                            <div style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                                gap: '1rem',
                                marginBottom: '1.5rem'
                            }} className="animate-fade-in delay-200">
                                {result.extracted_data?.name && (
                                    <div className="hover-lift" style={{
                                        padding: '1.25rem',
                                        background: 'var(--color-bg-alt)',
                                        borderRadius: 'var(--radius-md)',
                                        border: '1px solid var(--color-border-light)'
                                    }}>
                                        <div style={{
                                            fontSize: '0.75rem',
                                            color: 'var(--color-text-muted)',
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.5px',
                                            marginBottom: '0.5rem'
                                        }}>Name</div>
                                        <div style={{ fontWeight: '600', color: 'var(--color-text)' }}>
                                            {result.extracted_data.name}
                                        </div>
                                    </div>
                                )}
                                {result.extracted_data?.email && (
                                    <div className="hover-lift" style={{
                                        padding: '1.25rem',
                                        background: 'var(--color-bg-alt)',
                                        borderRadius: 'var(--radius-md)',
                                        border: '1px solid var(--color-border-light)'
                                    }}>
                                        <div style={{
                                            fontSize: '0.75rem',
                                            color: 'var(--color-text-muted)',
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.5px',
                                            marginBottom: '0.5rem'
                                        }}>Email</div>
                                        <div style={{ fontWeight: '600', color: 'var(--color-text)' }}>
                                            {result.extracted_data.email}
                                        </div>
                                    </div>
                                )}
                                {result.extracted_data?.phone && (
                                    <div className="hover-lift" style={{
                                        padding: '1.25rem',
                                        background: 'var(--color-bg-alt)',
                                        borderRadius: 'var(--radius-md)',
                                        border: '1px solid var(--color-border-light)'
                                    }}>
                                        <div style={{
                                            fontSize: '0.75rem',
                                            color: 'var(--color-text-muted)',
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.5px',
                                            marginBottom: '0.5rem'
                                        }}>Phone</div>
                                        <div style={{ fontWeight: '600', color: 'var(--color-text)' }}>
                                            {result.extracted_data.phone}
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Skills */}
                            {result.extracted_data?.skills && result.extracted_data.skills.length > 0 && (
                                <div className="animate-fade-in-up delay-300" style={{ marginBottom: '1.5rem' }}>
                                    <h4 style={{
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
                                            background: 'var(--gradient-primary)',
                                            borderRadius: 'var(--radius-sm)',
                                            color: 'white',
                                            fontSize: '0.8rem'
                                        }}>✨</span>
                                        Extracted Skills
                                    </h4>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                                        {result.extracted_data.skills.map((skill, idx) => (
                                            <span
                                                key={idx}
                                                className="hover-scale animate-fade-in"
                                                style={{
                                                    padding: '0.5rem 1rem',
                                                    background: 'var(--gradient-primary)',
                                                    color: 'white',
                                                    borderRadius: 'var(--radius-full)',
                                                    fontSize: '0.9rem',
                                                    fontWeight: '500',
                                                    boxShadow: 'var(--shadow-sm)',
                                                    animationDelay: `${idx * 50}ms`
                                                }}
                                            >
                                                {typeof skill === 'string' ? skill : skill.name}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Experience */}
                            {result.extracted_data?.experience && result.extracted_data.experience.length > 0 && (
                                <div className="animate-fade-in-up delay-400" style={{ marginBottom: '1.5rem' }}>
                                    <h4 style={{
                                        marginBottom: '1rem',
                                        color: 'var(--color-text)',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.5rem'
                                    }}>
                                        <FiBriefcase size={18} />
                                        Experience
                                    </h4>
                                    {result.extracted_data.experience.map((exp, idx) => (
                                        <div
                                            key={idx}
                                            className="hover-lift"
                                            style={{
                                                padding: '1.25rem',
                                                background: 'var(--color-bg-alt)',
                                                borderRadius: 'var(--radius-md)',
                                                marginBottom: '0.75rem',
                                                borderLeft: '3px solid var(--color-primary)'
                                            }}
                                        >
                                            <div style={{ fontWeight: '600', color: 'var(--color-text)' }}>
                                                {exp.title || exp.role}
                                            </div>
                                            <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
                                                {exp.company} • {exp.duration}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Education */}
                            {result.extracted_data?.education && result.extracted_data.education.length > 0 && (
                                <div className="animate-fade-in-up delay-500" style={{ marginBottom: '2rem' }}>
                                    <h4 style={{
                                        marginBottom: '1rem',
                                        color: 'var(--color-text)',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.5rem'
                                    }}>
                                        🎓 Education
                                    </h4>
                                    {result.extracted_data.education.map((edu, idx) => (
                                        <div
                                            key={idx}
                                            className="hover-lift"
                                            style={{
                                                padding: '1.25rem',
                                                background: 'var(--color-bg-alt)',
                                                borderRadius: 'var(--radius-md)',
                                                marginBottom: '0.75rem',
                                                borderLeft: '3px solid var(--color-success)'
                                            }}
                                        >
                                            <div style={{ fontWeight: '600', color: 'var(--color-text)' }}>
                                                {edu.degree}
                                            </div>
                                            <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
                                                {edu.institution} • {edu.year}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Next Steps */}
                            <div className="animate-fade-in-up delay-500" style={{
                                padding: '2rem',
                                background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.08) 0%, rgba(118, 75, 162, 0.08) 100%)',
                                borderRadius: 'var(--radius-lg)',
                                border: '1px solid rgba(102, 126, 234, 0.15)'
                            }}>
                                <h4 style={{
                                    marginBottom: '1.25rem',
                                    color: 'var(--color-text)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    fontSize: '1.1rem'
                                }}>
                                    🚀 Next Steps
                                </h4>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
                                    <button
                                        onClick={() => navigate('/skill-gaps')}
                                        className="btn-glow hover-lift"
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.5rem',
                                            padding: '0.875rem 1.5rem',
                                            background: 'var(--gradient-primary)',
                                            color: 'white',
                                            border: 'none',
                                            borderRadius: 'var(--radius-md)',
                                            fontWeight: '600',
                                            cursor: 'pointer',
                                            boxShadow: 'var(--shadow-md)'
                                        }}
                                    >
                                        <FiTarget size={16} />
                                        View Skill Gaps
                                        <FiArrowRight size={14} />
                                    </button>
                                    <button
                                        onClick={() => navigate('/learning')}
                                        className="btn-glow hover-lift"
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.5rem',
                                            padding: '0.875rem 1.5rem',
                                            background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                                            color: 'white',
                                            border: 'none',
                                            borderRadius: 'var(--radius-md)',
                                            fontWeight: '600',
                                            cursor: 'pointer',
                                            boxShadow: 'var(--shadow-md)'
                                        }}
                                    >
                                        <FiBook size={16} />
                                        Start Learning Path
                                        <FiArrowRight size={14} />
                                    </button>
                                    <button
                                        onClick={() => navigate('/opportunities')}
                                        className="btn-glow hover-lift"
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.5rem',
                                            padding: '0.875rem 1.5rem',
                                            background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
                                            color: 'white',
                                            border: 'none',
                                            borderRadius: 'var(--radius-md)',
                                            fontWeight: '600',
                                            cursor: 'pointer',
                                            boxShadow: 'var(--shadow-md)'
                                        }}
                                    >
                                        <FiBriefcase size={16} />
                                        Find Opportunities
                                        <FiArrowRight size={14} />
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ResumeUpload;
