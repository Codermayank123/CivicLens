import React, { useEffect, useRef, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  MapPin,
  CheckCircle,
  Upload,
} from 'lucide-react';
import toast from 'react-hot-toast';

import { complaintService } from '../services/complaint.service';
import { Complaint } from '../types';
import { StatusBadge, PriorityBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Modal } from '../components/ui/Modal';
import { ComplaintMap } from '../components/map/ComplaintMap';

export const FieldStaffDashboard: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedTask, setSelectedTask] = useState<Complaint | null>(null);
  const [beforeProof, setBeforeProof] = useState<File | null>(null);
  const [afterProof, setAfterProof] = useState<File | null>(null);
  const [proofPreviewUrls, setProofPreviewUrls] = useState<string[]>([]);
  const [workNotes, setWorkNotes] = useState('');
  const beforeInputRef = useRef<HTMLInputElement>(null);
  const afterInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!beforeProof && !afterProof) {
      setProofPreviewUrls([]);
      return;
    }
    const urls = [beforeProof, afterProof].filter(Boolean).map((file) => URL.createObjectURL(file!));
    setProofPreviewUrls(urls);
    return () => urls.forEach((url) => URL.revokeObjectURL(url));
  }, [beforeProof, afterProof]);

  const { data, isLoading } = useQuery({
    queryKey: ['assignedTasks'],
    queryFn: () => complaintService.getAssignedToMe(),
  });

  const resolveMutation = useMutation({
    mutationFn: async () => {
      if (!selectedTask || !beforeProof || !afterProof) throw new Error('Upload both before and after photographs before submitting.');
      const uploadedMedia = await Promise.all([beforeProof, afterProof].map((file) => complaintService.uploadMedia(file)));
      return complaintService.updateStatus(
        selectedTask!.id,
        'resolved',
        workNotes || 'Field staff completed work order and uploaded evidence proof.',
        uploadedMedia.map((media) => media.url),
        [
          { media_url: uploadedMedia[0].url, stage: 'before' },
          { media_url: uploadedMedia[1].url, stage: 'after' },
        ]
      );
    },
    onSuccess: () => {
      toast.success('Work order marked as resolved! Awaiting citizen verification.');
      setSelectedTask(null);
      setBeforeProof(null);
      setAfterProof(null);
      setWorkNotes('');
      queryClient.invalidateQueries({ queryKey: ['assignedTasks'] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.error?.message || error.message || 'Could not submit resolution.');
    },
  });

  const tasks = data?.items || [];

  const handleProofSelection = (event: React.ChangeEvent<HTMLInputElement>, kind: 'before' | 'after') => {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = '';
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      toast.error('Choose an image file for resolution evidence.');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast.error('Resolution evidence must be 10 MB or smaller.');
      return;
    }
    if (kind === 'before') setBeforeProof(file);
    else setAfterProof(file);
  };

  return (
    <div className="heritage-portal space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100">
          Field Operations Tasks
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Work orders assigned to you for physical repair and on-site evidence resolution.
        </p>
      </div>

      {/* Task Location Map */}
      <div className="space-y-2">
        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
          Task Locations Overview
        </h3>
        <ComplaintMap complaints={tasks} height="300px" />
      </div>

      {/* Task Cards List */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
          Assigned Tasks ({tasks.length})
        </h3>

        {isLoading ? (
          <div className="py-12 text-center text-xs text-slate-500">Loading assigned tasks...</div>
        ) : tasks.length === 0 ? (
          <Card className="p-8 text-center text-xs text-slate-500">
            No active tasks currently assigned to you.
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {tasks.map((task) => (
              <Card key={task.id} className="p-5 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-xs font-bold text-slate-500">
                      #{task.public_id}
                    </span>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={task.status} />
                      <PriorityBadge priority={task.priority} />
                    </div>
                  </div>

                  <h4 className="font-bold text-base text-slate-900 dark:text-slate-100 mb-1">
                    {task.title}
                  </h4>
                  <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2 mb-3">
                    {task.description}
                  </p>

                  {task.address && (
                    <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-2">
                      <MapPin className="w-3.5 h-3.5 text-indigo-500" />
                      <span>{task.address}</span>
                    </div>
                  )}
                </div>

                <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
                  <Link
                    to={`/complaints/${task.id}`}
                    className="text-xs font-semibold text-indigo-600 hover:underline"
                  >
                    View Details
                  </Link>

                  {task.status !== 'resolved' && task.status !== 'closed' && (
                    <Button
                      size="sm"
                      variant="success"
                      onClick={() => setSelectedTask(task)}
                      leftIcon={<CheckCircle className="w-3.5 h-3.5" />}
                      className="text-xs py-1 px-3"
                    >
                      Complete & Upload Proof
                    </Button>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Completion Modal */}
      <Modal
        isOpen={!!selectedTask}
        onClose={() => {
          setSelectedTask(null);
          setBeforeProof(null);
          setAfterProof(null);
          setWorkNotes('');
        }}
        title={`Complete Task #${selectedTask?.public_id}`}
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-500">
            Upload photographic proof that the issue was fixed and write a summary for citizen
            verification.
          </p>

          <div>
            <input
              ref={beforeInputRef}
              type="file"
              accept="image/*"
              onChange={(event) => handleProofSelection(event, 'before')}
              className="sr-only"
              aria-label="Choose before repair image"
            />
            <input ref={afterInputRef} type="file" accept="image/*" onChange={(event) => handleProofSelection(event, 'after')} className="sr-only" aria-label="Choose after repair image" />
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Before & after repair photographs
            </label>
            {proofPreviewUrls.length > 0 && (
              <div className="mb-3 grid grid-cols-2 gap-2">
                {proofPreviewUrls.map((url, index) => <img key={url} src={url} alt={index === 0 ? 'Selected before repair image' : 'Selected after repair image'} className="h-28 w-full object-cover" />)}
              </div>
            )}
            <div className="flex flex-wrap gap-2"><Button type="button" variant="outline" size="sm" onClick={() => beforeInputRef.current?.click()} leftIcon={<Upload className="w-3.5 h-3.5" />}>{beforeProof ? 'Replace before photo' : 'Choose before photo'}</Button><Button type="button" variant="outline" size="sm" onClick={() => afterInputRef.current?.click()} leftIcon={<Upload className="w-3.5 h-3.5" />}>{afterProof ? 'Replace after photo' : 'Choose after photo'}</Button></div>
            <p className="mt-2 text-xs text-slate-500">{beforeProof?.name || 'Before photo required'} · {afterProof?.name || 'After photo required'}</p>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Resolution Summary / Work Details
            </label>
            <textarea
              rows={3}
              value={workNotes}
              onChange={(e) => setWorkNotes(e.target.value)}
              placeholder="e.g. Repaired broken valve, restored water pressure, site cleared..."
              className="w-full text-xs p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" size="sm" onClick={() => setSelectedTask(null)}>
              Cancel
            </Button>
            <Button
              variant="success"
              size="sm"
              onClick={() => resolveMutation.mutate()}
              isLoading={resolveMutation.isPending}
              disabled={!beforeProof || !afterProof}
            >
              Submit Fixed Proof
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
