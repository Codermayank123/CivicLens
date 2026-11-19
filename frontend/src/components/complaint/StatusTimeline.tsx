import React from 'react';
import { ComplaintStatusHistory } from '../../types';
import { STATUS_CONFIG } from '../../config/constants';

interface StatusTimelineProps {
  history: ComplaintStatusHistory[];
}

export const StatusTimeline: React.FC<StatusTimelineProps> = ({ history }) => {
  if (!history || history.length === 0) {
    return <p className="text-xs text-slate-500">No status events recorded yet.</p>;
  }

  return (
    <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200 dark:before:bg-slate-800">
      {history.map((event, idx) => {
        const config = STATUS_CONFIG[event.new_status] || {
          label: event.new_status.replace(/_/g, ' '),
        };
        const dateStr = new Date(event.created_at).toLocaleString('en-US', {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        });

        return (
          <div key={event.id || idx} className="relative group">
            {/* Timeline icon dot */}
            <div className="absolute -left-6 top-0.5 w-5 h-5 rounded-full bg-white dark:bg-slate-900 border-2 border-indigo-600 flex items-center justify-center">
              <div className="w-1.5 h-1.5 rounded-full bg-indigo-600" />
            </div>

            <div className="bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 p-3.5 rounded-xl">
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="font-semibold text-xs text-slate-900 dark:text-slate-100 uppercase tracking-wide">
                  {config.label}
                </span>
                <span className="text-[11px] text-slate-400 font-mono">{dateStr}</span>
              </div>
              {event.notes && (
                <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                  {event.notes}
                </p>
              )}
              {event.changed_by_name && (
                <div className="mt-2 text-[10px] text-slate-500 dark:text-slate-400">
                  Updated by: <span className="font-medium text-slate-700 dark:text-slate-300">{event.changed_by_name}</span>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
