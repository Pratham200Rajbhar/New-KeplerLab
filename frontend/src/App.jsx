import { BrowserRouter as Router, Routes, Route, Navigate, useParams } from 'react-router-dom';
import { useEffect } from 'react';
import './index.css';
import { AppProvider, useApp } from './context/AppContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import ErrorBoundary, { PanelErrorBoundary } from './components/ErrorBoundary';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ChatPanel from './components/ChatPanel';
import StudioPanel from './components/StudioPanel';
import AuthPage from './components/AuthPage';
import HomePage from './components/HomePage';
import FileViewerPage from './components/FileViewerPage';
import { getNotebook } from './api/notebooks';

/**
 * ProtectedRoute component to wrap authenticated routes
 */
function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface">
        <div className="flex flex-col items-center gap-4">
          <div className="loading-spinner w-10 h-10" />
          <p className="text-text-secondary">Loading session...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />;
  }

  return children;
}

/**
 * Workspace handles the notebook view logic, loading data from URL params if needed.
 */
function Workspace() {
  const { id } = useParams();
  const { user } = useAuth();
  const {
    currentNotebook,
    setCurrentNotebook,
    setDraftMode,
    setMaterials,
    setMessages,
    setCurrentMaterial,
    deselectAllSources,
  } = useApp();

  useEffect(() => {
    const loadNotebook = async () => {
      // If we are navigating to a specific notebook and it's not the one in state
      if (id && id !== 'draft' && currentNotebook?.id !== id) {
        try {
          const notebook = await getNotebook(id);
          setCurrentNotebook(notebook);
          setDraftMode(false);
        } catch (error) {
          console.error('Failed to load notebook:', error);
          // TODO: Redirect to home or show error
        }
      } else if (id === 'draft' && !currentNotebook?.isDraft && (!currentNotebook?.id || currentNotebook.id === 'draft')) {
        // Only reset to draft when there is no real notebook loaded yet.
        // Guard against the race where setCurrentNotebook(realId) fires before
        // navigate('/notebook/realId') updates the URL: if a real notebook was
        // just assigned, do NOT overwrite it back to the draft placeholder.
        setCurrentNotebook({ id: 'draft', name: 'New Notebook', isDraft: true });
        setDraftMode(true);
      }
    };
    loadNotebook();
  }, [id, currentNotebook?.id]);

  const handleBack = () => {
    setCurrentNotebook(null);
    setDraftMode(false);
    setMaterials([]);
    setMessages([]);
    setCurrentMaterial(null);
    deselectAllSources();
  };

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-surface">
      <Header user={user} onBack={handleBack} />
      <div className="flex-1 flex overflow-hidden">
        <PanelErrorBoundary panelName="Sidebar">
          <Sidebar />
        </PanelErrorBoundary>
        <PanelErrorBoundary panelName="Chat">
          <ChatPanel />
        </PanelErrorBoundary>
        <PanelErrorBoundary panelName="Studio">
          <StudioPanel />
        </PanelErrorBoundary>
      </div>
    </div>
  );
}

function AppContent() {
  return (
    <AppProvider>
      <Routes>
        <Route path="/auth" element={<AuthPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <HomePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/notebook/:id"
          element={
            <ProtectedRoute>
              <Workspace />
            </ProtectedRoute>
          }
        />
        {/* Public file viewer — no auth required */}
        <Route path="/view" element={<FileViewerPage />} />
        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppProvider>
  );
}

function App() {
  return (
    <Router>
      <ThemeProvider>
        <AuthProvider>
          <ErrorBoundary>
            <AppContent />
          </ErrorBoundary>
        </AuthProvider>
      </ThemeProvider>
    </Router>
  );
}

export default App;
