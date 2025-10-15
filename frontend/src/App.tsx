import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { ChatProvider } from "./contexts/ChatContext";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { Chat } from "./pages/Chat";

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/chat"
            element={
              <ProtectedRoute>
                <ChatProvider>
                  <Chat />
                </ChatProvider>
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<Navigate to="/chat" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
