/**
 * Adizon Admin API Client
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const ADMIN_TOKEN = import.meta.env.VITE_ADMIN_TOKEN || 'your_admin_token_here';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${ADMIN_TOKEN}`
  }
});

// === TYPES ===

export interface User {
  id: string;
  email: string;
  name: string;
  telegram_id?: string;
  slack_id?: string;
  is_active: boolean;
  is_approved: boolean;
  role: string;
  crm_display_name: string;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  email: string;
  name: string;
  crm_display_name?: string;
  telegram_id?: string;
  slack_id?: string;
  is_approved?: boolean;
  role?: string;
}

export interface UserUpdate {
  email?: string;
  name?: string;
  crm_display_name?: string;
  telegram_id?: string;
  slack_id?: string;
  is_active?: boolean;
  is_approved?: boolean;
  role?: string;
}

export interface Stats {
  total_users: number;
  active_users: number;
  pending_users: number;
}

// === API CALLS ===

export const userApi = {
  // Get all users
  getAll: async (skip: number = 0, limit: number = 100): Promise<User[]> => {
    const response = await api.get(`/api/users?skip=${skip}&limit=${limit}`);
    return response.data;
  },

  // Get pending users
  getPending: async (): Promise<User[]> => {
    const response = await api.get('/api/users/pending');
    return response.data;
  },

  // Get statistics
  getStats: async (): Promise<Stats> => {
    const response = await api.get('/api/users/stats');
    return response.data;
  },

  // Get single user
  getById: async (id: string): Promise<User> => {
    const response = await api.get(`/api/users/${id}`);
    return response.data;
  },

  // Create user
  create: async (data: UserCreate): Promise<User> => {
    const response = await api.post('/api/users', data);
    return response.data;
  },

  // Update user
  update: async (id: string, data: UserUpdate): Promise<User> => {
    const response = await api.patch(`/api/users/${id}`, data);
    return response.data;
  },

  // Approve user
  approve: async (id: string): Promise<User> => {
    const response = await api.post(`/api/users/${id}/approve`);
    return response.data;
  },

  // Link platform
  linkPlatform: async (id: string, platform: string, platformId: string): Promise<User> => {
    const response = await api.post(`/api/users/${id}/link`, null, {
      params: { platform, platform_id: platformId }
    });
    return response.data;
  },

  // Delete user
  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/users/${id}`);
  }
};

