import React from 'react';
import { NavLink } from 'react-router-dom';
import { BarChart3, ClipboardCheck, MapPin, Shield, UsersRound, ScanSearch } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';

const roleCopy: Record<string, { label: string; subtitle: string }> = {
  officer: { label: 'Department Control Room', subtitle: 'Triage, assignment, and verification' },
  field_staff: { label: 'Field Operations', subtitle: 'Mobile work orders and site evidence' },
  admin: { label: 'CivicLens Command', subtitle: 'Accountability, security, and city performance' },
};

export const RoleNavigation: React.FC = () => {
  const { user } = useAuthStore();
  const role = user?.roles?.[0] || 'officer';
  const copy = roleCopy[role] || roleCopy.officer;

  const links = role === 'field_staff'
    ? [
      { to: '/field/tasks', label: 'My Work Orders', icon: MapPin },
      { to: '/notifications', label: 'Operations Inbox', icon: ClipboardCheck },
      { to: '/impact', label: 'Impact Tracker', icon: BarChart3 },
    ]
    : role === 'admin'
      ? [
        { to: '/admin', label: 'Command Overview', icon: Shield },
        { to: '/analytics', label: 'Accountability', icon: BarChart3 },
        { to: '/impact', label: 'Civic Impact Tracker', icon: BarChart3 },
        { to: '/admin/ai-review', label: 'AI Verification', icon: ScanSearch },
        { to: '/notifications', label: 'System Inbox', icon: ClipboardCheck },
      ]
      : [
        { to: '/officer/triage', label: 'Department Queue', icon: ClipboardCheck },
        { to: '/accountability', label: 'Performance', icon: BarChart3 },
        { to: '/impact', label: 'Department Impact', icon: BarChart3 },
        { to: '/admin/ai-review', label: 'AI Review Queue', icon: ScanSearch },
        { to: '/notifications', label: 'Department Inbox', icon: UsersRound },
      ];

  return (
    <div className="border-b border-[#dcc6a7] bg-[#fffaf3]">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 sm:px-6 lg:px-8 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.22em] text-[#9a4d12]">{copy.label}</p>
          <p className="text-xs text-[#66565f]">{copy.subtitle}{user?.department?.name ? ` · ${user.department.name}` : ''}</p>
        </div>
        <nav aria-label={`${copy.label} navigation`} className="flex gap-2 overflow-x-auto pb-1">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `flex min-h-10 shrink-0 items-center gap-2 border px-3 py-2 text-xs font-bold transition-colors ${isActive ? 'border-[#4b205b] bg-[#4b205b] text-white' : 'border-[#dcc6a7] text-[#4b205b] hover:bg-[#f4e8d5]'}`}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  );
};
