import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  PlusCircle,
  FileText,
  MapPin,
  BarChart3,
  CheckCircle2,
  UploadCloud,
  Settings,
  Flame,
  Award,
  ShieldAlert,
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { useI18n } from '../../i18n';

export const Sidebar: React.FC = () => {
  const { user } = useAuthStore();
  const role = user?.roles?.[0] || 'citizen';
  const { t } = useI18n();

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors ${
      isActive
        ? 'bg-[#4b205b] text-white shadow-sm shadow-[#4b205b]/20'
        : 'text-[var(--color-text-muted)] hover:bg-[var(--color-surface)] hover:text-[var(--color-text)]'
    }`;

  return (
    <aside className="w-64 flex-shrink-0 hidden md:block border-r border-[var(--color-border)] bg-[var(--color-surface)] min-h-[calc(100vh-4rem)] p-4 space-y-6">
      {/* Role specific links */}
      <div>
        <div className="px-3 mb-2 text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
          {role.replace('_', ' ')} Portal
        </div>
        <nav className="space-y-1">
          {/* Common citizen views */}
          <NavLink to="/dashboard" className={linkClass}>
            <LayoutDashboard className="w-4 h-4" />
            <span>{t('home')}</span>
          </NavLink>

          <NavLink to="/report" className={linkClass}>
            <PlusCircle className="w-4 h-4 text-emerald-500" />
            <span>{t('report')}</span>
          </NavLink>

          <NavLink to="/my-complaints" className={linkClass}>
            <FileText className="w-4 h-4" />
            <span>{t('issues')}</span>
          </NavLink>

          <NavLink to="/sync-queue" className={linkClass}>
            <UploadCloud className="w-4 h-4 text-amber-500" />
            <span>{t('sync')}</span>
          </NavLink>

          <NavLink to="/impact" className={linkClass}>
            <BarChart3 className="w-4 h-4 text-[#e87924]" />
            <span>{t('impact')}</span>
          </NavLink>

          <NavLink to="/rewards" className={linkClass}>
            <Award className="w-4 h-4 text-[#d9a84e]" />
            <span>{t('civicHeroRewards')}</span>
          </NavLink>

          {/* Officer & Admin views */}
          {(role === 'officer' || role === 'admin') && (
            <>
              <div className="pt-4 px-3 mb-2 text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
                {t('management')}
              </div>
              <NavLink to="/officer/triage" className={linkClass}>
                <CheckCircle2 className="w-4 h-4 text-purple-500" />
                <span>{t('departmentTriage')}</span>
              </NavLink>
              <NavLink to="/analytics" className={linkClass}>
                <BarChart3 className="w-4 h-4 text-cyan-500" />
                <span>{t('resolutionAnalytics')}</span>
              </NavLink>
              <NavLink to="/admin/ai-review" className={linkClass}>
                <ShieldAlert className="w-4 h-4 text-rose-500" />
                <span>{t('aiReview')}</span>
              </NavLink>
            </>
          )}

          {/* Field staff view */}
          {(role === 'field_staff' || role === 'admin') && (
            <>
              <div className="pt-4 px-3 mb-2 text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
                {t('fieldOperations')}
              </div>
              <NavLink to="/field/tasks" className={linkClass}>
                <MapPin className="w-4 h-4 text-rose-500" />
                <span>{t('fieldTasks')}</span>
              </NavLink>
            </>
          )}

          {/* Admin exclusive view */}
          {role === 'admin' && (
            <>
              <div className="pt-4 px-3 mb-2 text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
                {t('administration')}
              </div>
              <NavLink to="/admin" className={linkClass}>
                <Settings className="w-4 h-4" />
                <span>{t('adminConsole')}</span>
              </NavLink>
            </>
          )}
        </nav>
      </div>

      {/* Quick Tips Box */}
      <div className="p-3.5 rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-xs text-[var(--color-text-muted)]">
        <p className="font-semibold text-[var(--color-text)] mb-1 flex items-center gap-1.5">
          <Flame className="w-3.5 h-3.5 text-[#e87924]" /> {t('offlineCapable')}
        </p>
        <p className="text-[11px] leading-relaxed">
          {t('offlineMessage')}
        </p>
      </div>
    </aside>
  );
};
