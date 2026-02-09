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
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                                             {/* Application Status Chart */}
                                             <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                                                            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                                                                           <FiBriefcase /> Application Status
                                                            </h3>
                                                            <div className="h-64">
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
                                                                                          <div className="h-full flex items-center justify-center text-gray-400">
                                                                                                         No applications yet
                                                                                          </div>
                                                                           )}
                                                            </div>
                                                            <div className="mt-4 grid grid-cols-2 gap-4 text-center">
                                                                           <div className="bg-blue-50 p-2 rounded">
                                                                                          <span className="block text-2xl font-bold text-blue-600">{applications.total}</span>
                                                                                          <span className="text-xs text-blue-600">Total Applications</span>
                                                                           </div>
                                                                           <div className="bg-green-50 p-2 rounded">
                                                                                          <span className="block text-2xl font-bold text-green-600">{applications.offered}</span>
                                                                                          <span className="text-xs text-green-600">Offers</span>
                                                                           </div>
                                                            </div>
                                             </div>

                                             {/* Recent Activity */}
                                             <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                                                            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                                                                           <FiActivity /> Recent Activity
                                                            </h3>
                                                            <div className="space-y-4">
                                                                           {recent_activity.map((activity, index) => (
                                                                                          <div key={index} className="flex items-start gap-3 pb-3 border-b border-gray-50 last:border-0">
                                                                                                         <div className="bg-blue-100 p-2 rounded-full text-blue-600 mt-1">
                                                                                                                        <FiActivity size={12} />
                                                                                                         </div>
                                                                                                         <div>
                                                                                                                        <p className="text-sm font-medium text-gray-800">{activity.description}</p>
                                                                                                                        <p className="text-xs text-gray-500">
                                                                                                                                       {new Date(activity.timestamp).toLocaleDateString()} at {new Date(activity.timestamp).toLocaleTimeString()}
                                                                                                                        </p>
                                                                                                         </div>
                                                                                          </div>
                                                                           ))}
                                                                           {recent_activity.length === 0 && (
                                                                                          <p className="text-gray-400 text-center py-4">No recent activity found.</p>
                                                                           )}
                                                            </div>
                                             </div>
                              </div>
               );
};

export default StudentAnalytics;
