export const STATUS_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; border: string }
> = {
  submitted: {
    label: 'Submitted',
    color: 'text-amber-700 dark:text-amber-300',
    bg: 'bg-amber-50 dark:bg-amber-950/40',
    border: 'border-amber-200 dark:border-amber-800',
  },
  under_review: {
    label: 'Under Review',
    color: 'text-blue-700 dark:text-blue-300',
    bg: 'bg-blue-50 dark:bg-blue-950/40',
    border: 'border-blue-200 dark:border-blue-800',
  },
  verified: {
    label: 'Verified',
    color: 'text-indigo-700 dark:text-indigo-300',
    bg: 'bg-indigo-50 dark:bg-indigo-950/40',
    border: 'border-indigo-200 dark:border-indigo-800',
  },
  assigned: {
    label: 'Assigned',
    color: 'text-purple-700 dark:text-purple-300',
    bg: 'bg-purple-50 dark:bg-purple-950/40',
    border: 'border-purple-200 dark:border-purple-800',
  },
  in_progress: {
    label: 'In Progress',
    color: 'text-cyan-700 dark:text-cyan-300',
    bg: 'bg-cyan-50 dark:bg-cyan-950/40',
    border: 'border-cyan-200 dark:border-cyan-800',
  },
  resolved: {
    label: 'Resolved',
    color: 'text-emerald-700 dark:text-emerald-300',
    bg: 'bg-emerald-50 dark:bg-emerald-950/40',
    border: 'border-emerald-200 dark:border-emerald-800',
  },
  citizen_verification_pending: {
    label: 'Verification Pending',
    color: 'text-orange-700 dark:text-orange-300',
    bg: 'bg-orange-50 dark:bg-orange-950/40',
    border: 'border-orange-200 dark:border-orange-800',
  },
  reopened: {
    label: 'Reopened',
    color: 'text-rose-700 dark:text-rose-300',
    bg: 'bg-rose-50 dark:bg-rose-950/40',
    border: 'border-rose-200 dark:border-rose-800',
  },
  closed: {
    label: 'Closed',
    color: 'text-slate-700 dark:text-slate-300',
    bg: 'bg-slate-100 dark:bg-slate-800/60',
    border: 'border-slate-300 dark:border-slate-700',
  },
  rejected: {
    label: 'Rejected',
    color: 'text-red-700 dark:text-red-300',
    bg: 'bg-red-50 dark:bg-red-950/40',
    border: 'border-red-200 dark:border-red-800',
  },
};

export const PRIORITY_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; dot: string }
> = {
  low: {
    label: 'Low',
    color: 'text-slate-600 dark:text-slate-400',
    bg: 'bg-slate-100 dark:bg-slate-800',
    dot: 'bg-slate-400',
  },
  medium: {
    label: 'Medium',
    color: 'text-blue-700 dark:text-blue-300',
    bg: 'bg-blue-50 dark:bg-blue-900/40',
    dot: 'bg-blue-500',
  },
  high: {
    label: 'High',
    color: 'text-amber-700 dark:text-amber-300',
    bg: 'bg-amber-50 dark:bg-amber-900/40',
    dot: 'bg-amber-500',
  },
  critical: {
    label: 'Critical',
    color: 'text-red-700 dark:text-red-300',
    bg: 'bg-red-50 dark:bg-red-900/40',
    dot: 'bg-red-500 animate-pulse',
  },
};

export const DEMO_USERS = [
  {
    role: 'Citizen',
    email: 'citizen@example.com',
    password: 'Demo@12345',
    description: 'Report issues, track progress, verify fixes with proof',
  },
  {
    role: 'Officer',
    email: 'officer@example.com',
    password: 'Demo@12345',
    description: 'Triage department tickets, assign field staff, track SLAs',
  },
  {
    role: 'Field Staff',
    email: 'fieldstaff@example.com',
    password: 'Demo@12345',
    description: 'View assigned jobs on map, upload fix evidence, complete tasks',
  },
  {
    role: 'Admin',
    email: 'admin@example.com',
    password: 'Demo@12345',
    description: 'Executive analytics, cross-department resolution KPIs, system settings',
  },
];
