import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { PlusCircle, CheckCircle, Clock, AlertTriangle, ArrowRight } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { complaintService } from '../services/complaint.service';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ComplaintCard } from '../components/complaint/ComplaintCard';
import { ComplaintMap } from '../components/map/ComplaintMap';
import { useI18n } from '../i18n';

export const CitizenDashboard: React.FC = () => {
  const { user } = useAuthStore();
  const { t } = useI18n();

  const { data: myData, isLoading } = useQuery({
    queryKey: ['myComplaints'],
    queryFn: () => complaintService.getMyComplaints(1, 10),
  });

  const { data: allData } = useQuery({
    queryKey: ['nearbyComplaints'],
    queryFn: () => complaintService.getComplaints({ per_page: 20 }),
  });

  const complaints = myData?.items || [];
  const allComplaints = allData?.items || [];

  const totalReports = complaints.length;
  const resolvedCount = complaints.filter(
    (c) => c.status === 'resolved' || c.status === 'closed'
  ).length;
  const pendingCount = complaints.filter(
    (c) => c.status === 'submitted' || c.status === 'under_review' || c.status === 'assigned' || c.status === 'in_progress'
  ).length;

  return (
    <div className="premium-dashboard space-y-8">
      {/* Welcome & Quick Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-gradient-to-r from-[#4b205b] to-[#6d3b78] text-white rounded-2xl p-6 sm:p-8 shadow-lg">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            {t('welcomeBack')}, {user?.full_name || t('home')}!
          </h1>
          <p className="text-[#f4e8d5] text-xs sm:text-sm mt-1 max-w-xl">
            {t('activeCommunityIssues')}
          </p>
          {!user?.identity_verified && (
            <Link to="/verify-identity" className="inline-block mt-3 text-xs underline text-amber-200">
              {t('identityVerification')}
            </Link>
          )}
        </div>
        <Link to="/report">
          <Button
            size="lg"
            className="bg-[#f4e8d5] text-[#4b205b] hover:bg-[#fffaf3] font-bold shadow-md shadow-black/10"
            leftIcon={<PlusCircle className="w-5 h-5 text-[#e87924]" />}
          >
            {t('reportNewProblem')}
          </Button>
        </Link>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="p-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-[#f4e8d5] text-[#4b205b] flex items-center justify-center">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">{totalReports}</div>
            <div className="text-xs text-slate-500">{t('myTotalReports')}</div>
          </div>
        </Card>

        <Card className="p-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-[#fff0d9] text-[#e87924] flex items-center justify-center">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">{pendingCount}</div>
            <div className="text-xs text-slate-500">{t('inProgressPending')}</div>
          </div>
        </Card>

        <Card className="p-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-[#e4f0e9] text-[#286b50] flex items-center justify-center">
            <CheckCircle className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">{resolvedCount}</div>
            <div className="text-xs text-slate-500">{t('resolvedFixedIssues')}</div>
          </div>
        </Card>
      </div>

      {/* Community Map View */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
              {t('liveInfrastructureMap')}
            </h2>
            <p className="text-xs text-slate-500">{t('activeCommunityIssues')}</p>
          </div>
        </div>
        <ComplaintMap complaints={allComplaints} height="360px" />
      </div>

      {/* My Recent Reports */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
            {t('mySubmittedComplaints')}
          </h2>
          <Link
            to="/my-complaints"
            className="text-xs font-semibold text-[#4b205b] hover:underline flex items-center gap-1"
          >
            {t('viewAllReports')} <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {isLoading ? (
          <div className="py-12 text-center text-xs text-slate-500">{t('loading')}</div>
        ) : complaints.length === 0 ? (
          <Card className="p-8 text-center space-y-3">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              {t('noReportsYet')}
            </p>
            <Link to="/report">
              <Button size="sm">{t('reportFirstIssue')}</Button>
            </Link>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {complaints.slice(0, 6).map((c) => (
              <ComplaintCard key={c.id} complaint={c} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
