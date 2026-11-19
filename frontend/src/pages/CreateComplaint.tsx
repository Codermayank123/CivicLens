import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Mic,
  MicOff,
  Sparkles,
  MapPin,
  Upload,
  AlertTriangle,
  Image as ImageIcon,
  Camera,
  X,
} from 'lucide-react';
import toast from 'react-hot-toast';

import { complaintService } from '../services/complaint.service';
import { departmentService } from '../services/department.service';
import { queueOfflineComplaint } from '../services/offline/db';
import { useUIStore } from '../store/uiStore';
import { useGeolocation } from '../hooks/useGeolocation';
import { useVoiceInput } from '../hooks/useVoiceInput';
import { useI18n } from '../i18n';

import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Card } from '../components/ui/Card';
import { LocationPicker } from '../components/map/LocationPicker';

interface EvidenceFile {
  file: File;
  previewUrl: string;
}

interface AISuggestion {
  category?: string;
  urgency?: string;
  suggested_priority?: string;
  confidence?: number | null;
  confidence_status?: 'available' | 'unavailable';
  department?: string | null;
  is_relevant?: boolean;
  provider_unavailable?: boolean;
  requires_human_review?: boolean;
  message?: string;
  is_mock?: boolean;
}

const MAX_EVIDENCE_FILES = 5;
const MAX_EVIDENCE_SIZE = 10 * 1024 * 1024;

