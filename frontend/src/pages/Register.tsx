// ABOUTME: Registration page for creating new user accounts
// ABOUTME: Simple form with username, email, password, and full name fields

import React, { useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { useNavigate, Link } from "react-router-dom";

export const Register: React.FC = () => {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await register({ username, email, password, full_name: fullName });
      navigate("/chat");
    } catch (err: any) {
      setError(err.message || "Registration failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded-lg shadow">
        <h1 className="text-2xl font-bold mb-6 text-gray-900">Create Account</h1>

        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-600 rounded text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Username"
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
            />
          </div>

          <div>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
            />
          </div>

          <div>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Full Name"
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
            />
          </div>

          <div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              required
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300"
          >
            {isLoading ? "Creating account..." : "Register"}
          </button>
        </form>

        <div className="mt-4 text-center text-sm text-gray-600">
          Already have an account?{" "}
          <Link to="/login" className="text-blue-500 hover:underline">
            Login
          </Link>
        </div>
      </div>
    </div>
  );
};
