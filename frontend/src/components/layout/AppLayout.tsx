import React, { useEffect } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { WifiOff, LayoutDashboard, PlusCircle, FileText, UploadCloud, Map, Award } from 'lucide-react';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';
import { Footer } from './Footer';
import { useUIStore } from '../../store/uiStore';
import { syncManager } from '../../services/offline/syncManager';
import { useAuthStore } from '../../store/authStore';
import { RoleNavigation } from './RoleNavigation';
import { API_V1_URL } from '../../config/api';
import { useI18n } from '../../i18n';

export const AppLayout: React.FC = () => {
  const { isOnline, setOnlineStatus } = useUIStore();
  const { isAuthenticated, user } = useAuthStore();
  const queryClient = useQueryClient();
  const role = user?.roles?.[0] || 'citizen';
  const isCitizen = role === 'citizen';
  const { t } = useI18n();

  useEffect(() => {
    const handleOnline = () => setOnlineStatus(true);
    const handleOffline = () => setOnlineStatus(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    syncManager.listenForOnline();

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [setOnlineStatus]);

  useEffect(() => {
    if (!isAuthenticated) return undefined;
    const token = localStorage.getItem('civiclens_access_token');
    if (!token || typeof WebSocket === 'undefined') return undefined;
    const apiUrl = API_V1_URL.startsWith('http')
      ? API_V1_URL.replace(/^http/, 'ws')
      : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}${API_V1_URL}`;
    const socket = new WebSocket(`${apiUrl}/notifications/stream?access_token=${encodeURIComponent(token)}`);
    socket.onmessage = () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    };
    return () => socket.close();
  }, [isAuthenticated, queryClient]);

  return (
    <div className="flex min-h-screen flex-col bg-[var(--color-bg)] text-[var(--color-text)] font-sans transition-colors duration-200">
      {/* Offline Alert Strip */}
      {!isOnline && (
        <div className="bg-[#d9a84e] text-[#29232b] px-4 py-1.5 text-xs font-semibold flex items-center justify-center gap-2 shadow-sm">
          <WifiOff className="w-4 h-4" />
          <span>{t('offlineMessage')}</span>
        </div>
      )}

      <Navbar />

      {isAuthenticated && isCitizen && (
        <nav aria-label="Mobile navigation" className="mobile-app-nav sticky top-16 z-30 flex justify-around gap-1 p-2 md:hidden">
          {[
            { to: '/dashboard', label: t('home'), icon: LayoutDashboard },
            { to: '/report', label: t('report'), icon: PlusCircle },
            { to: '/my-complaints', label: t('issues'), icon: FileText },
            { to: '/sync-queue', label: t('sync'), icon: UploadCloud },
            { to: '/impact', label: t('map'), icon: Map },
            { to: '/rewards', label: t('rewards'), icon: Award },
          ].map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `flex min-h-11 min-w-0 flex-1 flex-col items-center justify-center gap-1 border-2 px-1 py-1 text-[10px] font-bold uppercase ${isActive ? 'border-[#4b205b] bg-[#f4e8d5] text-[#4b205b]' : 'border-transparent text-current'}`}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
      )}

      {isAuthenticated && !isCitizen && <RoleNavigation />}

      <div className="flex-1 max-w-7xl w-full mx-auto flex">
        {isAuthenticated && isCitizen && <Sidebar />}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">
          <Outlet />
        </main>
      </div>

      <Footer />
    </div>
  );
};
