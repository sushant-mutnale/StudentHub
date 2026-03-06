import React, { useState, useEffect } from 'react';
import { applicationService } from '../services/applicationService';
import { FaCheckCircle, FaCircle, FaSpinner, FaTimesCircle } from 'react-icons/fa';
import SidebarLeft from './SidebarLeft';

const ApplicationTracker = () => {
    const [applications, setApplications] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadApplications();
    }, []);

    const loadApplications = async () => {
        try {
            const data = await applicationService.getStudentApplications();
            setApplications(data.applications || []);
        } catch (error) {
            console.error("Failed to load applications", error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="p-8 text-center text-gray-500">Loading your applications...</div>;

    if (applications.length === 0) {
        return (
            <div className="dashboard-container">
                <SidebarLeft />
                <div className="dashboard-main custom-scrollbar">
                    <div className="dashboard-header animate-fade-in-down">
                        <h1 className="dashboard-title text-2xl font-bold text-gray-800 m-0">My Applications</h1>
                    </div>
                    <div className="dashboard-content" style={{ maxWidth: '900px', margin: '0 auto' }}>
                        <div className="text-center p-12 bg-white rounded-lg shadow-sm">
                            <h3 className="text-lg font-semibold text-gray-800 mb-2">No Applications Yet</h3>
                            <p className="text-gray-600">Start applying to jobs to track them here!</p>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-container">
            <SidebarLeft />
            <div className="dashboard-main custom-scrollbar">
                <div className="dashboard-header animate-fade-in-down">
                    <h1 className="dashboard-title text-2xl font-bold text-gray-800 m-0">My Applications</h1>
                </div>
                <div className="dashboard-content" style={{ maxWidth: '900px', margin: '0 auto' }}>
                    <div className="space-y-6">

                        {applications.map(app => (
                            <div key={app._id} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                                <div className="flex justify-between items-start mb-6">
                                    <div>
                                        <h3 className="text-xl font-bold text-gray-900">{app.job_title}</h3>
                                        <p className="text-gray-600 font-medium">{app.company_name}</p>
                                        <p className="text-sm text-gray-400 mt-1">Applied on {new Date(app.applied_at).toLocaleDateString()}</p>
                                    </div>
                                    <span className={`px-4 py-1 rounded-full text-sm font-semibold border ${getStatusColor(app.current_stage_name)}`}>
                                        {app.current_stage_name}
                                    </span>
                                </div>

                                {/* Vertical History Timeline */}
                                <div className="mt-8 px-4">
                                    <h4 className="text-lg font-bold text-gray-800 mb-6 border-b pb-2">Track Application</h4>

                                    <div className="flex flex-col">
                                        {/* Fallback if no history exists (legacy applications) */}
                                        {(!app.stage_history || app.stage_history.length === 0) ? (
                                            <div className="text-gray-500 italic text-sm text-center py-4">
                                                Application history not available. Current status: {app.current_stage_name}
                                            </div>
                                        ) : (
                                            // Render actual history
                                            [...app.stage_history].reverse().map((history, idx, arr) => {
                                                const dateObj = new Date(history.timestamp);
                                                const timeString = dateObj.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) + ' (IST)';

                                                // Format date as "19th Aug, 2025"
                                                const day = dateObj.getDate();
                                                const ordinal = day % 10 === 1 && day !== 11 ? 'st' : day % 10 === 2 && day !== 12 ? 'nd' : day % 10 === 3 && day !== 13 ? 'rd' : 'th';
                                                const monthStr = dateObj.toLocaleDateString('en-US', { month: 'short' });
                                                const yearStr = dateObj.getFullYear();
                                                const dateString = `${day}${ordinal} ${monthStr}, ${yearStr}`;

                                                const isLast = idx === arr.length - 1;

                                                return (
                                                    <div key={idx} style={{ display: 'flex', position: 'relative', alignItems: 'flex-start', marginBottom: '1.5rem', width: '100%' }}>

                                                        {/* Left Column: Date & Time */}
                                                        <div style={{ width: '25%', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', paddingRight: '1.5rem', paddingTop: '0.75rem', textAlign: 'right' }}>
                                                            <div style={{ fontSize: '13px', color: '#6b7280', fontWeight: 500, marginBottom: '0.25rem', whiteSpace: 'nowrap' }}>{timeString}</div>
                                                            <div style={{ fontWeight: 700, color: '#1f2937', whiteSpace: 'nowrap', fontSize: '14px' }}>{dateString}</div>
                                                        </div>

                                                        {/* Middle Column: Icon & Line */}
                                                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start', marginTop: '0.75rem', position: 'relative', marginRight: '1.5rem' }}>
                                                            {/* Connector Line spanning downwards to next item */}
                                                            {!isLast && (
                                                                <div style={{ position: 'absolute', top: '28px', bottom: '-28px', width: '2px', backgroundColor: '#148384', height: 'calc(100% + 24px)', zIndex: 0 }}></div>
                                                            )}

                                                            {/* Checkmark Circle */}
                                                            <div style={{ width: '24px', height: '24px', borderRadius: '50%', backgroundColor: '#148384', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)', zIndex: 10, position: 'relative', flexShrink: 0 }}>
                                                                <svg style={{ width: '14px', height: '14px', color: 'white' }} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7"></path>
                                                                </svg>
                                                            </div>
                                                        </div>

                                                        {/* Right Column: Stage Card */}
                                                        <div style={{ width: '60%', backgroundColor: 'white', border: '1px solid #d1d5db', borderRadius: '12px', padding: '1rem', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)', transition: 'box-shadow 0.2s', flexShrink: 0 }}>
                                                            <div style={{ color: '#4b5563', fontWeight: 500, fontSize: '13px', marginBottom: '0.25rem' }}>Status Update</div>
                                                            <div style={{ fontSize: '16px', fontWeight: 700, color: '#111827' }}>{history.stage_name}</div>
                                                            {(history.reason || history.changed_by) && (
                                                                <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '0.5rem', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                                                    <span>•</span> System event logged
                                                                </div>
                                                            )}
                                                        </div>

                                                    </div>
                                                );
                                            })
                                        )}
                                    </div>
                                </div>

                                {app.next_step && (
                                    <div className="mt-6 bg-blue-50 p-4 rounded-lg flex items-start border border-blue-100">
                                        <span className="text-blue-500 mr-2">ℹ️</span>
                                        <div>
                                            <h4 className="text-sm font-semibold text-blue-800">Next Step</h4>
                                            <p className="text-sm text-blue-700">{app.next_step}</p>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

// Helper functions for styles
const getStatusColor = (status) => {
    if (!status) return 'bg-blue-100 text-blue-700 border-blue-200';
    const lower = status.toLowerCase();
    if (lower.includes('hired')) return 'bg-green-100 text-green-700 border-green-200';
    if (lower.includes('reject') || lower.includes('not select')) return 'bg-red-100 text-red-700 border-red-200';
    if (lower.includes('offer')) return 'bg-purple-100 text-purple-700 border-purple-200';
    if (lower.includes('withdraw')) return 'bg-gray-100 text-gray-700 border-gray-200';
    return 'bg-blue-100 text-blue-700 border-blue-200';
};

export default ApplicationTracker;
