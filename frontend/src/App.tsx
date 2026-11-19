import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { useAuthStore } from './store/authStore';
import { useUIStore } from './store/uiStore';

import { AppLayout } from './components/layout/AppLayout';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { CitizenDashboard } from './pages/CitizenDashboard';
import { CreateComplaint } from './pages/CreateComplaint';
import { MyComplaintsPage } from './pages/MyComplaintsPage';
import { ComplaintDetails } from './pages/ComplaintDetails';
import { OfficerDashboard } from './pages/OfficerDashboard';
import { FieldStaffDashboard } from './pages/FieldStaffDashboard';
import { AdminDashboard } from './pages/AdminDashboard';
import { SyncQueuePage } from './pages/SyncQueuePage';
import { IdentityVerificationPage } from './pages/IdentityVerificationPage';
import { VerifyEmailPage } from './pages/VerifyEmailPage';
import { NotificationsPage } from './pages/NotificationsPage';
import { RewardsPage } from './pages/RewardsPage';
import { AccountabilityPage } from './pages/AccountabilityPage';
import { AIReviewPage } from './pages/AIReviewPage';
import { ImpactTrackerPage } from './pages/ImpactTrackerPage';

// Protected Route Guard
export const ProtectedRoute: React.FC<{
  children: React.ReactNode;
  roles?: string[];
}> = ({ children, roles }) => {
  const { isAuthenticated, isLoading, user } = useAuthStore();

  if (isLoading) {
    return <div role="status">Checking your session...</div>;
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  if (
    roles &&
    !user.roles.some((role) => role === 'admin' || roles.includes(role))
  ) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  const { initAuth } = useAuthStore();
  const { darkMode } = useUIStore();

  useEffect(() => {
    initAuth();
    document.documentElement.classList.toggle('dark', darkMode);
  }, [initAuth, darkMode]);

  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          className: 'text-xs font-medium dark:bg-slate-900 dark:text-slate-100 dark:border-slate-800',
          duration: 4000,
        }}
      />
      <Routes>
        {/* Public Landing & Auth */}
        <Route path="/" element={<AppLayout />}>
          <Route index element={<LandingPage />} />
          <Route path="login" element={<LoginPage />} />
          <Route path="register" element={<RegisterPage />} />
          <Route path="verify-email" element={<VerifyEmailPage />} />

          {/* Authenticated Application Routes */}
          <Route
            path="dashboard"
            element={
              <ProtectedRoute roles={['citizen']}>
                <CitizenDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="report"
            element={
              <ProtectedRoute roles={['citizen']}>
                <CreateComplaint />
              </ProtectedRoute>
            }
          />
          <Route
            path="my-complaints"
            element={
              <ProtectedRoute roles={['citizen']}>
                <MyComplaintsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="complaints/:id"
            element={
              <ProtectedRoute>
                <ComplaintDetails />
              </ProtectedRoute>
            }
          />
          <Route
            path="sync-queue"
            element={
              <ProtectedRoute roles={['citizen']}>
                <SyncQueuePage />
              </ProtectedRoute>
            }
          />
          <Route path="notifications" element={<ProtectedRoute><NotificationsPage /></ProtectedRoute>} />
          <Route path="heatmap" element={<Navigate to="/impact" replace />} />
          <Route path="impact" element={<ImpactTrackerPage />} />
          <Route path="accountability" element={<ProtectedRoute roles={['officer', 'admin']}><AccountabilityPage /></ProtectedRoute>} />
          <Route path="rewards" element={<ProtectedRoute roles={['citizen']}><RewardsPage /></ProtectedRoute>} />
          <Route
            path="verify-identity"
            element={
              <ProtectedRoute roles={['citizen']}>
                <IdentityVerificationPage />
              </ProtectedRoute>
            }
          />

          {/* Role views */}
          <Route
            path="officer/triage"
            element={
              <ProtectedRoute roles={['officer']}>
                <OfficerDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="field/tasks"
            element={
              <ProtectedRoute roles={['field_staff']}>
                <FieldStaffDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="analytics"
            element={
              <ProtectedRoute roles={['admin']}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="admin"
            element={
              <ProtectedRoute roles={['admin']}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          <Route path="admin/ai-review" element={<ProtectedRoute roles={['admin', 'officer', 'department_head']}><AIReviewPage /></ProtectedRoute>} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </>
  );
};

export default App;
