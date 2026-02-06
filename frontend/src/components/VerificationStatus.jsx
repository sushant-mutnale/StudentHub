import React, { useState, useEffect } from 'react';
import { adminService } from '../services/adminService';
import { FaCheckCircle, FaExclamationTriangle, FaLock } from 'react-icons/fa';

const VerificationStatus = () => {
               const [statusData, setStatusData] = useState(null);
               const [loading, setLoading] = useState(true);

               useEffect(() => {
                              loadStatus();
               }, []);

               const loadStatus = async () => {
                              try {
                                             const data = await adminService.getVerificationStatus();
                                             setStatusData(data);
                              } catch (error) {
                                             console.error("Failed to load status", error);
                              } finally {
                                             setLoading(false);
                              }
               };

               const handleRequest = async (e) => {
                              e.preventDefault();
                              const formData = new FormData(e.target);
                              const payload = {
                                             company_website: formData.get('website'),
                                             company_description: formData.get('description'),
                                             additional_info: formData.get('info')
                              };

                              try {
                                             await adminService.requestVerification(payload);
                                             loadStatus(); // Reload
                              } catch (error) {
                                             alert("Request failed");
                              }
               };

               if (loading) return <div>Loading status...</div>;

               const isVerified = statusData?.status === 'verified';
               const isPending = statusData?.status === 'review_required';

               return (
                              <div className="bg-white rounded-lg shadow-sm border p-6">
                                             <h2 className="text-xl font-bold text-gray-800 mb-6">Verification Center</h2>

                                             {/* Status Status */}
                                             <div className={`p-4 rounded-lg mb-8 flex items-center ${isVerified ? 'bg-green-50 border-green-200' : 'bg-yellow-50 border-yellow-200'
                                                            }`}>
                                                            <div className={`w-12 h-12 rounded-full flex items-center justify-center mr-4 ${isVerified ? 'bg-green-100 text-green-600' : 'bg-yellow-100 text-yellow-600'
                                                                           }`}>
                                                                           {isVerified ? <FaCheckCircle size={24} /> : <FaLock size={20} />}
                                                            </div>
                                                            <div>
                                                                           <h3 className={`font-bold ${isVerified ? 'text-green-800' : 'text-yellow-800'}`}>
                                                                                          {isVerified ? 'Verified Recruiter' : isPending ? 'Verification Pending' : 'Unverified Account'}
                                                                           </h3>
                                                                           <p className="text-sm text-gray-600">
                                                                                          {isVerified
                                                                                                         ? "Your account is fully verified. You have full access to all features."
                                                                                                         : "Verifying your account builds trust with candidates and unlocks advanced features."}
                                                                           </p>
                                                            </div>
                                             </div>

                                             {/* Trust Score */}
                                             <div className="grid grid-cols-3 gap-4 mb-8">
                                                            <div className="border p-4 rounded text-center">
                                                                           <div className="text-2xl font-bold text-gray-800">{statusData?.trust_score || 0}</div>
                                                                           <div className="text-xs text-gray-500 uppercase tracking-wide">Trust Score</div>
                                                            </div>
                                                            <div className="border p-4 rounded text-center">
                                                                           <div className="text-2xl font-bold text-gray-800">
                                                                                          {statusData?.email_verified ? <span className="text-green-500">Yes</span> : <span className="text-red-500">No</span>}
                                                                           </div>
                                                                           <div className="text-xs text-gray-500 uppercase tracking-wide">Email Verified</div>
                                                            </div>
                                                            <div className="border p-4 rounded text-center">
                                                                           <div className="text-2xl font-bold text-gray-800">
                                                                                          {statusData?.domain_verified ? <span className="text-green-500">Yes</span> : <span className="text-gray-400">No</span>}
                                                                           </div>
                                                                           <div className="text-xs text-gray-500 uppercase tracking-wide">Domain Match</div>
                                                            </div>
                                             </div>

                                             {/* Verification Form */}
                                             {!isVerified && !isPending && (
                                                            <form onSubmit={handleRequest} className="space-y-4">
                                                                           <h4 className="font-semibold text-gray-700">Request Verification</h4>
                                                                           <div>
                                                                                          <label className="block text-sm font-medium text-gray-700">Company Website</label>
                                                                                          <input name="website" type="url" required className="w-full border rounded p-2" placeholder="https://example.com" />
                                                                           </div>
                                                                           <div>
                                                                                          <label className="block text-sm font-medium text-gray-700">Company Description</label>
                                                                                          <textarea name="description" required className="w-full border rounded p-2" rows="3"></textarea>
                                                                           </div>
                                                                           <div>
                                                                                          <label className="block text-sm font-medium text-gray-700">Additional Info</label>
                                                                                          <textarea name="info" className="w-full border rounded p-2" rows="2" placeholder="LinkedIn, Social profiles..."></textarea>
                                                                           </div>
                                                                           <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">
                                                                                          Submit Request
                                                                           </button>
                                                                           <p className="text-xs text-gray-500 text-center mt-2">
                                                                                          <FaExclamationTriangle className="inline mr-1" />
                                                                                          Tip: Use your company email address for instant verification.
                                                                           </p>
                                                            </form>
                                             )}
                              </div>
               );
};

export default VerificationStatus;
