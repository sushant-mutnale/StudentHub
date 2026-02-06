import React, { useState, useEffect } from 'react';
import { applicationService } from '../services/applicationService';
import { FaCheckCircle, FaCircle, FaSpinner, FaTimesCircle } from 'react-icons/fa';

const ApplicationTracker = () => {
               const [applications, setApplications] = useState([]);
               const [loading, setLoading] = useState(true);

               useEffect(() => {
                              loadApplications();
               }, []);

               const loadApplications = async () => {
                              try {
                                             const data = await applicationService.getStudentApplications();
                                             setApplications(data);
                              } catch (error) {
                                             console.error("Failed to load applications", error);
                              } finally {
                                             setLoading(false);
                              }
               };

               if (loading) return <div className="p-8 text-center text-gray-500">Loading your applications...</div>;

               if (applications.length === 0) {
                              return (
                                             <div className="text-center p-12 bg-white rounded-lg shadow-sm">
                                                            <h3 className="text-lg font-semibold text-gray-800 mb-2">No Applications Yet</h3>
                                                            <p className="text-gray-600">Start applying to jobs to track them here!</p>
                                             </div>
                              );
               }

               return (
                              <div className="space-y-6">
                                             <h2 className="text-2xl font-bold text-gray-800">My Applications</h2>

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

                                                                           {/* Timeline */}
                                                                           <div className="relative">
                                                                                          <div className="absolute top-1/2 left-0 w-full h-0.5 bg-gray-200 transform -translate-y-1/2 -z-10"></div>
                                                                                          <div className="flex justify-between items-center w-full px-4">
                                                                                                         {['Applied', 'Screening', 'Interview', 'Offer'].map((step, index) => {
                                                                                                                        const status = getStepStatus(step, app.current_stage_name);
                                                                                                                        return (
                                                                                                                                       <div key={step} className="flex flex-col items-center bg-white px-2">
                                                                                                                                                      <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 ${getStepColor(status)}`}>
                                                                                                                                                                     {getStepIcon(status)}
                                                                                                                                                      </div>
                                                                                                                                                      <span className={`mt-2 text-xs font-medium ${status === 'current' ? 'text-blue-600' : 'text-gray-500'}`}>
                                                                                                                                                                     {step}
                                                                                                                                                      </span>
                                                                                                                                       </div>
                                                                                                                        );
                                                                                                         })}
                                                                                          </div>
                                                                           </div>

                                                                           {app.next_step && (
                                                                                          <div className="mt-6 bg-blue-50 p-4 rounded-lg flex items-start">
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
               );
};

// Helper functions for styles
const getStatusColor = (status) => {
               switch (status.toLowerCase()) {
                              case 'hired': return 'bg-green-100 text-green-700 border-green-200';
                              case 'rejected': return 'bg-red-100 text-red-700 border-red-200';
                              case 'offer': return 'bg-purple-100 text-purple-700 border-purple-200';
                              default: return 'bg-blue-100 text-blue-700 border-blue-200';
               }
};

const getStepStatus = (step, currentStage) => {
               const stages = ['Applied', 'Screening', 'Interview', 'Offer', 'Hired'];
               const currentIndex = stages.indexOf(currentStage) === -1 ? 0 : stages.indexOf(currentStage); // Default to 0 if unknown
               const stepIndex = stages.indexOf(step);

               if (currentStage === 'Rejected') return 'error';
               if (stepIndex < currentIndex) return 'completed';
               if (stepIndex === currentIndex) return 'current';
               return 'pending';
};

const getStepColor = (status) => {
               switch (status) {
                              case 'completed': return 'bg-green-500 border-green-500 text-white';
                              case 'current': return 'bg-white border-blue-500 text-blue-500';
                              case 'error': return 'bg-red-500 border-red-500 text-white';
                              default: return 'bg-white border-gray-300 text-gray-300';
               }
};

const getStepIcon = (status) => {
               switch (status) {
                              case 'completed': return <FaCheckCircle size={14} />;
                              case 'current': return <FaSpinner className="animate-spin" size={14} />;
                              case 'error': return <FaTimesCircle size={14} />;
                              default: return <FaCircle size={8} />;
               }
};

export default ApplicationTracker;
