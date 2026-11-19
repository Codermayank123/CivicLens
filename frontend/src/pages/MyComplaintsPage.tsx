import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { PlusCircle, Search } from 'lucide-react';
import { complaintService } from '../services/complaint.service';
import { ComplaintCard } from '../components/complaint/ComplaintCard';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { useI18n } from '../i18n';

export const MyComplaintsPage: React.FC = () => {
  const { t } = useI18n();
  const [filterTab, setFilterTab] = useState<'all' | 'active' | 'resolved'>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['myAllComplaints'],
    queryFn: () => complaintService.getMyComplaints(1, 50),
  });

  const complaints = data?.items || [];

  const filtered = complaints.filter((c) => {
    if (filterTab === 'active') {
      if (c.status === 'resolved' || c.status === 'closed') return false;
    } else if (filterTab === 'resolved') {
      if (c.status !== 'resolved' && c.status !== 'closed') return false;
    }
    if (searchTerm) {
      const s = searchTerm.toLowerCase();
      return (
        c.title.toLowerCase().includes(s) ||
        c.public_id.toLowerCase().includes(s) ||
        (c.address && c.address.toLowerCase().includes(s))
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100">
            {t('mySubmittedComplaints')}
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            {t('trackResolution')}
          </p>
        </div>

        <Link to="/report">
          <Button size="sm" leftIcon={<PlusCircle className="w-4 h-4" />}>
            {t('reportNewProblem')}
          </Button>
        </Link>
      </div>

      {/* Filter Tabs & Search */}
      <Card className="p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex rounded-lg bg-slate-100 dark:bg-slate-800 p-1 w-full sm:w-auto">
          <button
            onClick={() => setFilterTab('all')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
              filterTab === 'all'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-sm'
                : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            {t('allReports')} ({complaints.length})
          </button>
          <button
            onClick={() => setFilterTab('active')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
              filterTab === 'active'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-sm'
                : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            {t('activeInProgress')}
          </button>
          <button
            onClick={() => setFilterTab('resolved')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
              filterTab === 'resolved'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-sm'
                : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            {t('resolvedClosed')}
          </button>
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder={t('searchComplaints')}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </Card>

      {/* Grid */}
      {isLoading ? (
        <div className="py-20 text-center text-xs text-slate-500">{t('loading')}</div>
      ) : filtered.length === 0 ? (
        <Card className="p-12 text-center text-xs text-slate-500">
          {t('noComplaintsFound')}
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((c) => (
            <ComplaintCard key={c.id} complaint={c} />
          ))}
        </div>
      )}
    </div>
  );
};
