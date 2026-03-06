import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid, LineChart, Line } from 'recharts';
import { FiUsers, FiBriefcase, FiTrendingUp, FiSearch } from 'react-icons/fi';
import { analyticsService } from '../../services/analyticsService';

const RecruiterAnalytics = ({ data }) => {
    const { active_jobs, total_applicants, active_interviews, job_performance } = data;
    const [selectedJob, setSelectedJob] = useState(null);
    const [funnelData, setFunnelData] = useState(null);

    useEffect(() => {
        if (job_performance && job_performance.length > 0) {
            handleJobSelect(job_performance[0].id);
        }
    }, [job_performance]);

    const handleJobSelect = async (jobId) => {
        try {
            const data = await analyticsService.getJobFunnel(jobId);
            setSelectedJob(data);

            // Transform metrics for chart
            const metrics = data.metrics;
            const chartData = [
                { name: 'Views', value: metrics.views },
                { name: 'Applied', value: metrics.applications },
                { name: 'Interviews', value: metrics.interviews },
                { name: 'Offers', value: metrics.offers },
                { name: 'Hires', value: metrics.hires },
            ];
            setFunnelData(chartData);
        } catch (err) {
            console.error("Failed to load funnel", err);
        }
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* Top Stats */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem' }}>
                <div title="Number of job listings currently published and accepting applications" style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)', border: '1px solid #f3f4f6', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                        <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '0.25rem' }}>Active Jobs</p>
                        <h3 style={{ fontSize: '1.875rem', fontWeight: 700, color: '#1f2937', margin: 0 }}>{active_jobs}</h3>
                        <p style={{ color: '#9ca3af', fontSize: '0.7rem', margin: '4px 0 0' }}>Currently accepting applications</p>
                    </div>
                    <div style={{ backgroundColor: '#eff6ff', padding: '0.75rem', borderRadius: '9999px', color: '#2563eb' }}>
                        <FiBriefcase size={24} />
                    </div>
                </div>
                <div title="Total unique students who have applied across all your job listings" style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)', border: '1px solid #f3f4f6', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                        <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '0.25rem' }}>Total Applicants</p>
                        <h3 style={{ fontSize: '1.875rem', fontWeight: 700, color: '#1f2937', margin: 0 }}>{total_applicants}</h3>
                        <p style={{ color: '#9ca3af', fontSize: '0.7rem', margin: '4px 0 0' }}>Across all job postings</p>
                    </div>
                    <div style={{ backgroundColor: '#faf5ff', padding: '0.75rem', borderRadius: '9999px', color: '#9333ea' }}>
                        <FiUsers size={24} />
                    </div>
                </div>
                <div title="Active mock and real interviews scheduled or in progress" style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)', border: '1px solid #f3f4f6', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                        <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '0.25rem' }}>Interviews</p>
                        <h3 style={{ fontSize: '1.875rem', fontWeight: 700, color: '#1f2937', margin: 0 }}>{active_interviews}</h3>
                        <p style={{ color: '#9ca3af', fontSize: '0.7rem', margin: '4px 0 0' }}>Active or scheduled</p>
                    </div>
                    <div style={{ backgroundColor: '#fff7ed', padding: '0.75rem', borderRadius: '9999px', color: '#ea580c' }}>
                        <FiTrendingUp size={24} />
                    </div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
                {/* Job Performance List */}
                <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)', border: '1px solid #f3f4f6' }}>
                    <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem' }}>Active Jobs</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        {job_performance.map(job => (
                            <div
                                key={job.id}
                                onClick={() => handleJobSelect(job.id)}
                                style={{
                                    padding: '0.75rem', borderRadius: '8px', cursor: 'pointer', transition: 'colors 0.2s', border: '1px solid',
                                    backgroundColor: selectedJob?.job_title === job.title ? '#eff6ff' : '#f9fafb',
                                    borderColor: selectedJob?.job_title === job.title ? '#bfdbfe' : 'transparent',
                                }}
                            >
                                <h4 style={{ fontWeight: 500, color: '#111827', margin: 0, textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>{job.title}</h4>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem' }}>
                                    <span>{new Date(job.posted_at).toLocaleDateString()}</span>
                                    <span>{job.applicants} Applicants</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Funnel Chart */}
                <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '12px', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)', border: '1px solid #f3f4f6', gridColumn: 'auto / span 2' }}>
                    <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem' }}>
                        Hiring Funnel: {selectedJob ? selectedJob.job_title : 'Select a Job'}
                    </h3>
                    <div style={{ height: '320px' }}>
                        {funnelData ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={funnelData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                    <XAxis dataKey="name" />
                                    <YAxis />
                                    <Tooltip
                                        cursor={{ fill: 'transparent' }}
                                        contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                                    />
                                    <Bar dataKey="value" fill="#4F46E5" radius={[4, 4, 0, 0]} barSize={50} />
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af' }}>
                                Select a job to view funnel metrics
                            </div>
                        )}
                    </div>
                    {selectedJob && (
                        <div style={{ marginTop: '1rem', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', textAlign: 'center', fontSize: '0.875rem' }}>
                            <div title="Percentage of viewers who submit an application">
                                <span style={{ display: 'block', color: '#6b7280' }}>View → Apply</span>
                                <span style={{ fontWeight: 600, fontSize: '1.1rem' }}>{selectedJob.conversion_rates.view_to_apply || 0}%</span>
                                <span style={{ display: 'block', color: '#9ca3af', fontSize: '0.7rem' }}>Viewers converting</span>
                            </div>
                            <div title="Percentage of applicants advanced to interview stage">
                                <span style={{ display: 'block', color: '#6b7280' }}>Apply → Interview</span>
                                <span style={{ fontWeight: 600, fontSize: '1.1rem' }}>{selectedJob.conversion_rates.apply_to_interview || 0}%</span>
                                <span style={{ display: 'block', color: '#9ca3af', fontSize: '0.7rem' }}>Screened through</span>
                            </div>
                            <div title="Percentage of interviewed candidates who receive an offer">
                                <span style={{ display: 'block', color: '#6b7280' }}>Interview → Offer</span>
                                <span style={{ fontWeight: 600, fontSize: '1.1rem' }}>{selectedJob.conversion_rates.interview_to_offer || 0}%</span>
                                <span style={{ display: 'block', color: '#9ca3af', fontSize: '0.7rem' }}>Successful interviews</span>
                            </div>
                            <div title="Percentage of offers accepted by candidates">
                                <span style={{ display: 'block', color: '#6b7280' }}>Offer → Hire</span>
                                <span style={{ fontWeight: 600, fontSize: '1.1rem' }}>{selectedJob.conversion_rates.offer_to_hire || 0}%</span>
                                <span style={{ display: 'block', color: '#9ca3af', fontSize: '0.7rem' }}>Offers accepted</span>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default RecruiterAnalytics;
