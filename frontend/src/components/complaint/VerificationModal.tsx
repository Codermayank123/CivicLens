import React, { useState } from 'react';
import { Star, CheckCircle, RotateCcw } from 'lucide-react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';

interface VerificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (action: 'approved' | 'rejected', feedback: string, rating: number) => Promise<void>;
  complaintPublicId: string;
}

export const VerificationModal: React.FC<VerificationModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  complaintPublicId,
}) => {
  const [action, setAction] = useState<'approved' | 'rejected'>('approved');
  const [rating, setRating] = useState<number>(5);
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onSubmit(action, feedback, rating);
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Verify Resolution #${complaintPublicId}`}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <p className="text-xs text-slate-600 dark:text-slate-400">
          Please confirm whether the municipality has resolved this problem to your satisfaction.
        </p>

        {/* Choice: Approve or Reject */}
        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => setAction('approved')}
            className={`p-3 rounded-xl border flex flex-col items-center gap-2 text-center transition-all ${
              action === 'approved'
                ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 font-semibold ring-2 ring-emerald-500/30'
                : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50'
            }`}
          >
            <CheckCircle className="w-5 h-5 text-emerald-600" />
            <span className="text-xs">Yes, Issue Fixed!</span>
          </button>

          <button
            type="button"
            onClick={() => setAction('rejected')}
            className={`p-3 rounded-xl border flex flex-col items-center gap-2 text-center transition-all ${
              action === 'rejected'
                ? 'border-rose-500 bg-rose-50 dark:bg-rose-950/40 text-rose-800 dark:text-rose-300 font-semibold ring-2 ring-rose-500/30'
                : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-50'
            }`}
          >
            <RotateCcw className="w-5 h-5 text-rose-600" />
            <span className="text-xs">No, Still Broken</span>
          </button>
        </div>

        {/* Rating Stars */}
        {action === 'approved' && (
          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Rate Municipal Resolution Quality:
            </label>
            <div className="flex gap-1.5">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setRating(star)}
                  className="p-1 hover:scale-110 transition-transform"
                >
                  <Star
                    className={`w-6 h-6 ${
                      star <= rating
                        ? 'fill-amber-400 text-amber-400'
                        : 'text-slate-300 dark:text-slate-600'
                    }`}
                  />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Feedback text */}
        <div>
          <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
            Verification Feedback / Notes:
          </label>
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            rows={3}
            placeholder={
              action === 'approved'
                ? 'e.g., Road repaired smoothly, debris cleared. Thank you!'
                : 'e.g., Water is still leaking from the main joint.'
            }
            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 p-2.5 text-xs focus:ring-2 focus:ring-indigo-500 outline-none"
          />
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant={action === 'approved' ? 'success' : 'danger'}
            size="sm"
            isLoading={isSubmitting}
          >
            {action === 'approved' ? 'Confirm Resolution' : 'Reopen Complaint'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
