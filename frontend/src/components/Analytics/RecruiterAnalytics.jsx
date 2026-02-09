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
                              <div className="space-y-6">
                                             {/* Top Stats */}
                                             <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                                            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
                                                                           <div>
                                                                                          <p className="text-gray-500 text-sm">Active Jobs</p>
                                                                                          <h3 className="text-3xl font-bold text-gray-800">{active_jobs}</h3>
                                                                           </div>
                                                                           <div className="bg-blue-50 p-3 rounded-full text-blue-600">
                                                                                          <FiBriefcase size={24} />
                                                                           </div>
                                                            </div>
                                                            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
                                                                           <div>
                                                                                          <p className="text-gray-500 text-sm">Total Applicants</p>
                                                                                          <h3 className="text-3xl font-bold text-gray-800">{total_applicants}</h3>
                                                                           </div>
                                                                           <div className="bg-purple-50 p-3 rounded-full text-purple-600">
                                                                                          <FiUsers size={24} />
                                                                           </div>
                                                            </div>
                                                            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
                                                                           <div>
                                                                                          <p className="text-gray-500 text-sm">Interviews</p>
                                                                                          <h3 className="text-3xl font-bold text-gray-800">{active_interviews}</h3>
                                                                           </div>
                                                                           <div className="bg-orange-50 p-3 rounded-full text-orange-600">
                                                                                          <FiTrendingUp size={24} />
                                                                           </div>
                                                            </div>
                                             </div>

                                             <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                                            {/* Job Performance List */}
                                                            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 lg:col-span-1">
                                                                           <h3 className="text-lg font-semibold mb-4">Active Jobs</h3>
                                                                           <div className="space-y-3">
                                                                                          {job_performance.map(job => (
                                                                                                         <div
                                                                                                                        key={job.id}
                                                                                                                        onClick={() => handleJobSelect(job.id)}
                                                                                                                        className={`p-3 rounded-lg cursor-pointer transition-colors border ${selectedJob?.job_title === job.title ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-transparent hover:bg-gray-100'}`}
                                                                                                         >
                                                                                                                        <h4 className="font-medium text-gray-900 truncate">{job.title}</h4>
                                                                                                                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                                                                                                                                       <span>{new Date(job.posted_at).toLocaleDateString()}</span>
                                                                                                                                       <span>{job.applicants} Applicants</span>
                                                                                                                        </div>
                                                                                                         </div>
                                                                                          ))}
                                                                           </div>
                                                            </div>

                                                            {/* Funnel Chart */}
                                                            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 lg:col-span-2">
                                                                           <h3 className="text-lg font-semibold mb-4">
                                                                                          Hiring Funnel: {selectedJob ? selectedJob.job_title : 'Select a Job'}
                                                                           </h3>
                                                                           <div className="h-80">
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
                                                                                                         <div className="h-full flex items-center justify-center text-gray-400">
                                                                                                                        Select a job to view funnel metrics
                                                                                                         </div>
                                                                                          )}
                                                                           </div>
                                                                           {selectedJob && (
                                                                                          <div className="mt-4 grid grid-cols-4 gap-4 text-center text-sm">
                                                                                                         <div>
                                                                                                                        <span className="block text-gray-500">View to Apply</span>
                                                                                                                        <span className="font-semibold">{selectedJob.conversion_rates.view_to_apply || 0}%</span>
                                                                                                         </div>
                                                                                                         <div>
                                                                                                                        <span className="block text-gray-500">Apply to Interview</span>
                                                                                                                        <span className="font-semibold">{selectedJob.conversion_rates.apply_to_interview || 0}%</span>
                                                                                                         </div>
                                                                                                         <div>
                                                                                                                        <span className="block text-gray-500">Interview to Offer</span>
                                                                                                                        <span className="font-semibold">{selectedJob.conversion_rates.interview_to_offer || 0}%</span>
                                                                                                         </div>
                                                                                                         <div>
                                                                                                                        <span className="block text-gray-500">Offer to Hire</span>
                                                                                                                        <span className="font-semibold">{selectedJob.conversion_rates.offer_to_hire || 0}%</span>
                                                                                                         </div>
                                                                                          </div>
                                                                           )}
                                                            </div>
                                             </div>
                              </div>
               );
};

export default RecruiterAnalytics;
