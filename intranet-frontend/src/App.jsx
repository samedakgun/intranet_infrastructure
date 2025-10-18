// src/App.jsx
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import Header from "./components/Header";
import ApplicationGrid from "./components/ApplicationGrid";
import LoginPage from "./pages/LoginPage";
import PlatePage from "./pages/PlatePage";
import DocQAPage from "./pages/DocQAPage";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./App.css";

const AppContent = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Routes>
          <Route path="/" element={<ApplicationGrid />} />
          <Route path="/apps/plate" element={<PlatePage />} />
          <Route path="/apps/doc-qa" element={<DocQAPage />} />
        </Routes>
      </main>
      <footer className="bg-white border-t border-gray-200 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center text-sm text-gray-500">
            <p>
              &copy; 2024 Sigorta Tahkim İntranet Sistemi. Tüm hakları saklıdır.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </AuthProvider>
  );
}
