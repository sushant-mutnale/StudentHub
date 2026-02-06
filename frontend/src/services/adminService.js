import axios from 'axios';

const API_URL = 'https://studenthub-i7pa.onrender.com';

const getAuthHeader = () => {
               const token = localStorage.getItem('token');
               return { headers: { Authorization: `Bearer ${token}` } };
};

export const adminService = {
               // Get review queue
               getReviewQueue: async (type = null) => {
                              const url = type ? `${API_URL}/admin/review-queue?type_filter=${type}` : `${API_URL}/admin/review-queue`;
                              const response = await axios.get(url, getAuthHeader());
                              return response.data;
               },

               // Approve job
               approveJob: async (jobId) => {
                              const response = await axios.post(`${API_URL}/admin/jobs/${jobId}/approve`, {}, getAuthHeader());
                              return response.data;
               },

               // Reject job
               rejectJob: async (jobId, reason) => {
                              const response = await axios.post(`${API_URL}/admin/jobs/${jobId}/reject`, { reason }, getAuthHeader());
                              return response.data;
               },

               // Verify recruiter
               verifyRecruiter: async (recruiterId) => {
                              const response = await axios.post(`${API_URL}/admin/recruiters/${recruiterId}/verify`, {}, getAuthHeader());
                              return response.data;
               },

               // Suspend recruiter
               suspendRecruiter: async (recruiterId, reason) => {
                              const response = await axios.post(`${API_URL}/admin/recruiters/${recruiterId}/suspend`, { reason }, getAuthHeader());
                              return response.data;
               },

               // Get verification status (for recruiter)
               getVerificationStatus: async () => {
                              const response = await axios.get(`${API_URL}/verification/status`, getAuthHeader());
                              return response.data;
               },

               // Request verification
               requestVerification: async (data) => {
                              const response = await axios.post(`${API_URL}/verification/request`, data, getAuthHeader());
                              return response.data;
               }
};
