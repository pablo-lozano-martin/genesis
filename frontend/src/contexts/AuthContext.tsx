// ABOUTME: React Context for authentication state management
// ABOUTME: Provides auth state and methods (login, register, logout) to all components

import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import type { User, LoginRequest, RegisterRequest, AuthState } from '../types/auth';
import { authService } from '../services/authService';

interface AuthContextType extends AuthState {
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = authService.getToken();
      if (storedToken) {
        try {
          const currentUser = await authService.getCurrentUser();
          setUser(currentUser);
          setToken(storedToken);
          setIsAuthenticated(true);
        } catch (error) {
          authService.removeToken();
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (data: LoginRequest) => {
    setIsLoading(true);
    try {
      const tokenResponse = await authService.login(data);
      setToken(tokenResponse.access_token);

      const currentUser = await authService.getCurrentUser();
      setUser(currentUser);
      setIsAuthenticated(true);
    } catch (error) {
      setUser(null);
      setToken(null);
      setIsAuthenticated(false);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: RegisterRequest) => {
    setIsLoading(true);
    try {
      await authService.register(data);
      await login({
        username: data.username,
        password: data.password,
      });
    } catch (error) {
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    authService.logout();
    setUser(null);
    setToken(null);
    setIsAuthenticated(false);
  };

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated,
    isLoading,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
