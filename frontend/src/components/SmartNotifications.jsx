import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { smartNotificationService } from '../services/smartNotificationService';
import {
    FiBell, FiBriefcase, FiClock, FiBook, FiUsers, FiAward, FiCheckCircle,
    FiSettings, FiX, FiChevronRight, FiZap, FiMessageSquare, FiCalendar,
    FiRefreshCw, FiTrendingUp, FiInbox
} from 'react-icons/fi';
import '../App.css';

/* ─────────────────── helpers ─────────────────── */

const TYPE_META = {
    opportunity_match:  { label: 'Job Match',        icon: FiBriefcase,    gradient: 'linear-gradient(135deg,#3b82f6,#1d4ed8)', bg: '#eff6ff', border: '#bfdbfe', dot: '#3b82f6' },
    deadline_reminder:  { label: 'Deadline',          icon: FiClock,        gradient: 'linear-gradient(135deg,#ef4444,#b91c1c)', bg: '#fef2f2', border: '#fecaca', dot: '#ef4444' },
    learning_reminder:  { label: 'Learning',          icon: FiBook,         gradient: 'linear-gradient(135deg,#10b981,#047857)', bg: '#ecfdf5', border: '#a7f3d0', dot: '#10b981' },
    recruiter_activity: { label: 'Recruiter',         icon: FiUsers,        gradient: 'linear-gradient(135deg,#8b5cf6,#6d28d9)', bg: '#f5f3ff', border: '#ddd6fe', dot: '#8b5cf6' },
    achievement:        { label: 'Achievement',       icon: FiAward,        gradient: 'linear-gradient(135deg,#f59e0b,#b45309)', bg: '#fffbeb', border: '#fde68a', dot: '#f59e0b' },
    interview_proposed: { label: 'Interview',         icon: FiCalendar,     gradient: 'linear-gradient(135deg,#06b6d4,#0e7490)', bg: '#ecfeff', border: '#a5f3fc', dot: '#06b6d4' },
    message:            { label: 'Message',           icon: FiMessageSquare,gradient: 'linear-gradient(135deg,#ec4899,#be185d)', bg: '#fdf2f8', border: '#fbcfe8', dot: '#ec4899' },
};

const PRIORITY_BADGE = {
    urgent: { label: '🔴 Urgent', color: '#ef4444' },
    high:   { label: '🟠 High',   color: '#f97316' },
    medium: { label: '🔵 Medium', color: '#3b82f6' },
    low:    { label: '⚪ Low',    color: '#94a3b8' },
};

const getMeta = (type) => TYPE_META[type] || { label: type, icon: FiBell, gradient: 'linear-gradient(135deg,#64748b,#334155)', bg: '#f8fafc', border: '#e2e8f0', dot: '#94a3b8' };

const timeAgo = (timestamp) => {
    if (!timestamp) return '';
    const secs = Math.floor((Date.now() - new Date(timestamp)) / 1000);
    if (secs < 60)    return 'Just now';
    if (secs < 3600)  return `${Math.floor(secs / 60)}m ago`;
    if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
    return new Date(timestamp).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
};

/* ─────────────────── component ─────────────────── */

