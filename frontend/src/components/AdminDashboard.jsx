import React, { useState, useEffect } from 'react';
import { adminService } from '../services/adminService';
import { FaCheck, FaTimes, FaExclamationTriangle, FaShieldAlt } from 'react-icons/fa';

const AdminDashboard = () => {
               const [activeTab, setActiveTab] = useState('jobs'); // jobs, recruiters
               const [items, setItems] = useState([]);
               const [loading, setLoading] = useState(true);

               useEffect(() => {
                              loadReviewQueue();
               }, [activeTab]);

               const loadReviewQueue = async () => {
                              setLoading(true);
                              try {
                                             const filter = activeTab === 'jobs' ? 'job' : 'recruiter';
                                             const data = await adminService.getReviewQueue(filter);
                                             setItems(data.items);
                              } catch (error) {
                                             console.error("Failed to load review queue", error);
                              } finally {
                                             setLoading(false);
                              }
               };

               const handleApprove = async (id) => {
                              try {
                                             if (activeTab === 'jobs') {
                                                            await adminService.approveJob(id);
                                             } else {
                                                            await adminService.verifyRecruiter(id);
                                             }
                                             // Remove from list
                                             setItems(items.filter(i => i.id !== id));
                              } catch (error) {
                                             alert("Action failed: " + error.message);
                              }
               };

               const handleReject = async (id) => {
                              const reason = prompt("Enter reason for rejection/suspension:");
                              if (!reason) return;

                              try {
                                             if (activeTab === 'jobs') {
                                                            await adminService.rejectJob(id, reason);
                                             } else {
                                                            await adminService.suspendRecruiter(id, reason);
                                             }
                                             setItems(items.filter(i => i.id !== id));
                              } catch (error) {
                                             alert("Action failed: " + error.message);
                              }
               };

               return (
                              <div className="p-6 bg-gray-50 min-h-screen">
                                             <header className="mb-8 flex justify-between items-center">
                                                            <div>
                                                                           <h1 className="text-2xl font-bold text-gray-800 flex items-center">
                                                                                          <FaShieldAlt className="mr-2 text-blue-600" />
                                                                                          Admin Governance
                                                                           </h1>
                                                                           <p className="text-gray-500">Moderation Queue & Verification</p>
                                                            </div>
                                             </header>

                                             {/* Tabs */}
                                             <div className="flex border-b mb-6">
                                                            <button
                                                                           className={`px-6 py-3 font-medium ${activeTab === 'jobs' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
                                                                           onClick={() => setActiveTab('jobs')}
                                                            >
                                                                           Job Postings ({activeTab === 'jobs' ? items.length : '?'})
                                                            </button>
                                                            <button
                                                                           className={`px-6 py-3 font-medium ${activeTab === 'recruiters' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
                                                                           onClick={() => setActiveTab('recruiters')}
                                                            >
                                                                           Recruiter Verification ({activeTab === 'recruiters' ? items.length : '?'})
                                                            </button>
                                             </div>

                                             {/* Content */}
                                             {loading ? (
                                                            <div className="p-12 text-center text-gray-500">Loading queue...</div>
                                             ) : items.length === 0 ? (
                                                            <div className="p-12 text-center bg-white rounded shadow-sm">
                                                                           <div className="text-green-500 text-6xl mb-4">✓</div>
                                                                           <h3 className="text-lg font-medium text-gray-800">All caught up!</h3>
                                                                           <p className="text-gray-500">No items pending review.</p>
                                                            </div>
                                             ) : (
                                                            <div className="space-y-4">
                                                                           {items.map(item => (
                                                                                          <div key={item.id} className="bg-white p-6 rounded-lg shadow-sm border border-gray-100 flex justify-between items-start">
                                                                                                         <div className="flex-1">
                                                                                                                        <div className="flex items-center mb-2">
                                                                                                                                       <h3 className="text-lg font-bold text-gray-900 mr-3">{item.title}</h3>
                                                                                                                                       {item.risk_score > 50 && (
                                                                                                                                                      <span className="bg-red-100 text-red-700 px-2 py-0.5 rounded text-xs font-semibold flex items-center">
                                                                                                                                                                     <FaExclamationTriangle className="mr-1" /> High Risk ({item.risk_score})
                                                                                                                                                      </span>
                                                                                                                                       )}
                                                                                                                        </div>
                                                                                                                        <p className="text-gray-600 mb-4">{item.company_name}</p>

                                                                                                                        {item.flags && item.flags.length > 0 && (
                                                                                                                                       <div className="bg-yellow-50 p-3 rounded text-sm text-yellow-800 mb-4">
                                                                                                                                                      <p className="font-semibold mb-1">Risk Flags:</p>
                                                                                                                                                      <ul className="list-disc pl-5">
                                                                                                                                                                     {item.flags.map((flag, idx) => (
                                                                                                                                                                                    <li key={idx}>{flag.reason} (Score: {flag.score})</li>
                                                                                                                                                                     ))}
                                                                                                                                                      </ul>
                                                                                                                                       </div>
                                                                                                                        )}

                                                                                                                        <p className="text-xs text-gray-400">Created: {new Date(item.created_at).toLocaleString()}</p>
                                                                                                         </div>

                                                                                                         <div className="flex gap-3 ml-4">
                                                                                                                        <button
                                                                                                                                       onClick={() => handleReject(item.id)}
                                                                                                                                       className="px-4 py-2 border border-red-200 text-red-600 rounded hover:bg-red-50 flex items-center"
                                                                                                                        >
                                                                                                                                       <FaTimes className="mr-2" /> Reject
                                                                                                                        </button>
                                                                                                                        <button
                                                                                                                                       onClick={() => handleApprove(item.id)}
                                                                                                                                       className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 flex items-center shadow-sm"
                                                                                                                        >
                                                                                                                                       <FaCheck className="mr-2" /> Approve
                                                                                                                        </button>
                                                                                                         </div>
                                                                                          </div>
                                                                           ))}
                                                            </div>
                                             )}
                              </div>
               );
};

export default AdminDashboard;
