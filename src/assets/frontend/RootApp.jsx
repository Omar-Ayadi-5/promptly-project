import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import Body from "./body.jsx";
import Sign from "./Sign-in-up.jsx";
import MyProfile from "./components/MyProfile.jsx";
import Settings from './components/Settings.jsx';
import { AuthProvider } from './AuthContext.jsx';
import { useAuth } from './authContext';

function ProtectedRoute({ children }) {
  const { token, loading } = useAuth();

  if (loading) {
    return <p>Loading...</p>;
  }

  if (!token) {
    return <Navigate to="/" replace />;
  }

  return children;
}

function RootApp() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Sign />} />
          <Route
            path="/app"
            element={
              <ProtectedRoute>
                <Body />
              </ProtectedRoute>
            }
          />
          <Route
            path="/MyProfile"
            element={
              <ProtectedRoute>
                <MyProfile />
              </ProtectedRoute>
            }
          />
        <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <Settings />
              </ProtectedRoute>
            }
          />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default RootApp;
