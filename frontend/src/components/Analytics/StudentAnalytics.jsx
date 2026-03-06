import React from 'react';
import { PieChart, Pie, Cell, Tooltip, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts';
import { FiActivity, FiTarget, FiBriefcase } from 'react-icons/fi';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

const StudentAnalytics = ({ data }) => {
    const { applications, recent_activity } = data;

    const appData = [
        { name: 'Applied', value: applications.applied },
        { name: 'Interviewing', value: applications.interviewing },
        { name: 'Offered', value: applications.offered },
        { name: 'Rejected', value: applications.rejected },
    ].filter(item => item.value > 0);

    return (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>

            {/* Application Status Chart */}
            <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)', border: '1px solid #f3f4f6' }}>
                <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <FiBriefcase /> Application Status
                </h3>
                <p style={{ fontSize: '0.75rem', color: '#9ca3af', margin: '0 0 1rem' }}>Breakdown of where your applications stand across all jobs</p>
                <div style={{ height: '250px' }}>
                    {appData.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={appData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={80}
                                    paddingAngle={5}
                                    dataKey="value"
                                >
                                    {appData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip />
                                <Legend />
                            </PieChart>
                        </ResponsiveContainer>
                    ) : (
                        <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af' }}>
                            No applications yet
                        </div>
                    )}
                </div>
                <div style={{ marginTop: '1rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', textAlign: 'center' }}>
                    <div title="Sum of all job applications submitted" style={{ backgroundColor: '#eff6ff', padding: '0.5rem', borderRadius: '4px' }}>
                        <span style={{ display: 'block', fontSize: '1.5rem', lineHeight: '2rem', fontWeight: 700, color: '#2563eb' }}>{applications.total}</span>
                        <span style={{ fontSize: '0.75rem', lineHeight: '1rem', color: '#2563eb' }}>Total Applications</span>
                    </div>
                    <div title="Applications that reached the offer stage" style={{ backgroundColor: '#f0fdf4', padding: '0.5rem', borderRadius: '4px' }}>
                        <span style={{ display: 'block', fontSize: '1.5rem', lineHeight: '2rem', fontWeight: 700, color: '#16a34a' }}>{applications.offered}</span>
                        <span style={{ fontSize: '0.75rem', lineHeight: '1rem', color: '#16a34a' }}>Offers</span>
                    </div>
                </div>
            </div>

            {/* Recent Activity */}
            <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)', border: '1px solid #f3f4f6' }}>
                <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <FiActivity /> Recent Activity
                </h3>
                <p style={{ fontSize: '0.75rem', color: '#9ca3af', margin: '0 0 1rem' }}>Your latest actions: applications, interviews, and skill assessments</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {recent_activity.map((activity, index) => (
                        <div key={index} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', paddingBottom: '0.75rem', borderBottom: index === recent_activity.length - 1 ? 'none' : '1px solid #f9fafb' }}>
                            <div style={{ backgroundColor: '#dbeafe', padding: '0.5rem', borderRadius: '9999px', color: '#2563eb', marginTop: '0.25rem' }}>
                                <FiActivity size={12} />
                            </div>
                            <div>
                                <p style={{ fontSize: '0.875rem', lineHeight: '1.25rem', fontWeight: 500, color: '#1f2937', margin: 0 }}>{activity.description}</p>
                                <p style={{ fontSize: '0.75rem', lineHeight: '1rem', color: '#6b7280', margin: 0 }}>
                                    {new Date(activity.timestamp).toLocaleDateString()} at {new Date(activity.timestamp).toLocaleTimeString()}
                                </p>
                            </div>
                        </div>
                    ))}
                    {recent_activity.length === 0 && (
                        <p style={{ color: '#9ca3af', textAlign: 'center', padding: '1rem 0' }}>No recent activity found.</p>
                    )}
                </div>
            </div>
        </div>
    );
};

export default StudentAnalytics;
