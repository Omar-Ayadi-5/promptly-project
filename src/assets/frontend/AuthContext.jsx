import { useEffect, useState } from "react";
import { AuthContext } from "./authContext";
import {jwtDecode} from "jwt-decode";


export const AuthProvider = ({ children }) => {
  const [userId, setUserId] = useState(null);
  const [token, setToken] = useState(null);
  const [userEmail, setUserEmail] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedToken = localStorage.getItem("authToken");
    if (savedToken) {
      try {
        const decoded = jwtDecode(savedToken);

        // The backend requires exp; discard legacy non-expiring sessions.
        const currentTime = Date.now() / 1000;
        if (!decoded.exp || decoded.exp < currentTime) {
          console.warn("Token expired, removing it");
          localStorage.removeItem("authToken");
          setToken(null);
          setUserId(null);
        } else {
          setUserId(decoded.user_id);
          setUserEmail(decoded.user_email);
          setToken(savedToken);
        }
      } catch (err) {
        console.error("Invalid token:", err.message);
        localStorage.removeItem("authToken");
      }
    }
    setLoading(false);
  }, []);

  return (
    <AuthContext.Provider value={{ userId, userEmail, token, loading }}>
      {children}
    </AuthContext.Provider>
  );
};
