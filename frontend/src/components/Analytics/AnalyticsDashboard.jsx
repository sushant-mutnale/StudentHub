import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { analyticsService } from '../../services/analyticsService';
import StudentAnalytics from './StudentAnalytics';
import RecruiterAnalytics from './RecruiterAnalytics';
import SidebarLeft from '../SidebarLeft';
import { FiLoader } from 'react-icons/fi';

const AnalyticsDashboard = () => {
    const { user } = useAuth();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const loadAnalytics = async () => {
            if (!user) return;

            setLoading(true);
            try {
                let result;
                if (user.role === 'student') {
                    result = await analyticsService.getStudentOverview();
                } else if (user.role === 'recruiter') {
                    result = await analyticsService.getRecruiterOverview();
                }
                setData(result);
            } catch (err) {
                console.error("Failed to load analytics:", err);
                setError("Failed to load analytics data.");
            } finally {
                setLoading(false);
            }
        };

        loadAnalytics();
    }, [user]);

    if (loading) {
        return (
            <div className="dashboard-container">
                <SidebarLeft />
                <div className="dashboard-main" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
                    <FiLoader className="loading-spinner" size={32} />
                </div>
            </div>
        );
    }

    return (
        <div className="dashboard-container">
            <SidebarLeft />
            <div className="dashboard-main">
                <div className="dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h1 className="dashboard-title">Analytics Dashboard</h1>
                    <span style={{ backgroundColor: '#e0e7ff', color: '#3730a3', fontSize: '0.75rem', fontWeight: 600, padding: '0.25rem 0.5rem', borderRadius: '4px', textTransform: 'capitalize' }}>
                        {user?.role} View
                    </span>
                </div>

                <div className="dashboard-content">
                    {error ? (
                        <div style={{ backgroundColor: '#fee2e2', color: '#b91c1c', padding: '1rem', borderRadius: '8px' }}>
                            {error}
                        </div>
                    ) : (
                        <>
                            {user?.role === 'student' && <StudentAnalytics data={data} />}
                            {user?.role === 'recruiter' && <RecruiterAnalytics data={data} />}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

export default AnalyticsDashboard;