const SmartNotifications = () => {
    const navigate = useNavigate();
    const { user } = useAuth();

    const [notifications, setNotifications] = useState([]);
    const [stats, setStats]                 = useState(null);
    const [loading, setLoading]             = useState(true);
    const [refreshing, setRefreshing]       = useState(false);
    const [filter, setFilter]               = useState('all');
    const [showSettings, setShowSettings]   = useState(false);
    const [settings, setSettings]           = useState(null);
    const [savingSettings, setSavingSettings] = useState(false);
    const [error, setError]                 = useState(null);

    /* ── data loaders ── */
    const loadAll = useCallback(async (silent = false) => {
        if (!silent) setLoading(true); else setRefreshing(true);
        setError(null);
        try {
            const [notifData, statsData] = await Promise.all([
                smartNotificationService.getNotifications(false, 50, null),
                smartNotificationService.getStats()
            ]);
            setNotifications(notifData.notifications || notifData || []);
            setStats(statsData.stats || statsData);
        } catch (err) {
            console.error('Failed to load notifications:', err);
            setError('Could not reach the server. Showing cached data.');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    useEffect(() => {
        if (!user) { navigate('/'); return; }
        loadAll();
    }, [user, navigate, loadAll]);

    /* ── actions ── */
    const handleMarkRead = async (id, e) => {
        e?.stopPropagation();
        try {
            await smartNotificationService.markAsRead(id);
            setNotifications(prev => prev.map(n => (n._id || n.id) === id ? { ...n, read: true, is_read: true } : n));
            if (stats) setStats(s => ({ ...s, unread: Math.max(0, (s.unread || 1) - 1), read: (s.read || 0) + 1 }));
        } catch { /* silent */ }
    };

    const handleMarkAllRead = async () => {
        try {
            await smartNotificationService.markAllAsRead();
            setNotifications(prev => prev.map(n => ({ ...n, read: true, is_read: true })));
            if (stats) setStats(s => ({ ...s, unread: 0, read: s.total || s.read }));
        } catch { /* silent */ }
    };

    const handleClick = async (notif) => {
        const id = notif._id || notif.id;
        try { await smartNotificationService.clickNotification(id); } catch { /* silent */ }
        handleMarkRead(id);

        // Type → verified App.jsx route map
        const fallbackMap = {
            opportunity_match:  '/opportunities',
            deadline_reminder:  '/opportunities',
            learning_reminder:  '/learning',
            interview_proposed: '/interviews',
            recruiter_activity: '/messages',
            message:            '/messages',
            achievement:        '/profile/student',
        };

        // Whitelist of valid routes — only navigate to action_url if it's a real route
        const validRoutes = [
            '/opportunities', '/learning', '/messages', '/interviews',
            '/profile/student', '/applications', '/research', '/skill-gaps',
            '/mock-interview', '/resume', '/analytics', '/notifications',
            '/smart-notifications', '/dashboard/student',
        ];

        const actionUrl = notif.action_url;
        if (actionUrl) {
            // Check if action_url starts with a valid route prefix
            const isValid = validRoutes.some(r => actionUrl === r || actionUrl.startsWith(r + '/'));
            if (isValid) {
                navigate(actionUrl);
                return;
            }
            // If invalid (e.g. /opportunities/jobs/{id}), use the type-based fallback
        }

        const destination = fallbackMap[notif.type] || '/dashboard/student';
        navigate(destination);
    };

    const handleDismiss = async (id, e) => {
        e.stopPropagation();
        try {
            await smartNotificationService.dismissNotification(id);
            setNotifications(prev => prev.filter(n => (n._id || n.id) !== id));
        } catch { /* silent */ }
    };

    const handleTrigger = async () => {
        setRefreshing(true);
        try {
            await smartNotificationService.triggerCheck('all');
            await loadAll(true);
        } catch { setRefreshing(false); }
    };

    const handleLoadSettings = async () => {
        try {
            const data = await smartNotificationService.getSettings();
            setSettings(data.settings || data);
            setShowSettings(true);
        } catch { setError('Failed to load settings.'); }
    };

    const handleSaveSettings = async () => {
        setSavingSettings(true);
        try {
            await smartNotificationService.updateSettings(settings);
            setShowSettings(false);
        } catch { setError('Failed to save settings.'); }
        finally { setSavingSettings(false); }
    };

    /* ── filter logic ── */
    const TABS = [
        { value: 'all',         label: 'All' },
        { value: 'unread',      label: 'Unread' },
        { value: 'opportunity_match',  label: '💼 Jobs' },
        { value: 'deadline_reminder',  label: '⏰ Deadlines' },
        { value: 'learning_reminder',  label: '📚 Learning' },
        { value: 'recruiter_activity', label: '👥 Recruiter' },
        { value: 'achievement',        label: '🏆 Achievements' },
    ];

    const visible = notifications.filter(n => {
        if (filter === 'all')    return true;
        if (filter === 'unread') return !n.read && !n.is_read;
        return n.type === filter;
    });

    const unreadCount = notifications.filter(n => !n.read && !n.is_read).length;

    if (!user) return null;

    /* ── render ── */
    return (
        <>
            <div className="dashboard-main">
                {/* ── Header ── */}
                <div className="dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <h1 className="dashboard-title" style={{ margin: 0 }}>Notifications</h1>
                        {unreadCount > 0 && (
                            <span style={{
                                padding: '0.25rem 0.75rem',
                                background: 'linear-gradient(135deg,#ef4444,#b91c1c)',
                                color: 'white',
                                borderRadius: '999px',
                                fontSize: '0.8rem',
                                fontWeight: 700,
                                boxShadow: '0 2px 8px rgba(239,68,68,0.4)'
                            }}>
                                {unreadCount} new
                            </span>
                        )}
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        {unreadCount > 0 && (
                            <button onClick={handleMarkAllRead} className="edit-button" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                                <FiCheckCircle size={14} /> Mark all read
                            </button>
                        )}
                        <button onClick={handleTrigger} className="edit-button" title="Refresh notifications" style={{ margin: 0 }}>
                            <FiRefreshCw size={14} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
                        </button>
                        <button onClick={handleLoadSettings} className="edit-button" style={{ margin: 0 }}>
                            <FiSettings size={14} />
                        </button>
                    </div>
                </div>

                <div className="dashboard-content">

                    {/* ── Error banner ── */}
                    {error && (
                        <div style={{ padding: '0.75rem 1rem', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '10px', color: '#dc2626', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <FiZap /> {error}
                            <button onClick={() => setError(null)} style={{ marginLeft: 'auto', border: 'none', background: 'none', cursor: 'pointer', color: '#dc2626' }}><FiX /></button>
                        </div>
                    )}

                    {/* ── Stats Grid ── */}
                    {stats && (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
                            {[
                                { label: 'Total',   value: stats.total   || notifications.length, icon: FiInbox,      color: '#3b82f6' },
                                { label: 'Unread',  value: stats.unread  || unreadCount,           icon: FiBell,       color: '#ef4444' },
                                { label: 'Read',    value: stats.read    || (notifications.length - unreadCount), icon: FiCheckCircle, color: '#10b981' },
                                { label: 'Clicked', value: stats.clicked || 0,                    icon: FiTrendingUp, color: '#f59e0b' },
                            ].map(s => (
                                <div key={s.label} className="card" style={{ padding: '1rem', textAlign: 'center', background: 'white', borderRadius: '14px', border: '1px solid #f1f5f9' }}>
                                    <s.icon size={20} style={{ color: s.color, marginBottom: '0.5rem' }} />
                                    <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#1e293b', lineHeight: 1 }}>{s.value}</div>
                                    <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem', fontWeight: 500 }}>{s.label}</div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* ── Filter Tabs ── */}
                    <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
                        {TABS.map(tab => {
                            const active = filter === tab.value;
                            return (
                                <button
                                    key={tab.value}
                                    onClick={() => setFilter(tab.value)}
                                    style={{
                                        padding: '0.45rem 1rem',
                                        border: 'none',
                                        background: active ? 'linear-gradient(135deg,#3b82f6,#8b5cf6)' : '#f1f5f9',
                                        color: active ? 'white' : '#64748b',
                                        borderRadius: '8px',
                                        cursor: 'pointer',
                                        fontSize: '0.82rem',
                                        fontWeight: active ? 700 : 500,
                                        transition: 'all 0.2s',
                                        boxShadow: active ? '0 4px 12px rgba(59,130,246,0.3)' : 'none'
                                    }}
                                >
                                    {tab.label}
                                    {tab.value === 'unread' && unreadCount > 0 && (
                                        <span style={{ marginLeft: '0.4rem', background: '#ef4444', color: 'white', borderRadius: '999px', padding: '0 5px', fontSize: '0.7rem' }}>
                                            {unreadCount}
                                        </span>
                                    )}
                                </button>
                            );
                        })}
                    </div>

                    {/* ── Notification List ── */}
                    {loading ? (
                        <div className="card" style={{ textAlign: 'center', padding: '4rem' }}>
                            <div className="loading-spinner" style={{ margin: '0 auto 1rem', width: 48, height: 48, border: '4px solid #e2e8f0', borderTop: '4px solid #3b82f6' }} />
                            <p style={{ color: '#64748b' }}>Loading your notifications…</p>
                        </div>
                    ) : visible.length === 0 ? (
                        <div className="card" style={{ textAlign: 'center', padding: '4rem', borderRadius: '16px' }}>
                            <FiBell size={52} style={{ color: '#cbd5e1', marginBottom: '1rem' }} />
                            <h3 style={{ color: '#475569', margin: '0 0 0.5rem' }}>
                                {filter === 'unread' ? 'You\'re all caught up!' : 'No notifications here'}
                            </h3>
                            <p style={{ color: '#94a3b8', margin: 0 }}>
                                {filter === 'unread' ? 'All notifications have been read.' : 'Nothing to show for this category yet.'}
                            </p>
                            <button onClick={handleTrigger} className="form-button" style={{ marginTop: '1.5rem', display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
                                <FiZap /> Check for new notifications
                            </button>
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                            {visible.map((notif, idx) => {
                                const id       = notif._id || notif.id;
                                const meta     = getMeta(notif.type);
                                const Icon     = meta.icon;
                                const isUnread = !notif.read && !notif.is_read;
                                const pBadge   = PRIORITY_BADGE[notif.priority];

                                return (
                                    <div
                                        key={id || idx}
                                        onClick={() => handleClick(notif)}
                                        style={{
                                            padding: '1rem 1.25rem',
                                            background: isUnread ? meta.bg : 'white',
                                            border: `1px solid ${isUnread ? meta.border : '#e8edf4'}`,
                                            borderRadius: '14px',
                                            cursor: 'pointer',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '1rem',
                                            transition: 'all 0.2s',
                                            boxShadow: isUnread ? `0 2px 12px ${meta.dot}22` : '0 1px 4px rgba(0,0,0,0.04)',
                                            position: 'relative',
                                        }}
                                        onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = `0 6px 20px ${meta.dot}33`; }}
                                        onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = isUnread ? `0 2px 12px ${meta.dot}22` : '0 1px 4px rgba(0,0,0,0.04)'; }}
                                    >
                                        {/* unread indicator */}
                                        {isUnread && (
                                            <div style={{ position: 'absolute', left: 0, top: '50%', transform: 'translateY(-50%)', width: 4, height: '60%', background: meta.dot, borderRadius: '0 4px 4px 0' }} />
                                        )}

                                        {/* Icon bubble */}
                                        <div style={{
                                            width: 44, height: 44,
                                            background: meta.gradient,
                                            borderRadius: '12px',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            flexShrink: 0,
                                            boxShadow: `0 4px 12px ${meta.dot}44`
                                        }}>
                                            <Icon size={20} color="white" />
                                        </div>

                                        {/* Text */}
                                        <div style={{ flex: 1, minWidth: 0 }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.2rem' }}>
                                                <span style={{
                                                    fontWeight: isUnread ? 700 : 500,
                                                    color: '#0f172a',
                                                    fontSize: '0.95rem',
                                                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
                                                }}>
                                                    {notif.title || meta.label}
                                                </span>
                                                {pBadge && notif.priority !== 'low' && (
                                                    <span style={{ fontSize: '0.7rem', color: pBadge.color, fontWeight: 600, whiteSpace: 'nowrap' }}>
                                                        {pBadge.label}
                                                    </span>
                                                )}
                                            </div>
                                            <div style={{ fontSize: '0.85rem', color: '#64748b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: '0.25rem' }}>
                                                {notif.message || ''}
                                            </div>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.75rem', color: '#94a3b8' }}>
                                                <span style={{ background: '#f1f5f9', px: 6, padding: '1px 8px', borderRadius: 6, fontWeight: 500, color: '#475569' }}>
                                                    {meta.label}
                                                </span>
                                                <span>{timeAgo(notif.created_at)}</span>
                                                {notif.action_url && <span style={{ color: '#3b82f6' }}>→ View</span>}
                                            </div>
                                        </div>

                                        {/* Actions */}
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', flexShrink: 0 }}>
                                            {isUnread && (
                                                <button
                                                    onClick={(e) => handleMarkRead(id, e)}
                                                    title="Mark as read"
                                                    style={{ padding: '0.35rem', border: 'none', background: 'rgba(16,185,129,0.1)', color: '#10b981', borderRadius: '8px', cursor: 'pointer', display: 'flex' }}
                                                >
                                                    <FiCheckCircle size={15} />
                                                </button>
                                            )}
                                            <button
                                                onClick={(e) => handleDismiss(id, e)}
                                                title="Dismiss"
                                                style={{ padding: '0.35rem', border: 'none', background: 'rgba(148,163,184,0.1)', color: '#94a3b8', borderRadius: '8px', cursor: 'pointer', display: 'flex' }}
                                            >
                                                <FiX size={15} />
                                            </button>
                                            <FiChevronRight size={16} style={{ color: '#cbd5e1' }} />
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>

            {/* ── Settings Modal ── */}
            {showSettings && (
                <div style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, backdropFilter: 'blur(4px)' }}>
                    <div style={{ background: 'white', borderRadius: '20px', padding: '2rem', maxWidth: 480, width: '90%', maxHeight: '85vh', overflow: 'auto', boxShadow: '0 25px 60px rgba(0,0,0,0.25)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                            <div>
                                <h2 style={{ margin: 0, color: '#0f172a' }}>Notification Preferences</h2>
                                <p style={{ margin: '0.25rem 0 0', color: '#64748b', fontSize: '0.875rem' }}>Control what you want to be notified about</p>
                            </div>
                            <button onClick={() => setShowSettings(false)} style={{ border: 'none', background: '#f1f5f9', borderRadius: '10px', padding: '0.5rem', cursor: 'pointer', color: '#64748b' }}>
                                <FiX size={18} />
                            </button>
                        </div>

                        {settings ? (
                            <>
                                {Object.entries(settings).map(([key, val]) => {
                                    const enabled = val?.enabled !== false;
                                    const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                                    return (
                                        <div key={key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', background: '#f8fafc', borderRadius: '12px', marginBottom: '0.75rem', border: '1px solid #f1f5f9' }}>
                                            <div>
                                                <div style={{ fontWeight: 600, color: '#1e293b', marginBottom: '0.1rem' }}>{label}</div>
                                                {val?.min_score_threshold && <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Min score: {val.min_score_threshold}%</div>}
                                                {val?.advance_notice_days && <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Notice: {val.advance_notice_days} days</div>}
                                            </div>
                                            <label style={{ position: 'relative', display: 'inline-block', width: 44, height: 24, cursor: 'pointer', flexShrink: 0 }}>
                                                <input
                                                    type="checkbox"
                                                    checked={enabled}
                                                    onChange={() => setSettings(prev => ({
                                                        ...prev,
                                                        [key]: { ...(prev[key] || {}), enabled: !enabled }
                                                    }))}
                                                    style={{ opacity: 0, width: 0, height: 0 }}
                                                />
                                                <span style={{
                                                    position: 'absolute', inset: 0,
                                                    background: enabled ? '#3b82f6' : '#cbd5e1',
                                                    borderRadius: '999px',
                                                    transition: '0.2s'
                                                }} />
                                                <span style={{
                                                    position: 'absolute',
                                                    top: 3, left: enabled ? 23 : 3,
                                                    width: 18, height: 18,
                                                    background: 'white',
                                                    borderRadius: '50%',
                                                    transition: '0.2s',
                                                    boxShadow: '0 1px 4px rgba(0,0,0,0.2)'
                                                }} />
                                            </label>
                                        </div>
                                    );
                                })}

                                <button
                                    onClick={handleSaveSettings}
                                    className="form-button"
                                    style={{ width: '100%', marginTop: '0.5rem', opacity: savingSettings ? 0.7 : 1 }}
                                    disabled={savingSettings}
                                >
                                    {savingSettings ? 'Saving…' : '✓ Save Preferences'}
                                </button>
                            </>
                        ) : (
                            <div style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
                                <div className="loading-spinner" style={{ margin: '0 auto 1rem' }} />
                                Loading settings…
                            </div>
                        )}
                    </div>
                </div>
            )}
        </>
    );
};

export default SmartNotifications;
