// ABOUTME: Global axios configuration with interceptors
// ABOUTME: Handles 401 errors by triggering automatic logout

import axios from 'axios';

export const setupAxiosInterceptors = (onUnauthorized: () => void) => {
  axios.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        onUnauthorized();
      }
      return Promise.reject(error);
    }
  );
};
