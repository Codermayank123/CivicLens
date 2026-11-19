import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart3,
  CheckCircle2,
  Clock,
  Bell,
  Award,
  ShieldAlert,
} from 'lucide-react';
import { analyticsService } from '../services/analytics.service';
import { adminMonitoringService } from '../services/admin-monitoring.service';
import { Card } from '../components/ui/Card';
import { AnalyticsCharts } from '../components/analytics/AnalyticsCharts';

export const AdminDashboard: React.FC = () => {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['adminStats'],
    queryFn: () => analyticsService.getOverview(),
  });
  const { data: rewards } = useQuery({
    queryKey: ['admin-rewards-overview'],
    queryFn: adminMonitoringService.getRewards,
  });
  const { data: deliveries } = useQuery({
    queryKey: ['admin-delivery-summary'],
    queryFn: adminMonitoringService.getDeliverySummary,
  });

  if (isLoading || !stats) {
    return (
      <div className="py-20 text-center text-xs text-slate-500">
        Aggregating system telemetry and resolution performance...
      </div>
    );
  }

  return (
    <div className="premium-dashboard heritage-portal space-y-8">
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100">
          Executive Governance & Analytics Console
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          City-wide municipal SLA monitoring, AI categorization accuracy, and citizen satisfaction metrics.
        </p>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-500">Total Volume</span>
            <BarChart3 className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100">
            {stats.total_complaints}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            All recorded complaints
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-500">Citizen Satisfaction</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100">
            {stats.citizen_satisfaction_percentage}%
          </div>
          <div className="text-[11px] text-slate-400 mt-1">From verified citizen ratings</div>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-500">Avg Resolution SLA</span>
            <Clock className="w-4 h-4 text-cyan-500" />
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100">
            {stats.avg_resolution_time_hours}h
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Across resolved complaints</div>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-500">Duplicates Saved</span>
            <ShieldAlert className="w-4 h-4 text-purple-500" />
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100">
            {stats.duplicate_prevented_count}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Prevented redundant work orders</div>
        </Card>
      </div>

      {/* Visual Recharts Section */}
      <AnalyticsCharts
        statusDistribution={stats.status_distribution}
        categoryDistribution={stats.category_distribution}
        trends={stats.trends_last_30_days}
        departmentMetrics={stats.department_metrics}
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <div className="mb-4 flex items-center gap-2">
            <Award className="h-4 w-4 text-amber-500" />
            <h2 className="font-bold text-slate-900 dark:text-slate-100">Civic Hero monitoring</h2>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><span className="text-slate-500">Citizens with points</span><strong className="block text-xl">{rewards?.citizens_with_points ?? '—'}</strong></div>
            <div><span className="text-slate-500">Points awarded</span><strong className="block text-xl">{rewards?.total_points_awarded ?? '—'}</strong></div>
            <div><span className="text-slate-500">Verified contributions</span><strong className="block text-xl">{rewards?.verified_contribution_count ?? '—'}</strong></div>
            <div><span className="text-slate-500">Transactions</span><strong className="block text-xl">{rewards?.transaction_count ?? '—'}</strong></div>
          </div>
        </Card>

        <Card className="p-5">
          <div className="mb-4 flex items-center gap-2">
            <Bell className="h-4 w-4 text-cyan-500" />
            <h2 className="font-bold text-slate-900 dark:text-slate-100">Notification delivery monitoring</h2>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><span className="text-slate-500">Total deliveries</span><strong className="block text-xl">{deliveries?.total ?? '—'}</strong></div>
            <div><span className="text-slate-500">Failed deliveries</span><strong className="block text-xl text-rose-600">{deliveries?.by_status?.failed ?? 0}</strong></div>
            <div><span className="text-slate-500">In-app</span><strong className="block text-xl">{deliveries?.by_channel?.in_app ?? 0}</strong></div>
            <div><span className="text-slate-500">Email / SMS</span><strong className="block text-xl">{(deliveries?.by_channel?.email ?? 0) + (deliveries?.by_channel?.sms ?? 0)}</strong></div>
          </div>
        </Card>
      </div>
    </div>
  );
};
