import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Activity, CheckCircle2, Clock3, MapPinned, ShieldAlert } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { analyticsService } from '../services/analytics.service';
import { publicService } from '../services/public.service';
import { Card } from '../components/ui/Card';
import { IndiaImpactMap, INDIA_STATES } from '../components/map/IndiaImpactMap';

export const ImpactTrackerPage: React.FC = () => {
  const { user } = useAuthStore();
  const isOfficial = !!user?.roles?.some((role) => ['admin', 'officer', 'department_head'].includes(role));
  const { data: impact, isLoading } = useQuery({ queryKey: ['impact-tracker', isOfficial], queryFn: () => isOfficial ? analyticsService.getImpact() : publicService.getImpact(), staleTime: 30_000 });
  const { data: states = [] } = useQuery({ queryKey: ['india-impact', isOfficial], queryFn: () => isOfficial ? analyticsService.getIndia() : publicService.getIndia(), staleTime: 30_000 });
  const stateMap = new Map(states.map((state) => [state.state.toLowerCase(), state]));
  if (isLoading || !impact) return <div className="py-20 text-center text-sm text-[#66565f]">Loading live Civic Impact Tracker data…</div>;
  return <div className="heritage-portal space-y-6 py-4"><div><p className="heritage-kicker flex items-center gap-2"><Activity className="h-4 w-4" /> Evidence-led public accountability</p><h1 className="heritage-section-title">Civic Impact Tracker</h1><p className="heritage-subtitle">Live complaint outcomes, service deadlines, department performance, and state-wise improvement from CivicLens records.</p></div><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5"><Kpi icon={<Activity />} label="Total complaints" value={impact.total_complaints} /><Kpi icon={<CheckCircle2 />} label="Successfully resolved" value={impact.resolved_complaints} /><Kpi icon={<Clock3 />} label="Avg resolution" value={`${impact.average_resolution_hours}h`} /><Kpi icon={<ShieldAlert />} label="Overdue" value={impact.overdue_complaints} /><Kpi icon={<MapPinned />} label="On-time resolution" value={`${impact.on_time_resolution_percentage}%`} /></div><Card className="p-4 sm:p-5"><div className="mb-4"><h2 className="font-bold text-[#4b205b]">India complaints map</h2><p className="text-xs text-[#66565f]">Click a state marker to inspect live complaint totals and resolution percentage.</p></div><IndiaImpactMap metrics={states} /></Card><Card className="overflow-hidden"><div className="border-b border-[#dcc6a7] px-5 py-4"><h2 className="font-bold text-[#4b205b]">State and Union Territory outcomes</h2><p className="text-xs text-[#66565f]">States with no records remain visible with zero counts; no dummy complaint data is inserted.</p></div><div className="grid gap-2 p-4 sm:grid-cols-2 lg:grid-cols-3">{INDIA_STATES.map((state) => { const metric = stateMap.get(state.toLowerCase()); return <div key={state} className="border border-[#eadcc6] bg-[#fffaf3] p-3"><div className="flex items-center justify-between gap-2"><strong className="text-sm text-[#29232b]">{state}</strong><span className="text-xs font-bold text-[#286b50]">{metric?.resolution_percentage || 0}%</span></div><p className="mt-1 text-xs text-[#66565f]">{metric?.total_complaints || 0} complaints · {metric?.resolved_complaints || 0} resolved · {metric?.overdue_complaints || 0} overdue</p></div>; })}</div></Card></div>;
};

const Kpi: React.FC<{ icon: React.ReactNode; label: string; value: React.ReactNode }> = ({ icon, label, value }) => <Card className="p-4"><div className="flex items-center gap-2 text-[#9a4d12]">{icon}<span className="text-xs font-bold">{label}</span></div><strong className="mt-2 block text-2xl text-[#4b205b]">{value}</strong></Card>;
