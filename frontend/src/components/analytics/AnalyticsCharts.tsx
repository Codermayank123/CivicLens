import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { Card } from '../ui/Card';

interface AnalyticsChartsProps {
  statusDistribution: Array<{ status: string; count: number }>;
  categoryDistribution: Array<{ category_name: string; count: number }>;
  trends: Array<{ date: string; reported: number; resolved: number }>;
  departmentMetrics: Array<{ department_name: string; total_assigned: number; resolved: number }>;
}

const COLORS = ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'];

export const AnalyticsCharts: React.FC<AnalyticsChartsProps> = ({
  statusDistribution,
  categoryDistribution,
  trends,
  departmentMetrics,
}) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* 30-Day Trend Chart */}
      <Card className="p-5">
        <h4 className="text-sm font-bold text-slate-800 dark:text-slate-100 mb-1">
          Issue Resolution Activity (Reported vs Resolved)
        </h4>
        <p className="text-xs text-slate-500 mb-4">Volume velocity over the last two weeks</p>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={trends}>
              <defs>
                <linearGradient id="colorReported" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorResolved" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Area
                type="monotone"
                dataKey="reported"
                name="Reported"
                stroke="#f59e0b"
                fillOpacity={1}
                fill="url(#colorReported)"
              />
              <Area
                type="monotone"
                dataKey="resolved"
                name="Resolved"
                stroke="#10b981"
                fillOpacity={1}
                fill="url(#colorResolved)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Categories Breakdown */}
      <Card className="p-5">
        <h4 className="text-sm font-bold text-slate-800 dark:text-slate-100 mb-1">
          Complaints by Infrastructure Category
        </h4>
        <p className="text-xs text-slate-500 mb-4">Potholes, water leaks, garbage, etc.</p>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={categoryDistribution} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis type="number" tick={{ fontSize: 10 }} />
              <YAxis dataKey="category_name" type="category" width={110} tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#4f46e5" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Department SLA Comparison */}
      <Card className="p-5">
        <h4 className="text-sm font-bold text-slate-800 dark:text-slate-100 mb-1">
          Department Resolution Efficiency
        </h4>
        <p className="text-xs text-slate-500 mb-4">Total assigned vs. completed resolutions</p>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={departmentMetrics}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="department_name" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="total_assigned" name="Assigned" fill="#94a3b8" radius={[4, 4, 0, 0]} />
              <Bar dataKey="resolved" name="Resolved" fill="#10b981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Status Distribution Pie */}
      <Card className="p-5">
        <h4 className="text-sm font-bold text-slate-800 dark:text-slate-100 mb-1">
          Complaint Lifecycle Distribution
        </h4>
        <p className="text-xs text-slate-500 mb-4">Ratio of submitted, active, and closed tickets</p>
        <div className="h-64 w-full flex items-center justify-center">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={statusDistribution.filter((s) => s.count > 0)}
                dataKey="count"
                nameKey="status"
                cx="50%"
                cy="50%"
                outerRadius={80}
                label={({ status, count }) => `${status}: ${count}`}
              >
                {statusDistribution.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
};
