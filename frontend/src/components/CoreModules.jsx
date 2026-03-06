import { useNavigate } from 'react-router-dom';
import {
    FiUser, FiLayers, FiBook, FiBell, FiMessageSquare,
    FiChevronRight
} from 'react-icons/fi';

const CoreModules = () => {
    const navigate = useNavigate();

    const handleNavigate = (path) => {
        navigate(path);
    };

    const modules = [
        {
            id: 'profile',
            title: 'User & Profile Management',
            description: 'Manage your identity, resume, and career preferences.',
            icon: FiUser,
            color: 'var(--color-primary)',
            bgSoft: 'rgba(102, 126, 234, 0.1)',
            gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            primaryPath: '/profile/student',
            links: [
                { label: 'Profile', path: '/profile/student' },
                { label: 'Resume', path: '/resume' }
            ]
        },
        {
            id: 'evaluation',
            title: 'Evaluation & Matching',
            description: 'Discover your skill gaps and prove your expertise through assessments.',
            icon: FiLayers,
            color: '#10b981',
            bgSoft: 'rgba(16, 185, 129, 0.1)',
            gradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
            primaryPath: '/skill-gaps',
            links: [
                { label: 'Skill Gaps', path: '/skill-gaps' },
                { label: 'Assessments', path: '/assessment' }
            ]
        },
        {
            id: 'learning',
            title: 'Learning & Feedback',
            description: 'Upskill with AI-guided learning paths and actionable feedback.',
            icon: FiBook,
            color: '#f59e0b',
            bgSoft: 'rgba(245, 158, 11, 0.1)',
            gradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
            primaryPath: '/learning',
            links: [
                { label: 'Learning Paths', path: '/learning' }
            ]
        },
        {
            id: 'recommendation',
            title: 'Recommendations & Notifications',
            description: 'Stay updated with personalized job matches and critical alerts.',
            icon: FiBell,
            color: '#ef4444',
            bgSoft: 'rgba(239, 68, 68, 0.1)',
            gradient: 'linear-gradient(135deg, #ef4444 0%, #b91c1c 100%)',
            primaryPath: '/opportunities',
            links: [
                { label: 'Opportunities', path: '/opportunities' },
                { label: 'Alerts', path: '/smart-notifications' },
                { label: 'Research', path: '/research' }
            ]
        },
        {
            id: 'communication',
            title: 'Communication & Tracking',
            description: 'Track applications, prep for interviews, and communicate.',
            icon: FiMessageSquare,
            color: '#8b5cf6',
            bgSoft: 'rgba(139, 92, 246, 0.1)',
            gradient: 'linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)',
            primaryPath: '/applications',
            links: [
                { label: 'Applications', path: '/applications' },
                { label: 'Messages', path: '/messages' },
                { label: 'Interviews', path: '/interviews' },
                { label: 'Mock', path: '/mock-interview' },
                { label: 'Voice', path: '/interview/voice' },
            ]
        }
    ];

    return (
        <div style={{ marginBottom: '2rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }}>
                {modules.map((mod) => (
                    <div
                        key={mod.id}
                        className="interactive-card hover-lift"
                        style={{
                            background: 'var(--color-bg)',
                            borderRadius: 'var(--radius-lg)',
                            padding: '1.5rem',
                            border: '1px solid var(--color-border-light)',
                            boxShadow: 'var(--shadow-sm)',
                            display: 'flex',
                            flexDirection: 'column',
                            transition: 'all 0.3s ease',
                            cursor: 'pointer'
                        }}
                        onClick={() => handleNavigate(mod.primaryPath)}
                    >
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem', marginBottom: '1rem' }}>
                            <div style={{
                                width: '48px', height: '48px', borderRadius: '14px',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                background: mod.bgSoft, color: mod.color, flexShrink: 0
                            }}>
                                <mod.icon size={24} />
                            </div>
                            <div>
                                <h3 style={{ margin: '0 0 0.25rem 0', fontSize: '1.1rem', color: 'var(--color-text)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                    {mod.title}
                                </h3>
                                <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                                    {mod.description}
                                </p>
                            </div>
                        </div>

                        <div style={{ marginTop: 'auto', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                            {mod.links.map((link, idx) => (
                                <button
                                    key={idx}
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        handleNavigate(link.path);
                                    }}
                                    style={{
                                        background: 'var(--color-bg-alt)',
                                        border: '1px solid var(--color-border)',
                                        borderRadius: 'var(--radius-full)',
                                        padding: '0.35rem 0.75rem',
                                        fontSize: '0.8rem',
                                        color: 'var(--color-text-secondary)',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.25rem',
                                        transition: 'all 0.2s ease'
                                    }}
                                    onMouseOver={(e) => {
                                        e.currentTarget.style.borderColor = mod.color;
                                        e.currentTarget.style.color = mod.color;
                                    }}
                                    onMouseOut={(e) => {
                                        e.currentTarget.style.borderColor = 'var(--color-border)';
                                        e.currentTarget.style.color = 'var(--color-text-secondary)';
                                    }}
                                >
                                    {link.label}
                                    <FiChevronRight size={12} />
                                </button>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default CoreModules;
