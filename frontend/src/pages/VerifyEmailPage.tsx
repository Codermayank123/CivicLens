import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { CheckCircle2, ShieldAlert } from 'lucide-react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { authService } from '../services/auth.service';

export const VerifyEmailPage: React.FC = () => {
  const [params] = useSearchParams();
  const [state, setState] = useState<'loading' | 'success' | 'error'>('loading');

  useEffect(() => {
    const token = params.get('token');
    if (!token) {
      setState('error');
      return;
    }
    authService.verifyEmail(token).then(() => setState('success')).catch(() => setState('error'));
  }, [params]);

  return (
    <div className="mx-auto max-w-md py-12">
      <Card className="p-8 text-center shadow-xl">
        {state === 'success' ? <CheckCircle2 className="mx-auto mb-4 h-12 w-12 text-emerald-600" /> : <ShieldAlert className="mx-auto mb-4 h-12 w-12 text-amber-600" />}
        <h1 className="text-2xl font-bold">{state === 'loading' ? 'Verifying your email…' : state === 'success' ? 'Email verified' : 'Verification link unavailable'}</h1>
        <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">
          {state === 'loading' ? 'Please wait while CivicLens checks the secure token.' : state === 'success' ? 'Your email address is confirmed. You can continue to sign in.' : 'The link may be expired or already used. Request a new one from support.'}
        </p>
        {state !== 'loading' && <Link to="/login"><Button className="mt-6">Continue to sign in</Button></Link>}
      </Card>
    </div>
  );
};