export const CreateComplaint: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isOnline } = useUIStore();
  const { language, t } = useI18n();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [priority, setPriority] = useState('medium');
  const [address, setAddress] = useState('');
  const [landmark, setLandmark] = useState('');
  const [mediaFiles, setMediaFiles] = useState<EvidenceFile[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [aiAnalyzing, setAiAnalyzing] = useState(false);
  const [aiResult, setAiResult] = useState<AISuggestion | null>(null);
  const [duplicates, setDuplicates] = useState<any[]>([]);
  const galleryInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const evidenceFilesRef = useRef<EvidenceFile[]>([]);
  const aiRequestId = useRef(0);

  const {
    coordinates,
    setCoordinates,
    loading: isLocating,
    error: locationError,
    address: detectedAddress,
    getCurrentLocation,
  } = useGeolocation();

  useEffect(() => {
    if (!detectedAddress) return;
    if (detectedAddress.formatted_address) setAddress(detectedAddress.formatted_address);
  }, [detectedAddress]);

  const { isListening, isSupported: voiceSupported, startListening, stopListening } = useVoiceInput(
    (text) => {
      setDescription((prev) => (prev ? `${prev} ${text}` : text));
    }
  );

  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: () => departmentService.getCategories(),
  });

  const { data: nearbyComplaints = [] } = useQuery({
    queryKey: ['nearby-complaints', coordinates?.lat, coordinates?.lng],
    queryFn: () => complaintService.getNearby(coordinates!.lat, coordinates!.lng),
    enabled: isOnline && !!coordinates,
    staleTime: 30_000,
  });

  const supportMutation = useMutation({
    mutationFn: complaintService.support,
    onSuccess: () => {
      toast.success('Thanks — your neighbourhood support was recorded.');
      queryClient.invalidateQueries({ queryKey: ['nearby-complaints'] });
    },
    onError: (error: any) =>
      toast.error(error.response?.data?.error?.message || 'Could not support this complaint.'),
  });

  useEffect(() => {
    evidenceFilesRef.current = mediaFiles;
  }, [mediaFiles]);

  useEffect(
    () => () => evidenceFilesRef.current.forEach(({ previewUrl }) => URL.revokeObjectURL(previewUrl)),
    []
  );

  const resolveCategoryId = (slug?: string) => {
    if (!categories.length) return '';
    if (slug) {
      const matched = categories.find((c) => c.slug.toLowerCase() === slug.toLowerCase());
      if (matched) return matched.id;
    }
    const fallback =
      categories.find((c) => c.slug === 'other') ||
      categories.find((c) => c.slug === 'infrastructure');
    return fallback?.id || '';
  };

  const applyAISuggestion = (res: AISuggestion) => {
    setAiResult(res);
    const nextCategoryId = resolveCategoryId(res.category);
    if (nextCategoryId) setCategoryId(nextCategoryId);
    if (res.suggested_priority) setPriority(res.suggested_priority);
    else if (res.urgency === 'high') setPriority('high');
    else if (res.urgency === 'low') setPriority('low');
  };

  const runAITriage = async (sourceText: string, silent = false): Promise<AISuggestion | null> => {
    if (!isOnline || sourceText.trim().length < 10) return null;
    const requestId = ++aiRequestId.current;
    setAiAnalyzing(true);
    try {
      const res = (await complaintService.suggestAI(sourceText.trim())) as AISuggestion;
      if (requestId !== aiRequestId.current) return res;
      applyAISuggestion(res);

      if (res.provider_unavailable) {
        if (!silent) {
          toast('AI triage is temporarily unavailable. Your report will go to officer review.', {
            icon: '⚠️',
          });
        }
        return res;
      }

      if (res.is_relevant === false) {
        if (!silent) {
          toast(
            'AI could not confidently recognize a civic issue. It will be submitted for human review.',
            { icon: '⚠️' }
          );
        }
        return res;
      }

      if (!silent) {
        if (res.confidence_status === 'available' && typeof res.confidence === 'number') {
          toast.success(
            `AI categorized as "${(res.category || 'other').replace(/_/g, ' ')}" · ${Math.round(res.confidence * 100)}% confidence${
              res.department ? ` · ${res.department}` : ''
            }`
          );
        } else {
          toast(
            `AI suggested "${(res.category || 'other').replace(/_/g, ' ')}". Confidence was not returned by the provider; officers will confirm.`,
            { icon: 'ℹ️' }
          );
        }
      }
      return res;
    } catch {
      if (requestId !== aiRequestId.current) return null;
      const fallbackId = resolveCategoryId('other');
      if (fallbackId) setCategoryId(fallbackId);
      const unavailable: AISuggestion = {
        category: 'other',
        confidence: null,
        confidence_status: 'unavailable',
        provider_unavailable: true,
        requires_human_review: true,
        message: 'AI analysis is temporarily unavailable.',
      };
      setAiResult(unavailable);
      if (!silent) toast.error('AI suggestion service temporarily unavailable.');
      return unavailable;
    } finally {
      if (requestId === aiRequestId.current) setAiAnalyzing(false);
    }
  };

  // Automatic triage once the description is substantial enough.
  useEffect(() => {
    const text = `${title}. ${description}`.trim();
    if (description.trim().length < 20) return;
    const timer = window.setTimeout(() => {
      void runAITriage(text, true);
    }, 900);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [title, description, categories.length, isOnline]);

  const handleCheckDuplicates = async () => {
    if (title.trim().length < 5 || description.trim().length < 10 || !categoryId) return;
    try {
      const res = await complaintService.checkDuplicates(
        title,
        description,
        categoryId,
        coordinates?.lat,
        coordinates?.lng
      );
      setDuplicates(res || []);
    } catch {
      // Ignore background duplicate check failure
    }
  };

  const handleEvidenceSelection = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.currentTarget.files || []);
    const availableSlots = MAX_EVIDENCE_FILES - mediaFiles.length;
    const acceptedFiles: EvidenceFile[] = [];

    for (const file of selectedFiles) {
      if (acceptedFiles.length >= availableSlots) break;
      if (!file.type.startsWith('image/') && file.type !== 'video/mp4') {
        toast.error(`${file.name}: choose an image or MP4 video.`);
        continue;
      }
      if (file.size > MAX_EVIDENCE_SIZE) {
        toast.error(`${file.name}: evidence must be 10 MB or smaller.`);
        continue;
      }
      acceptedFiles.push({ file, previewUrl: URL.createObjectURL(file) });
    }

    if (selectedFiles.length > availableSlots) {
      toast.error(`You can attach up to ${MAX_EVIDENCE_FILES} files.`);
    }
    if (acceptedFiles.length > 0) setMediaFiles((current) => [...current, ...acceptedFiles]);
    event.currentTarget.value = '';
  };

  const removeEvidence = (fileToRemove: EvidenceFile) => {
    URL.revokeObjectURL(fileToRemove.previewUrl);
    setMediaFiles((current) => current.filter((item) => item !== fileToRemove));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !description) {
      toast.error('Please fill in title and description.');
      return;
    }

    let latestAI = aiResult;
    let resolvedCategoryId = categoryId;
    if (!resolvedCategoryId || !latestAI) {
      latestAI = await runAITriage(`${title}. ${description}`, true);
      resolvedCategoryId =
        resolveCategoryId(latestAI?.category) || resolveCategoryId('other') || categoryId;
    }
    if (!resolvedCategoryId) {
      toast.error('Categories are still loading. Please try again in a moment.');
      return;
    }

    if (latestAI?.is_relevant === false || latestAI?.provider_unavailable) {
      toast('This report will be submitted for human review.', { icon: '⚠️' });
    }

    setIsSubmitting(true);
    const payload = {
      title,
      description,
      category_id: resolvedCategoryId,
      priority,
      latitude: coordinates?.lat,
      longitude: coordinates?.lng,
      address,
      landmark,
      state: detectedAddress?.state,
      district: detectedAddress?.district,
      city: detectedAddress?.city,
      locality: detectedAddress?.locality,
      pincode: detectedAddress?.pincode,
      language,
    };

    try {
      if (!isOnline) {
        await queueOfflineComplaint({
          ...payload,
          media_files: mediaFiles.map(({ file }) => file),
        });
        toast.success('You are offline. Issue saved locally and will auto-sync once connected!');
        navigate('/sync-queue');
      } else {
        const uploadedMedia = await Promise.all(
          mediaFiles.map(({ file }) => complaintService.uploadMedia(file))
        );
        const created = await complaintService.create({
          ...payload,
          media_urls: uploadedMedia.map((media) => media.url),
          media_metadata: uploadedMedia.map(({ file_name, file_size, mime_type }) => ({
            file_name,
            file_size,
            mime_type,
          })),
        });
        toast.success(`Complaint #${created.public_id} submitted successfully!`);
        navigate(`/complaints/${created.id}`);
      }
    } catch (err: any) {
      const detail = err.response?.data?.error?.message ?? err.response?.data?.detail;
      const message = Array.isArray(detail)
        ? detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join(' ')
        : typeof detail === 'string'
          ? detail
          : 'Failed to submit complaint.';
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const matchedCategory = categories.find((c) => c.id === categoryId);
  const confidenceLabel =
    aiResult?.confidence_status === 'available' && typeof aiResult.confidence === 'number'
      ? aiResult.confidence >= 0.75
        ? 'High'
        : aiResult.confidence >= 0.5
          ? 'Medium'
          : 'Low'
      : 'Unavailable';

  return (
    <div className="max-w-3xl mx-auto py-4 space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-[var(--heritage-charcoal)] dark:text-[var(--heritage-ivory)]">
          {t('reportInfrastructureIssue')}
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
          {t('reportInfrastructureDescription')}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {nearbyComplaints.length > 0 && (
          <Card className="border-[var(--heritage-gold)] bg-[#fffaf3] p-5 dark:bg-[#2a2230] dark:border-[#5c4a2e]">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 text-[var(--heritage-terracotta)]" />
              <div>
                <h2 className="font-bold text-[var(--heritage-plum)] dark:text-[var(--heritage-ivory)]">
                  Neighbourhood alerts
                </h2>
                <p className="mt-1 text-xs text-[#66565f] dark:text-slate-400">
                  An active report is already near this location. Support it so the department sees
                  the community impact, instead of creating duplicate work.
                </p>
              </div>
            </div>
            <div className="mt-3 space-y-2">
              {nearbyComplaints.slice(0, 3).map((nearby) => (
                <div
                  key={nearby.id}
                  className="flex flex-col gap-2 border-t border-[#eadcc6] pt-3 sm:flex-row sm:items-center dark:border-slate-700"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-[var(--heritage-charcoal)] dark:text-slate-100">
                      #{nearby.public_id} · {nearby.title}
                    </p>
                    <p className="text-xs text-[#66565f] dark:text-slate-400">
                      {nearby.category_name || 'Civic issue'} · {nearby.status.replace('_', ' ')}
                    </p>
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={supportMutation.isPending}
                    onClick={() => supportMutation.mutate(nearby.id)}
                  >
                    Support report
                  </Button>
                </div>
              ))}
            </div>
          </Card>
        )}

        <Card className="p-6 space-y-4">
          <Input
            label="Issue Title"
            placeholder="e.g. Hazardous deep pothole on Main Ring Road"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onBlur={handleCheckDuplicates}
            minLength={5}
            maxLength={255}
            required
          />

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Detailed Description
              </label>
              <div className="flex items-center gap-2">
                {voiceSupported && (
                  <Button
                    type="button"
                    variant={isListening ? 'danger' : 'outline'}
                    size="sm"
                    onClick={isListening ? stopListening : startListening}
                    leftIcon={
                      isListening ? <MicOff className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5" />
                    }
                    className="text-xs py-1 h-7"
                  >
                    {isListening ? 'Stop Dictating' : 'Voice Input'}
                  </Button>
                )}
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => void runAITriage(`${title}. ${description}`)}
                  isLoading={aiAnalyzing}
                  leftIcon={<Sparkles className="w-3.5 h-3.5 text-[var(--heritage-plum)]" />}
                  className="text-xs py-1 h-7"
                >
                  AI Auto-Triage
                </Button>
              </div>
            </div>

            <textarea
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              onBlur={() => {
                void runAITriage(`${title}. ${description}`);
                void handleCheckDuplicates();
              }}
              placeholder="Describe what is broken, visible hazards, approximate duration of issue..."
              minLength={10}
              maxLength={5000}
              required
              className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 p-3 text-sm focus:ring-2 focus:ring-[var(--heritage-plum)] outline-none"
            />

            <div className="mt-3 rounded-xl border border-[var(--heritage-plum)]/20 bg-[var(--heritage-plum)]/5 p-3 dark:border-[var(--heritage-gold)]/30 dark:bg-[#2a2230]">
              <div className="flex items-center gap-2 text-xs font-semibold text-[var(--heritage-plum)] dark:text-[var(--heritage-gold)]">
                <Sparkles className="h-3.5 w-3.5" />
                AI automatic triage
                {aiAnalyzing && <span className="font-normal opacity-70">Analyzing…</span>}
              </div>
              {aiResult ? (
                <div className="mt-2 grid gap-1 text-xs text-slate-700 dark:text-slate-300 sm:grid-cols-2">
                  <p>
                    Category:{' '}
                    <strong>
                      {matchedCategory?.name ||
                        (aiResult.category || 'other').replace(/_/g, ' ')}
                    </strong>
                  </p>
                  <p>
                    Department: <strong>{aiResult.department || matchedCategory?.department_name || 'Pending'}</strong>
                  </p>
                  <p>
                    Urgency: <strong>{aiResult.urgency || priority}</strong>
                  </p>
                  <p>
                    Confidence:{' '}
                    <strong>
                      {confidenceLabel}
                      {aiResult.confidence_status === 'available' &&
                      typeof aiResult.confidence === 'number'
                        ? ` (${Math.round(aiResult.confidence * 100)}%)`
                        : ''}
                    </strong>
                  </p>
                  {(aiResult.provider_unavailable ||
                    aiResult.requires_human_review ||
                    aiResult.is_relevant === false) && (
                    <p className="sm:col-span-2 text-[var(--heritage-terracotta)]">
                      {aiResult.message ||
                        'This submission will be routed for human review.'}
                    </p>
                  )}
                </div>
              ) : (
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Category, department, severity and confidence are assigned automatically from your
                  description. Manual category selection is not required.
                </p>
              )}
            </div>
          </div>
        </Card>

        <Card className="p-6 space-y-4">
          <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <MapPin className="w-5 h-5 text-[var(--heritage-plum)]" /> Geographic Location
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Street Address / Road Name"
              placeholder="e.g. Ring Road, Sector 4 Cross"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
            />
            <Input
              label="Nearby Landmark"
              placeholder="e.g. Near Metro Station Gate 2"
              value={landmark}
              onChange={(e) => setLandmark(e.target.value)}
            />
          </div>

          <LocationPicker
            latitude={coordinates?.lat ?? 28.6139}
            longitude={coordinates?.lng ?? 77.209}
            onChange={(lat, lng) => setCoordinates({ lat, lng })}
            onGetCurrentLocation={getCurrentLocation}
            isLocating={isLocating}
          />
          {locationError && (
            <p
              role="status"
              className="border-l-4 border-amber-500 bg-amber-50 p-3 text-sm text-slate-900 dark:bg-amber-950/40 dark:text-amber-100"
            >
              {locationError}
            </p>
          )}
        </Card>

        <Card className="p-6 space-y-4">
          <input
            ref={galleryInputRef}
            type="file"
            accept="image/*,video/mp4"
            multiple
            onChange={handleEvidenceSelection}
            className="sr-only"
            aria-label="Choose photos and MP4 videos"
          />
          <input
            ref={cameraInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleEvidenceSelection}
            className="sr-only"
            aria-label="Take a photo"
          />
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <ImageIcon className="w-5 h-5 text-[var(--heritage-plum)]" /> Photo & Video Evidence
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Up to 5 files, 10 MB each. Images or MP4 video. Vision AI reviews evidence on submit.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => cameraInputRef.current?.click()}
                leftIcon={<Camera className="w-3.5 h-3.5" />}
              >
                Take Photo
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => galleryInputRef.current?.click()}
                leftIcon={<Upload className="w-3.5 h-3.5" />}
              >
                Add Files
              </Button>
            </div>
          </div>

          {mediaFiles.length > 0 ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {mediaFiles.map((item) => (
                <div
                  key={item.previewUrl}
                  className="relative min-w-0 border border-slate-300 bg-white dark:border-slate-600 dark:bg-slate-900"
                >
                  {item.file.type.startsWith('video/') ? (
                    <video src={item.previewUrl} controls className="aspect-video w-full object-cover" />
                  ) : (
                    <img
                      src={item.previewUrl}
                      alt={`Evidence: ${item.file.name}`}
                      className="aspect-video w-full object-cover"
                    />
                  )}
                  <div className="flex items-center justify-between gap-2 p-2">
                    <span className="truncate text-xs dark:text-slate-300">{item.file.name}</span>
                    <button
                      type="button"
                      onClick={() => removeEvidence(item)}
                      className="shrink-0 p-1"
                      aria-label={`Remove ${item.file.name}`}
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div
              onClick={() => galleryInputRef.current?.click()}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') galleryInputRef.current?.click();
              }}
              role="button"
              tabIndex={0}
              className="border-2 border-dashed border-slate-400 p-6 text-center cursor-pointer hover:bg-[var(--heritage-ivory)] transition-colors dark:border-slate-600 dark:hover:bg-slate-800"
            >
              <Upload className="w-8 h-8 text-slate-400 mx-auto mb-2" />
              <p className="text-xs text-slate-700 dark:text-slate-300">
                Choose photos or MP4 video evidence
              </p>
            </div>
          )}
        </Card>

        {duplicates.length > 0 && (
          <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 space-y-2">
            <div className="flex items-center gap-2 text-amber-800 dark:text-amber-300 font-semibold text-xs">
              <AlertTriangle className="w-4 h-4" />
              <span>Potential Duplicate Issues Detected Nearby:</span>
            </div>
            <div className="space-y-1">
              {duplicates.slice(0, 2).map((dup) => (
                <div
                  key={dup.id}
                  className="text-xs text-amber-700 dark:text-amber-400 flex justify-between"
                >
                  <span>
                    #{dup.public_id}: {dup.title}
                  </span>
                  <span className="font-mono text-[10px]">
                    {Math.round(dup.similarity_score * 100)}% match
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={() => navigate(-1)}>
            Cancel
          </Button>
          <Button type="submit" size="lg" isLoading={isSubmitting || aiAnalyzing}>
            {isOnline ? 'Submit Complaint' : 'Save for Offline Sync'}
          </Button>
        </div>
      </form>
    </div>
  );
};
