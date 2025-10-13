// ABOUTME: Authentication service for API calls (login, register, token management)
// ABOUTME: Handles localStorage token persistence and axios configuration

import axios from 'axios';
import type { User, LoginRequest, RegisterRequest, TokenResponse } from '../types/auth';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const TOKEN_KEY = 'genesis_access_token';

export class AuthService {
  private static instance: AuthService;

  private constructor() {}

  static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
  }

  removeToken(): void {
    localStorage.removeItem(TOKEN_KEY);
  }

  async register(data: RegisterRequest): Promise<User> {
    try {
      const response = await axios.post<User>(`${API_URL}/api/auth/register`, data);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response) {
        throw new Error(error.response.data.detail || 'Registration failed');
      }
      throw new Error('Registration failed');
    }
  }

  async login(data: LoginRequest): Promise<TokenResponse> {
    try {
      const formData = new URLSearchParams();
      formData.append('username', data.username);
      formData.append('password', data.password);

      const response = await axios.post<TokenResponse>(
        `${API_URL}/api/auth/token`,
        formData,
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }
      );

      this.setToken(response.data.access_token);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response) {
        throw new Error(error.response.data.detail || 'Login failed');
      }
      throw new Error('Login failed');
    }
  }

  async getCurrentUser(): Promise<User> {
    const token = this.getToken();
    if (!token) {
      throw new Error('No authentication token found');
    }

    try {
      const response = await axios.get<User>(`${API_URL}/api/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      return response.data;
    } catch (error) {
      this.removeToken();
      if (axios.isAxiosError(error) && error.response) {
        throw new Error(error.response.data.detail || 'Failed to get user info');
      }
      throw new Error('Failed to get user info');
    }
  }

  logout(): void {
    this.removeToken();
  }
}

export const authService = AuthService.getInstance();
