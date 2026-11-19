import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  MapPin,
  Calendar,
  Building,
  User,
  Sparkles,
  MessageSquare,
  ShieldCheck,
  ShieldAlert,
  Send,
} from 'lucide-react';
import toast from 'react-hot-toast';

import { complaintService } from '../services/complaint.service';
import { useAuthStore } from '../store/authStore';
import { StatusBadge, PriorityBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { StatusTimeline } from '../components/complaint/StatusTimeline';
import { VerificationModal } from '../components/complaint/VerificationModal';

export const ComplaintDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  const [commentText, setCommentText] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);
  const [moderationAction, setModerationAction] = useState<'confirmed_spam' | 'not_spam' | 'escalated'>('not_spam');
  const [moderationReason, setModerationReason] = useState('');

  const { data: complaint, isLoading, error } = useQuery({
    queryKey: ['complaint', id],
    queryFn: () => complaintService.getById(id!),
    enabled: !!id,
  });

  const commentMutation = useMutation({
    mutationFn: (text: string) => complaintService.addComment(id!, text),
    onSuccess: () => {
      setCommentText('');
      toast.success('Comment posted.');
      queryClient.invalidateQueries({ queryKey: ['complaint', id] });
    },
  });

  const moderationMutation = useMutation({
    mutationFn: () => complaintService.reviewAIModeration(id!, moderationAction, moderationReason.trim()),
    onSuccess: () => {
      setModerationReason('');
      toast.success('AI moderation review recorded.');
      queryClient.invalidateQueries({ queryKey: ['complaint', id] });
    },
    onError: (err: any) => toast.error(err.response?.data?.error?.message || 'Moderation review failed.'),
  });

  const handleVerifySubmit = async (
    action: 'approved' | 'rejected',
    feedback: string,
    rating: number
  ) => {
    try {
      await complaintService.verifyResolution(id!, action, feedback, rating);
      toast.success(
        action === 'approved'
          ? 'Thank you! Resolution approved and case closed.'
          : 'Complaint reopened with your feedback.'
      );
      queryClient.invalidateQueries({ queryKey: ['complaint', id] });
    } catch (err: any) {
      toast.error(err.response?.data?.error?.message || 'Verification failed.');
    }
  };

  if (isLoading) {
    return <div className="py-20 text-center text-xs text-slate-500">Loading complaint details...</div>;
  }

  if (error || !complaint) {
    return (
      <div className="py-20 text-center space-y-3">
        <p className="text-sm text-slate-600 dark:text-slate-400">Complaint not found or has been removed.</p>
        <Link to="/dashboard">
          <Button size="sm">Back to Dashboard</Button>
        </Link>
      </div>
    );
  }

  const isCreator = user?.id === complaint.created_by;
  const canVerify =
    isCreator &&
    (complaint.status === 'resolved' || complaint.status === 'citizen_verification_pending');
  const canReviewAI = !!user?.roles?.some((role) => ['admin', 'officer'].includes(role));
  const spamCheck = complaint.ai_verification?.spam_check;
  const spamScore = spamCheck?.spam_score ?? 0;
  const spamLabel = spamCheck?.check_unavailable
    ? 'Assessment unavailable'
    : spamScore >= 0.7
      ? 'High risk'
      : spamScore >= 0.3
        ? 'Medium risk'
        : 'Low risk';

  return (
    <div className="max-w-5xl mx-auto py-4 space-y-6">
      {/* Header bar */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5 mb-2">
            <span className="font-mono text-xs font-bold text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-2.5 py-1 rounded">
              #{complaint.public_id}
            </span>
            <StatusBadge status={complaint.status} />
            <PriorityBadge priority={complaint.priority} />
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-slate-100 leading-tight">
            {complaint.title}
          </h1>
        </div>

        {canVerify && (
          <Button
            variant="success"
            size="md"
            onClick={() => setIsVerifying(true)}
            leftIcon={<ShieldCheck className="w-5 h-5" />}
          >
            Verify Municipal Fix
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Details & Media & Discussion */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          <Card className="p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">Description</h3>
            <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">
              {complaint.description}
            </p>
            {complaint.resolution_notes && (
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950">
                <h4 className="font-bold">Resolution remarks</h4>
                <p className="mt-1 whitespace-pre-wrap">{complaint.resolution_notes}</p>
              </div>
            )}

            {/* AI Predictions badge */}
            {complaint.ai_category && (
              <div className="p-3 rounded-xl bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-800 flex items-center justify-between text-xs text-purple-900 dark:text-purple-200">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-purple-600" />
                  <span>
                    AI Classification: <strong>{complaint.ai_category}</strong>
                  </span>
                </div>
                {complaint.ai_confidence && (
                  <span className="font-mono text-[11px] opacity-80">
                    Confidence: {Math.round(complaint.ai_confidence * 100)}%
                  </span>
                )}
              </div>
            )}
            {canReviewAI && complaint.ai_verification && (
              <div className="border border-[#dcc6a7] bg-[#fffaf3] p-4 text-xs text-[#29232b]">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <strong className="text-[#4b205b]">AI verification (advisory)</strong>
                  <span className={complaint.requires_human_review ? 'font-bold text-[#9a4d12]' : 'font-bold text-[#286b50]'}>{complaint.requires_human_review ? 'Human review required' : 'No review flag'}</span>
                </div>
                <div className="mt-3 grid gap-2 sm:grid-cols-3">
                  <span>Category match: <b>{complaint.ai_verification.category_match ? 'Yes' : 'Uncertain'}</b></span>
                  <span>Severity: <b>{complaint.ai_verification.severity || 'Unknown'}</b></span>
                  <span>Duplicate risk: <b>{complaint.ai_verification.duplicate_risk ? `${Math.round(complaint.ai_verification.duplicate_risk * 100)}%` : 'Low / not detected'}</b></span>
                </div>
                {complaint.ai_verification.suspicious_reasons?.length ? <p className="mt-3 text-[#9a4d12]">Indicators: {complaint.ai_verification.suspicious_reasons.join(', ')}</p> : null}
                {complaint.ai_verification.evidence?.length ? <div className="mt-3 space-y-1"><p className="font-semibold text-[#4b205b]">Evidence checks</p>{complaint.ai_verification.evidence.map((item, index) => <p key={`${item.media_type}-${index}`} className="text-[11px] text-[#66565f]">{item.media_type || 'media'}: {item.is_relevant ? 'relevant signal' : 'uncertain / unrelated'}{item.requires_human_review ? ' · human review' : ''}{item.message ? ` · ${item.message}` : ''}</p>)}</div> : null}
                <p className="mt-3 text-[11px] text-[#66565f]">{complaint.ai_is_mock ? 'Development/mock analysis: evidence pixels were not evaluated.' : 'AI can identify relevance signals, but cannot conclusively prove authenticity or manipulation.'}</p>
                {spamCheck && (
                  <div className="mt-4 border-t border-[#eadcc8] pt-4">
                    <div className="flex items-center gap-2 font-semibold text-[#4b205b]"><ShieldAlert className="w-4 h-4" /> AI Spam Assessment</div>
                    <div className="mt-2 grid gap-2 sm:grid-cols-3">
                      <span>Status: <b>{spamCheck.is_spam ? 'Potential spam' : spamLabel}</b></span>
                      <span>Score: <b>{spamCheck.check_unavailable ? 'Unavailable' : `${spamScore.toFixed(2)} / 1.00`}</b></span>
                      <span>Human review: <b>{complaint.requires_human_review ? 'Required' : 'Not specifically required'}</b></span>
                    </div>
                    {spamCheck.reasons?.length ? <p className="mt-2 text-[#66565f]">Reasons: {spamCheck.reasons.join('; ')}</p> : null}
                    {spamCheck.is_mock ? <p className="mt-1 text-[11px] text-[#9a4d12]">This assessment came from mock mode.</p> : null}
                    {complaint.ai_verification.moderation?.status === 'reviewed' ? (
                      <p className="mt-2 text-emerald-700">Reviewed: {complaint.ai_verification.moderation.action} — {complaint.ai_verification.moderation.reason}</p>
                    ) : (
                      <div className="mt-3 space-y-2">
                        <div className="flex flex-col sm:flex-row gap-2">
                          <select value={moderationAction} onChange={(e) => setModerationAction(e.target.value as typeof moderationAction)} className="rounded-lg border border-[#d8c4a8] bg-white px-3 py-2 text-xs">
                            <option value="not_spam">Not spam</option>
                            <option value="confirmed_spam">Confirmed spam</option>
                            <option value="escalated">Escalate for further review</option>
                          </select>
                          <input value={moderationReason} onChange={(e) => setModerationReason(e.target.value)} placeholder="Officer decision reason" className="flex-1 rounded-lg border border-[#d8c4a8] bg-white px-3 py-2 text-xs" />
                          <Button size="sm" disabled={moderationReason.trim().length < 5} isLoading={moderationMutation.isPending} onClick={() => moderationMutation.mutate()}>Record review</Button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </Card>

          {/* Media Evidence Gallery */}
          {complaint.media && complaint.media.length > 0 && (
            <Card className="p-6 space-y-4">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Uploaded Evidence Media
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {complaint.media.map((m) => (
                  <div
                    key={m.id}
                    className="group relative rounded-xl overflow-hidden border border-slate-200 dark:border-slate-800 aspect-video bg-slate-100"
                  >
                    {m.media_type === 'video' ? <video src={m.media_url} controls className="h-full w-full object-cover" aria-label="Complaint evidence video" /> : <img src={m.media_url} alt="Complaint Evidence" className="w-full h-full object-cover group-hover:scale-105 transition-transform" />}
                    {m.is_resolution_proof && (
                      <span className="absolute bottom-2 left-2 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-600 text-white">
                        Resolution Proof
                      </span>
                    )}
                    {m.is_resolution_evidence && (
                      <span className="absolute bottom-2 right-2 rounded bg-indigo-700 px-2 py-0.5 text-[10px] font-bold text-white">
                        Final evidence
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Public / Department Discussions */}
          <Card className="p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-indigo-600" /> Discussion & Updates
            </h3>

            <div className="space-y-3">
              {complaint.comments && complaint.comments.length > 0 ? (
                complaint.comments.map((comment) => (
                  <div
                    key={comment.id}
                    className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 text-xs"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-slate-900 dark:text-slate-100">
                        {comment.author_name || 'Anonymous User'}
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        {new Date(comment.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-slate-600 dark:text-slate-300">{comment.comment}</p>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-500 italic">No comments yet.</p>
              )}
            </div>

            {/* Comment Form */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (commentText.trim()) commentMutation.mutate(commentText);
              }}
              className="flex gap-2 pt-2"
            >
              <input
                type="text"
                placeholder="Write a message or update..."
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                className="flex-1 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <Button type="submit" size="sm" isLoading={commentMutation.isPending}>
                <Send className="w-3.5 h-3.5" />
              </Button>
            </form>
          </Card>
        </div>

        {/* Right Column: Meta Info & Status Audit Timeline */}
        <div className="space-y-6">
          <Card className="p-5 space-y-3 text-xs">
            <h4 className="font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider text-[11px] mb-2">
              Assignment & Logistics
            </h4>

            <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
              <Building className="w-4 h-4 text-slate-400" />
              <span>
                Department:{' '}
                <strong className="text-slate-900 dark:text-slate-200">
                  {complaint.assigned_department?.name || 'Pending assignment'}
                </strong>
              </span>
            </div>

            <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
              <User className="w-4 h-4 text-slate-400" />
              <span>
                Field Officer:{' '}
                <strong className="text-slate-900 dark:text-slate-200">
                  {complaint.assigned_staff?.full_name || 'Unassigned'}
                </strong>
              </span>
            </div>

            <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
              <MapPin className="w-4 h-4 text-slate-400" />
              <span>{complaint.address || 'Location coordinates logged'}</span>
            </div>

            <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
              <Calendar className="w-4 h-4 text-slate-400" />
              <span>Reported: {new Date(complaint.created_at).toLocaleDateString()}</span>
            </div>
          </Card>

          {/* Status Timeline */}
          <Card className="p-5 space-y-3">
            <h4 className="font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wider text-[11px] mb-1">
              Resolution Audit Trail
            </h4>
            <StatusTimeline history={complaint.status_history || []} />
          </Card>
        </div>
      </div>

      {/* Verification Modal */}
      <VerificationModal
        isOpen={isVerifying}
        onClose={() => setIsVerifying(false)}
        onSubmit={handleVerifySubmit}
        complaintPublicId={complaint.public_id}
      />
    </div>
  );
};
