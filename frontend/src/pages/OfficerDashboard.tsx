import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Search,
} from 'lucide-react';
import toast from 'react-hot-toast';

import { complaintService } from '../services/complaint.service';
import { departmentService } from '../services/department.service';
import { Complaint } from '../types';
import { StatusBadge, PriorityBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Modal } from '../components/ui/Modal';
import { Select } from '../components/ui/Select';

export const OfficerDashboard: React.FC = () => {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [selectedComplaint, setSelectedComplaint] = useState<Complaint | null>(null);
  const [assigneeId, setAssigneeId] = useState('');
  const [assignNotes, setAssignNotes] = useState('');
  const [statusModalComplaint, setStatusModalComplaint] = useState<Complaint | null>(null);
  const [newStatus, setNewStatus] = useState('in_progress');
  const [statusNotes, setStatusNotes] = useState('');
  const [resolutionFiles, setResolutionFiles] = useState<File[]>([]);

  // Fetch complaints
  const { data, isLoading } = useQuery({
    queryKey: ['officerComplaints', statusFilter, search],
    queryFn: () =>
      complaintService.getComplaints({
        status: statusFilter || undefined,
        search: search || undefined,
        per_page: 50,
      }),
  });

  // Fetch staff for assignment
  const { data: staff = [], isLoading: staffLoading } = useQuery({
    queryKey: ['staffMembers', selectedComplaint?.assigned_department_id],
    queryFn: () => departmentService.getStaff(selectedComplaint?.assigned_department_id),
    enabled: !!selectedComplaint?.assigned_department_id,
  });

  // Assign mutation
  const assignMutation = useMutation({
    mutationFn: () =>
      complaintService.assign(
        selectedComplaint!.id,
        undefined,
        assigneeId || undefined,
        assignNotes
      ),
    onSuccess: () => {
      toast.success('Complaint assigned to the selected field staff member.');
      setSelectedComplaint(null);
      setAssignNotes('');
      queryClient.invalidateQueries({ queryKey: ['officerComplaints'] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.error?.message || 'Assignment failed.');
    },
  });

  // Status mutation
  const statusMutation = useMutation({
    mutationFn: async () => {
      const isResolution = newStatus === 'resolved' || newStatus === 'citizen_verification_pending';
      if (isResolution && resolutionFiles.length === 0) throw new Error('Final evidence photographs are required.');
      const uploaded = isResolution
        ? await Promise.all(resolutionFiles.map((file) => complaintService.uploadMedia(file)))
        : [];
      return complaintService.updateStatus(
        statusModalComplaint!.id,
        newStatus,
        statusNotes,
        uploaded.map((item) => item.url),
        uploaded.map((item) => ({ media_url: item.url, stage: 'after' as const, caption: 'Final resolution photograph' })),
      );
    },
    onSuccess: () => {
      toast.success('Status updated.');
      setStatusModalComplaint(null);
      setStatusNotes('');
      setResolutionFiles([]);
      queryClient.invalidateQueries({ queryKey: ['officerComplaints'] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.error?.message || err.message || 'Status update failed.');
    },
  });

  const complaints = data?.items || [];

  return (
    <div className="premium-dashboard heritage-portal space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100">
            Department Officer Triage
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Review incoming citizen reports, assign field teams, and track resolution lifecycles.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <Card className="p-4 flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by ID, keyword, address..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="w-full sm:w-48">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full text-xs py-2 px-3 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All Statuses</option>
            <option value="submitted">Submitted</option>
            <option value="assigned">Assigned</option>
            <option value="in_progress">In Progress</option>
            <option value="resolved">Resolved</option>
            <option value="reopened">Reopened</option>
          </select>
        </div>
      </Card>

      {/* Complaints Table */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 text-slate-500 uppercase tracking-wider font-semibold">
              <tr>
                <th className="py-3 px-4">Ticket</th>
                <th className="py-3 px-4">Title</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Priority</th>
                <th className="py-3 px-4">Assigned Staff</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/80">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    Loading complaints...
                  </td>
                </tr>
              ) : complaints.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    No complaints found matching criteria.
                  </td>
                </tr>
              ) : (
                complaints.map((c) => (
                  <tr
                    key={c.id}
                    className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors"
                  >
                    <td className="py-3 px-4 font-mono font-semibold text-slate-600 dark:text-slate-300">
                      #{c.public_id}
                    </td>
                    <td className="py-3 px-4">
                      <Link
                        to={`/complaints/${c.id}`}
                        className="font-semibold text-slate-900 dark:text-slate-100 hover:text-indigo-600"
                      >
                        {c.title}
                      </Link>
                      <div className="text-[11px] text-slate-400 truncate max-w-xs">{c.address}</div>
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={c.status} />
                      {c.requires_human_review && (
                        <span className="mt-1 block text-[10px] font-semibold text-amber-700 dark:text-amber-300">
                          Human review required
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <PriorityBadge priority={c.priority} />
                    </td>
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-400">
                      {c.assigned_staff_name || (
                        <span className="italic text-slate-400">Unassigned</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setSelectedComplaint(c);
                          setAssigneeId(c.assigned_staff?.id || '');
                        }}
                        className="text-xs py-1 px-2.5 h-7"
                      >
                        Assign
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                          setStatusModalComplaint(c);
                          setNewStatus(c.status);
                          setResolutionFiles([]);
                        }}
                        className="text-xs py-1 px-2.5 h-7"
                      >
                        Status
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Assignment Modal */}
      <Modal
        isOpen={!!selectedComplaint}
        onClose={() => setSelectedComplaint(null)}
        title={`Assign Complaint #${selectedComplaint?.public_id}`}
      >
        <div className="space-y-4">
          <Select
            label="Assign to Field Staff Officer"
            value={assigneeId}
            onChange={(e) => setAssigneeId(e.target.value)}
            options={staff.map((s: any) => ({
              value: s.id,
              label: `${s.full_name} · ${s.department_name || 'Department field team'}`,
            }))}
          />
          {!staffLoading && staff.length === 0 && (
            <p role="alert" className="border-l-4 border-amber-500 bg-amber-50 p-3 text-xs text-amber-900">
              No active field staff are provisioned for this complaint&apos;s department. Ask an administrator to add a field staff account before assigning it.
            </p>
          )}
          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Assignment Notes / Instructions
            </label>
            <textarea
              rows={3}
              value={assignNotes}
              onChange={(e) => setAssignNotes(e.target.value)}
              placeholder="e.g. Inspect drainage blockage at Sector 4 before evening..."
              className="w-full text-xs p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {newStatus === 'rejected' && !statusNotes.trim() && <p className="mt-1 text-[11px] text-amber-700">A rejection reason is required for the citizen and audit trail.</p>}
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" size="sm" onClick={() => setSelectedComplaint(null)}>
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={() => assignMutation.mutate()}
              isLoading={assignMutation.isPending}
              disabled={!assigneeId || staff.length === 0}
            >
              Confirm Assignment
            </Button>
          </div>
        </div>
      </Modal>

      {/* Status Modal */}
      <Modal
        isOpen={!!statusModalComplaint}
        onClose={() => setStatusModalComplaint(null)}
        title={`Update Status #${statusModalComplaint?.public_id}`}
      >
        <div className="space-y-4">
          <Select
            label="New Status"
            value={newStatus}
            onChange={(e) => setNewStatus(e.target.value)}
            options={[
              { value: 'under_review', label: 'Under Review' },
              { value: 'assigned', label: 'Assigned' },
              { value: 'in_progress', label: 'In Progress' },
              { value: 'resolved', label: 'Resolved (Pending Citizen Verification)' },
              { value: 'citizen_verification_pending', label: 'Verified — Send to Citizen' },
              { value: 'rejected', label: 'Rejected' },
            ]}
          />
          <div>
            <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
              Transition Notes / Resolution Summary
            </label>
            <textarea
              rows={3}
              value={statusNotes}
              onChange={(e) => setStatusNotes(e.target.value)}
              placeholder="e.g. Work crew dispatched with asphalt patch truck..."
              className="w-full text-xs p-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          {(newStatus === 'resolved' || newStatus === 'citizen_verification_pending') && (
            <div className="space-y-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3">
              <label className="block text-xs font-semibold text-emerald-900">Final evidence photographs (required)</label>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                multiple
                onChange={(event) => setResolutionFiles(Array.from(event.target.files || []).slice(0, 10))}
                className="block w-full text-xs text-emerald-900"
              />
              {resolutionFiles.length > 0 && (
                <div className="grid grid-cols-3 gap-2">
                  {resolutionFiles.map((file) => (
                    <div key={`${file.name}-${file.lastModified}`} className="overflow-hidden rounded border border-emerald-200 bg-white">
                      <img src={URL.createObjectURL(file)} alt={file.name} className="h-20 w-full object-cover" />
                      <p className="truncate px-1 py-1 text-[10px] text-slate-600">{file.name}</p>
                    </div>
                  ))}
                </div>
              )}
              <p className="text-[11px] text-emerald-800">Upload completes before the complaint is marked resolved. If an upload or database save fails, no resolution email is sent.</p>
            </div>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" size="sm" onClick={() => setStatusModalComplaint(null)}>
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={() => statusMutation.mutate()}
              isLoading={statusMutation.isPending}
              disabled={!statusNotes.trim() || ((newStatus === 'resolved' || newStatus === 'citizen_verification_pending') && resolutionFiles.length === 0)}
            >
              Update Status
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
