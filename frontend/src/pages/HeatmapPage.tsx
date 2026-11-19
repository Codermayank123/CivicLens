import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Map, ShieldCheck } from 'lucide-react';
import { publicService } from '../services/public.service';
import { CivicHeatmap } from '../components/map/Heatmap';
import { Card } from '../components/ui/Card';

export const HeatmapPage: React.FC = () => {
  const { data: points = [], isLoading: loadingMap } = useQuery({ queryKey: ['public-heatmap'], queryFn: publicService.getHeatmap, staleTime: 30_000 });
  const { data: accountability = [], isLoading: loadingAccountability } = useQuery({ queryKey: ['public-accountability'], queryFn: publicService.getAccountability, staleTime: 30_000 });
  return (
    <div className="heritage-portal space-y-6 py-4">
      <div>
        <p className="heritage-kicker flex items-center gap-2"><Map className="h-4 w-4" /> Open civic intelligence</p>
        <h1 className="heritage-section-title">Civic Heatmap & Public Accountability</h1>
        <p className="heritage-subtitle">Hotspots are clustered and privacy-safe. Use an existing report to support a neighbourhood issue instead of creating a duplicate.</p>
      </div>
      <Card className="p-3 sm:p-5">
        {loadingMap ? <div className="py-24 text-center text-sm text-[#66565f]">Loading live complaint hotspots…</div> : <CivicHeatmap points={points} />}
      </Card>
      <Card className="overflow-hidden">
        <div className="flex items-center gap-2 border-b border-[#dcc6a7] px-5 py-4"><ShieldCheck className="h-5 w-5 text-[#286b50]" /><div><h2 className="font-bold text-[#4b205b]">Department-wise resolution performance</h2><p className="text-xs text-[#66565f]">Derived from live complaint status history.</p></div></div>
        <div className="overflow-x-auto"><table className="w-full min-w-[620px] text-left text-sm"><thead className="bg-[#f4e8d5] text-xs uppercase tracking-wide text-[#66565f]"><tr><th className="px-5 py-3">Department</th><th className="px-5 py-3">Total</th><th className="px-5 py-3">Pending</th><th className="px-5 py-3">Resolved</th><th className="px-5 py-3">Resolution rate</th></tr></thead><tbody className="divide-y divide-[#eadcc6]">{loadingAccountability ? <tr><td colSpan={5} className="px-5 py-8 text-center text-[#66565f]">Loading accountability data…</td></tr> : accountability.map((item) => <tr key={item.department_id}><td className="px-5 py-3 font-semibold text-[#29232b]">{item.department_name} <span className="ml-1 text-xs text-[#9a4d12]">{item.code}</span></td><td className="px-5 py-3">{item.total_complaints}</td><td className="px-5 py-3">{item.pending_complaints}</td><td className="px-5 py-3">{item.resolved_complaints}</td><td className="px-5 py-3 font-bold text-[#286b50]">{item.resolution_rate}%</td></tr>)}</tbody></table></div>
      </Card>
    </div>
  );
};
