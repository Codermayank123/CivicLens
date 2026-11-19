import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, Eye, ShieldAlert, XCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { complaintService } from '../services/complaint.service';
import { Complaint } from '../types';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { StatusBadge, PriorityBadge } from '../components/ui/Badge';

export const AIReviewPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<Complaint | null>(null);
  const [reason, setReason] = useState('');
  const { data, isLoading } = useQuery({
    queryKey: ['ai-review-queue'],
    queryFn: () => complaintService.getAIReviewQueue(),
    refetchInterval: 30_000,
  });
  const reviewMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'approve' | 'reject' | 'request_information' }) => complaintService.reviewAIModeration(id, action, reason || 'Reviewed by an authorized officer.'),
    onSuccess: () => {
      toast.success('AI review decision recorded and the citizen has been notified.');
      setSelected(null);
      setReason('');
      queryClient.invalidateQueries({ queryKey: ['ai-review-queue'] });
      queryClient.invalidateQueries({ queryKey: ['adminStats'] });
    },
    onError: (error: any) => toast.error(error.response?.data?.error?.message || 'Could not record the review decision.'),
  });
  const items = data?.items || [];

  const decide = (action: 'approve' | 'reject' | 'request_information') => {
    if (!selected) return;
    if (reason.trim().length < 5) {
      toast.error('Add a short explanation before recording a decision.');
      return;
    }
    reviewMutation.mutate({ id: selected.id, action });
  };

  return (
    <div className="heritage-portal space-y-6 py-4">
      <div>
        <p className="heritage-kicker flex items-center gap-2"><ShieldAlert className="h-4 w-4" /> Responsible AI oversight</p>
        <h1 className="heritage-section-title">AI Verification & Human Review</h1>
        <p className="heritage-subtitle">Uncertain AI decisions stay reviewable. Inspect the original complaint, evidence signals, explanation, and audit trail before deciding.</p>
      </div>
      {isLoading ? <div className="py-16 text-center text-sm text-[#66565f]">Loading the verification queue…</div> : items.length === 0 ? <Card className="p-10 text-center"><CheckCircle2 className="mx-auto h-8 w-8 text-[#286b50]" /><p className="mt-3 font-semibold text-[#4b205b]">No complaints are waiting for human review.</p><p className="mt-1 text-xs text-[#66565f]">New uncertain, duplicate, or evidence-mismatch reports will appear here.</p></Card> : <div className="grid gap-4 lg:grid-cols-2">{items.map((item) => <ReviewCard key={item.id} complaint={item} onReview={() => { setSelected(item); setReason(''); }} />)}</div>}

      {selected && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
        <Card className="max-h-[90vh] w-full max-w-2xl overflow-y-auto p-6">
          <div className="flex items-start justify-between gap-4"><div><p className="font-mono text-xs text-[#9a4d12]">#{selected.public_id}</p><h2 className="mt-1 text-xl font-bold text-[#4b205b]">{selected.title}</h2></div><button type="button" aria-label="Close review" onClick={() => setSelected(null)} className="text-xl text-[#66565f]">×</button></div>
          <div className="mt-4 grid gap-3 sm:grid-cols-3"><Metric label="AI outcome" value={selected.ai_outcome || 'human_review'} /><Metric label="Confidence" value={`${Math.round((selected.ai_confidence || 0) * 100)}%`} /><Metric label="Model" value={selected.ai_model_version || 'civiclens-ai-1'} /></div>
          <div className="mt-5 space-y-3 text-sm"><p><strong>Description:</strong> {selected.description}</p><p><strong>AI explanation:</strong> {selected.ai_reason || selected.ai_verification?.reason || 'No explanation provided.'}</p><p><strong>Signals:</strong> {(selected.ai_verification?.suspicious_reasons || []).join('; ') || 'No explicit suspicious signal.'}</p>{selected.media?.length ? <div><strong>Evidence:</strong><div className="mt-2 grid grid-cols-2 gap-2">{selected.media.map((media) => <div key={media.id} className="border border-[#dcc6a7] p-2"><img src={media.media_url} alt={media.file_name || 'Complaint evidence'} className="h-28 w-full object-cover" /><p className="mt-1 text-[11px] text-[#66565f]">{media.evidence_stage || 'supporting evidence'}</p></div>)}</div></div> : null}</div>
          <label className="mt-5 block text-sm font-semibold text-[#4b205b]">Reviewer explanation<textarea value={reason} onChange={(event) => setReason(event.target.value)} rows={3} className="mt-2 w-full border border-[#dcc6a7] bg-[#fffaf3] p-3 text-sm" placeholder="Explain why this is accepted, rejected, or needs more information." /></label>
          <div className="mt-5 flex flex-wrap justify-end gap-2"><Button variant="secondary" onClick={() => decide('request_information')} isLoading={reviewMutation.isPending}>Request information</Button><Button variant="danger" onClick={() => decide('reject')} isLoading={reviewMutation.isPending} leftIcon={<XCircle className="h-4 w-4" />}>Reject</Button><Button onClick={() => decide('approve')} isLoading={reviewMutation.isPending} leftIcon={<CheckCircle2 className="h-4 w-4" />}>Approve & forward</Button></div>
        </Card>
      </div>}
    </div>
  );
};

const Metric: React.FC<{ label: string; value: string }> = ({ label, value }) => <div className="border border-[#dcc6a7] bg-[#fffaf3] p-3"><p className="text-[10px] font-bold uppercase tracking-wide text-[#9a4d12]">{label}</p><p className="mt-1 font-semibold text-[#29232b]">{value}</p></div>;

const ReviewCard: React.FC<{ complaint: Complaint; onReview: () => void }> = ({ complaint, onReview }) => <Card className="p-5"><div className="flex items-start justify-between gap-3"><div><p className="font-mono text-xs text-[#9a4d12]">#{complaint.public_id}</p><h2 className="mt-1 font-bold text-[#29232b]">{complaint.title}</h2></div><div className="flex gap-2"><StatusBadge status={complaint.status} /><PriorityBadge priority={complaint.priority} /></div></div><p className="mt-3 line-clamp-3 text-sm text-[#66565f]">{complaint.description}</p><div className="mt-4 grid grid-cols-3 gap-2 text-xs"><Metric label="Outcome" value={complaint.ai_outcome || 'human_review'} /><Metric label="Confidence" value={`${Math.round((complaint.ai_confidence || 0) * 100)}%`} /><Metric label="Evidence" value={`${complaint.media?.length || 0} file(s)`} /></div><div className="mt-4 flex items-center justify-between gap-3"><span className="text-xs text-[#66565f]">{complaint.ai_reason || 'Review signals available in the case.'}</span><Button size="sm" onClick={onReview} leftIcon={<Eye className="h-4 w-4" />}>Inspect case</Button></div></Card>;
