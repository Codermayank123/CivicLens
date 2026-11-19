import React from 'react';
import { Link } from 'react-router-dom';
import { MapPin, Calendar, Sparkles } from 'lucide-react';
import { Complaint } from '../../types';
import { StatusBadge, PriorityBadge } from '../ui/Badge';
import { Card } from '../ui/Card';

interface ComplaintCardProps {
  complaint: Complaint;
}

export const ComplaintCard: React.FC<ComplaintCardProps> = ({ complaint }) => {
  const formattedDate = new Date(complaint.created_at).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  return (
    <Card hoverable className="p-5 flex flex-col justify-between group">
      <div>
        {/* Header badges */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-semibold text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
              #{complaint.public_id}
            </span>
            <StatusBadge status={complaint.status} />
          </div>
          <PriorityBadge priority={complaint.priority} />
        </div>

        {/* Title */}
        <Link to={`/complaints/${complaint.id}`}>
          <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors line-clamp-1 mb-1.5">
            {complaint.title}
          </h3>
        </Link>

        {/* Description snippet */}
        <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2 leading-relaxed mb-4">
          {complaint.description}
        </p>

        {/* AI Tag pill if present */}
        {complaint.ai_category && (
          <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 text-[11px] font-medium mb-3 border border-purple-200 dark:border-purple-800">
            <Sparkles className="w-3 h-3 text-purple-500" />
            <span>AI Tag: {complaint.ai_category.replace(/_/g, ' ')}</span>
            {complaint.ai_confidence && (
              <span className="opacity-75">({Math.round(complaint.ai_confidence * 100)}%)</span>
            )}
          </div>
        )}
      </div>

      {/* Footer metadata */}
      <div className="pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        <div className="flex items-center gap-3">
          {complaint.address && (
            <span className="flex items-center gap-1 line-clamp-1 max-w-[140px]" title={complaint.address}>
              <MapPin className="w-3.5 h-3.5 flex-shrink-0 text-slate-400" />
              <span className="truncate">{complaint.address}</span>
            </span>
          )}
          <span className="flex items-center gap-1">
            <Calendar className="w-3.5 h-3.5" />
            <span>{formattedDate}</span>
          </span>
        </div>

        <Link
          to={`/complaints/${complaint.id}`}
          className="font-medium text-indigo-600 dark:text-indigo-400 hover:underline"
        >
          View →
        </Link>
      </div>
    </Card>
  );
};
