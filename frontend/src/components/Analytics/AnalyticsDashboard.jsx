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
                                             <div className="flex h-screen bg-gray-50">
                                                            <SidebarLeft />
                                                            <div className="flex-1 flex items-center justify-center">
                                                                           <FiLoader className="animate-spin text-blue-600" size={32} />
                                                            </div>
                                             </div>
                              );
               }

               return (
                              <div className="flex h-screen bg-gray-50 overflow-hidden">
                                             <SidebarLeft />
                                             <div className="flex-1 overflow-auto">
                                                            <header className="bg-white shadow-sm sticky top-0 z-10">
                                                                           <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
                                                                                          <h1 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h1>
                                                                                          <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded capitalize">
                                                                                                         {user?.role} View
                                                                                          </span>
                                                                           </div>
                                                            </header>

                                                            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                                                                           {error ? (
                                                                                          <div className="bg-red-50 text-red-700 p-4 rounded-lg">
                                                                                                         {error}
                                                                                          </div>
                                                                           ) : (
                                                                                          <>
                                                                                                         {user?.role === 'student' && <StudentAnalytics data={data} />}
                                                                                                         {user?.role === 'recruiter' && <RecruiterAnalytics data={data} />}
                                                                                          </>
                                                                           )}
                                                            </main>
                                             </div>
                              </div>
               );
};

export default AnalyticsDashboard;
