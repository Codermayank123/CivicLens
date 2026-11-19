import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Bell,
  Sun,
  Moon,
  Wifi,
  WifiOff,
  LogOut,
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { useUIStore } from '../../store/uiStore';
import { Button } from '../ui/Button';
import { CivicLensMark } from '../brand/CivicLensMark';
import { useQuery } from '@tanstack/react-query';
import { notificationService } from '../../services/notification.service';
import { LANGUAGES, useI18n } from '../../i18n';

export const Navbar: React.FC = () => {
  const { user, isAuthenticated, logout } = useAuthStore();
  const { darkMode, toggleDarkMode, isOnline } = useUIStore();
  const navigate = useNavigate();
  const { language, setLanguage, t } = useI18n();
  const { data: notificationData } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationService.getNotifications(1),
    enabled: isAuthenticated,
    refetchInterval: 15_000,
  });

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-[#dcc6a7] bg-[#fbf7f0]/95 backdrop-blur supports-[backdrop-filter]:bg-[#fbf7f0]/70 dark:border-[#3d3344] dark:bg-[#1a1520]/95 dark:supports-[backdrop-filter]:bg-[#1a1520]/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <Link to="/" className="flex items-center gap-2.5 group">
            <CivicLensMark />
          </Link>

          {/* Offline / Online Status Indicator */}
          <div
            className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
              isOnline
                ? 'bg-[#e4f0e9] text-[#286b50] border-[#98c5ae] dark:bg-[#1f3a2e] dark:text-[#8fd0ad] dark:border-[#2f5a44]'
                : 'bg-[#fff0d9] text-[#9a4d12] border-[#e9b472] animate-pulse dark:bg-[#3a2a18] dark:text-[#f0b56a] dark:border-[#6b4a22]'
            }`}
          >
            {isOnline ? (
              <>
                <Wifi className="w-3.5 h-3.5" />
                <span>{t('online')}</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3.5 h-3.5" />
                <span>{t('offline')}</span>
              </>
            )}
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <label className="sr-only" htmlFor="language-selector">{t('language')}</label>
          <select id="language-selector" value={language} onChange={(event) => setLanguage(event.target.value as typeof language)} className="max-w-[7rem] rounded-lg border border-[#dcc6a7] bg-[#fffaf3] px-2 py-1.5 text-xs text-[#4b205b] dark:border-[#4a3d55] dark:bg-[#241c2c] dark:text-[#f4e8d5]" aria-label={t('language')}>
            {LANGUAGES.map(([code, label]) => <option key={code} value={code}>{label}</option>)}
          </select>
          {/* Theme Toggle */}
          <button
            onClick={toggleDarkMode}
            className="p-2 rounded-lg text-[#4b205b] hover:bg-[#f4e8d5] transition-colors dark:text-[#f4e8d5] dark:hover:bg-[#2f2638]"
            aria-label={t('toggleTheme')}
          >
            {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4" />}
          </button>

          {isAuthenticated && user ? (
            <div className="flex items-center gap-3 pl-2 border-l border-[#dcc6a7] dark:border-[#3d3344]">
              {/* Notification icon */}
              <Link
                to="/notifications"
                className="p-2 rounded-lg text-[#4b205b] hover:bg-[#f4e8d5] relative transition-colors dark:text-[#f4e8d5] dark:hover:bg-[#2f2638]"
              >
                <Bell className="w-4 h-4" />
                {!!notificationData?.unread_count && <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-[#e87924] px-1 text-[9px] font-black text-white">{notificationData.unread_count > 9 ? '9+' : notificationData.unread_count}</span>}
              </Link>

              {/* User profile capsule */}
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-[#f4e8d5] flex items-center justify-center font-bold text-xs text-[#4b205b] dark:bg-[#3a2f48] dark:text-[#f4e8d5]">
                  {user.full_name.charAt(0).toUpperCase()}
                </div>
                <div className="hidden lg:block text-left">
                  <div className="text-xs font-semibold text-[#29232b] leading-tight dark:text-[#f4e8d5]">
                    {user.full_name}
                  </div>
                  <div className="text-[10px] text-[#746565] capitalize dark:text-slate-400">
                    {user.roles?.[0] || 'Citizen'}
                  </div>
                </div>
              </div>

              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                title={t('logout')}
                className="text-slate-500 hover:text-rose-600"
              >
                <LogOut className="w-4 h-4" />
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link to="/login">
                <Button variant="ghost" size="sm">
                  {t('signIn')}
                </Button>
              </Link>
              <Link to="/register">
                <Button variant="primary" size="sm">
                  {t('register')}
                </Button>
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
