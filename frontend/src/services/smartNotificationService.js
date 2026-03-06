import { api } from '../api/client';

export const smartNotificationService = {
               // Get my notifications
               getNotifications: async (unreadOnly = false, limit = 20, type = null) => {
                              const params = { unread_only: unreadOnly, limit };
                              if (type) params.notification_type = type;
                              const { data } = await api.get('/smart-notifications/my', { params });
                              return data;
               },

               // Mark as read
               markAsRead: async (notificationId) => {
                              const { data } = await api.post(`/smart-notifications/${notificationId}/mark-read`);
                              return data;
               },

               // Mark all as read
               markAllAsRead: async () => {
                              const { data } = await api.post('/smart-notifications/mark-all-read');
                              return data;
               },

               // Click notification (tracks analytics)
               clickNotification: async (notificationId) => {
                              const { data } = await api.post(`/smart-notifications/${notificationId}/click`);
                              return data;
               },

               // Dismiss notification
               dismissNotification: async (notificationId) => {
                              const { data } = await api.delete(`/smart-notifications/${notificationId}`);
                              return data;
               },

               // Get settings
               getSettings: async () => {
                              const { data } = await api.get('/smart-notifications/settings');
                              return data;
               },

               // Update settings
               updateSettings: async (settings) => {
                              const { data } = await api.put('/smart-notifications/settings', settings);
                              return data;
               },

               // Get stats
               getStats: async () => {
                              const { data } = await api.get('/smart-notifications/stats');
                              return data;
               },

               // Trigger checks manually
               triggerCheck: async (type = 'all') => {
                              const { data } = await api.post(`/smart-notifications/trigger/${type}`);
                              return data;
               }
};
