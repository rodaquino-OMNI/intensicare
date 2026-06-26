import { useState } from 'react';
import { AuthProvider, useAuth } from './hooks/useAuth';
import LoginForm from './components/LoginForm';
import BedGrid from './components/BedGrid';
import PatientDetail from './components/PatientDetail';

function AppContent() {
  const { isAuthenticated, username, logout } = useAuth();
  const [selectedPatient, setSelectedPatient] = useState<string | null>(null);

  if (!isAuthenticated) {
    return <LoginForm />;
  }

  if (selectedPatient) {
    return (
      <PatientDetail
        mpiId={selectedPatient}
        onBack={() => setSelectedPatient(null)}
      />
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top bar */}
      <header className="bg-slate-800 text-white px-6 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold tracking-tight">Intensicare</h1>
          <p className="text-xs text-slate-400">Clinical Monitoring Platform</p>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-slate-300">{username}</span>
          <button
            onClick={logout}
            className="text-sm text-slate-400 hover:text-white transition-colors"
          >
            Sign Out
          </button>
        </div>
      </header>

      <BedGrid onSelectPatient={(mpiId) => setSelectedPatient(mpiId)} />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
