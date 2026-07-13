import { Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Home from "./pages/Home";
import Agents from "./pages/Agents";
import AgentDetail from "./pages/AgentDetail";
import RAGs from "./pages/RAGs";
import RAGDetail from "./pages/RAGDetail";
import RAGPage from "./pages/RAGPage";
import Credits from "./pages/Credits";
import Admin from "./pages/Admin";
import SkillsPage from "./pages/Skills";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<Home />} />
                  <Route path="/agents" element={<Agents />} />
                  <Route path="/agents/:id" element={<AgentDetail />} />
                  <Route path="/rags" element={<RAGs />} />
                  <Route path="/rags/new" element={<RAGDetail />} />
                  <Route path="/rags/:ragId" element={<RAGPage />} />
                  <Route path="/skills" element={<SkillsPage />} />
                  <Route path="/credits" element={<Credits />} />
                  <Route
                    path="/admin"
                    element={
                      <ProtectedRoute adminOnly>
                        <Admin />
                      </ProtectedRoute>
                    }
                  />
                </Routes>
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </AuthProvider>
  );
}
