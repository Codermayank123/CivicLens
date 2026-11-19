import React, { useEffect, useState } from 'react';
import { Shield, AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { identityService, IdentityStatus } from '../services/identity.service';
import { useAuthStore } from '../store/authStore';

export const IdentityVerificationPage: React.FC = () => {
  const { user, initAuth } = useAuthStore();
  const [status, setStatus] = useState<IdentityStatus | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [shareCode, setShareCode] = useState('');
  const [encryptedXml, setEncryptedXml] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    identityService
      .getStatus()
      .then(setStatus)
      .catch(() => toast.error('Could not load identity verification status'));
  }, []);

  const startSession = async () => {
    if (!status) return;
    setLoading(true);
    try {
      const session = await identityService.startSession(status.consent_version);
      setSessionId(session.session_id);
      toast.success(session.message || 'Session started');
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error
          ?.message || 'Could not start verification session';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const submitOfflineEkyc = async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const result = await identityService.completeOfflineEkyc(sessionId, encryptedXml, shareCode);
      if (result.verified) {
        toast.success('Identity verified');
        await initAuth();
      } else {
        toast.error(result.message || 'Verification could not be completed');
      }
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error
          ?.message || 'Verification failed';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  if (user?.identity_verified) {
    return (
      <Card className="p-6 max-w-2xl mx-auto">
        <p className="text-sm text-slate-600">Your account is already identity-verified.</p>
      </Card>
    );
  }

  return (
    <div className="max-w-2xl mx-auto py-6 space-y-4">
      <Card className="p-6">
        <div className="flex items-start gap-3">
          <Shield className="w-6 h-6 text-indigo-600 shrink-0" />
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">Identity verification</h1>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
              CivicLens does not collect Aadhaar OTPs. Use UIDAI-authorized flows only.
            </p>
          </div>
        </div>

        {status && (
          <div className="mt-4 text-xs text-slate-600 dark:text-slate-400 space-y-1">
            <p>Provider: {status.provider}</p>
            <p>Sandbox: {status.is_sandbox ? 'yes' : 'no'}</p>
            <p>Consent version: {status.consent_version}</p>
          </div>
        )}

        <div
          role="note"
          className="mt-4 flex gap-2 border border-amber-300 bg-amber-50 p-3 text-xs text-amber-950"
        >
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>
            Production citizen registration stays disabled until your deployment is authorized by UIDAI,
            configured with real credentials, and tested end-to-end.
          </span>
        </div>

        <div className="mt-6 flex flex-wrap gap-2">
          <Button onClick={startSession} disabled={loading || !status?.supports_verification_sessions}>
            I consent — start session
          </Button>
        </div>
      </Card>

      {sessionId && status?.provider === 'uidai_offline_ekyc' && (
        <Card className="p-6 space-y-3">
          <h2 className="font-semibold text-sm">Offline e-KYC (mAadhaar)</h2>
          <p className="text-xs text-slate-500">
            Paste encrypted XML and share code. Data is validated and not retained.
          </p>
          <input
            className="w-full border rounded px-3 py-2 text-xs"
            placeholder="Share code"
            value={shareCode}
            onChange={(e) => setShareCode(e.target.value)}
          />
          <textarea
            className="w-full border rounded px-3 py-2 text-xs min-h-[120px]"
            placeholder="Encrypted offline e-KYC XML"
            value={encryptedXml}
            onChange={(e) => setEncryptedXml(e.target.value)}
          />
          <Button onClick={submitOfflineEkyc} disabled={loading || !shareCode || !encryptedXml}>
            Submit offline e-KYC
          </Button>
        </Card>
      )}
    </div>
  );
};
