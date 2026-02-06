import { api as API } from '../api/client';

export const notificationService = {
               getNotifications: async () => {
                              const response = await API.get('/notifications/');
                              return response.data;
               },

               markAsRead: async (notificationId) => {
                              const response = await API.put(`/notifications/${notificationId}/read`);
                              return response.data;
               },

               markAllAsRead: async () => {
                              const response = await API.put('/notifications/read-all');
                              return response.data;
               }
};
