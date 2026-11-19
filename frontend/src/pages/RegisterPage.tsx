import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, ArrowLeft, CheckCircle2, Lock, Mail, Phone, RefreshCw, Shield, User } from 'lucide-react';
import toast from 'react-hot-toast';

import { authService } from '../services/auth.service';
import { useAuthStore } from '../store/authStore';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Card } from '../components/ui/Card';
import { useI18n } from '../i18n';

type VerificationMethod = 'email' | 'sms';
type AccountType = 'citizen' | 'officer' | 'field_staff';

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { setUser } = useAuthStore();
  const { t } = useI18n();
  const [method, setMethod] = useState<VerificationMethod>('email');
  const [accountType, setAccountType] = useState<AccountType>('citizen');
  const [step, setStep] = useState<'details' | 'otp'>('details');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirmation, setPasswordConfirmation] = useState('');
  const [code, setCode] = useState('');
  const [session, setSession] = useState<{ verification_session_id: string; verification_token: string; resend_after: number } | null>(null);
  const [cooldown, setCooldown] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  const passwordChecks = {
    length: password.length >= 10,
    upper: /[A-Z]/.test(password),
    lower: /[a-z]/.test(password),
    number: /\d/.test(password),
    special: /[^A-Za-z0-9]/.test(password),
  };
  const passwordStrong = Object.values(passwordChecks).every(Boolean);

  useEffect(() => {
    if (cooldown <= 0) return undefined;
    const timer = window.setInterval(() => setCooldown((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearInterval(timer);
  }, [cooldown]);

  const requestOtp = async (event?: React.FormEvent) => {
    event?.preventDefault();
    if (accountType !== 'citizen') {
      toast('Officer and Field Staff accounts are created by an authorized administrator. Please use an invitation or contact your department.', { icon: '🛡️' });
      return;
    }
    if (!passwordStrong || password !== passwordConfirmation) {
      toast.error(password !== passwordConfirmation ? 'Passwords do not match.' : 'Choose a stronger password using all the requirements shown below.');
      return;
    }
    if (method === 'sms' && !/^\+91[6-9]\d{9}$/.test(phone.replace(/[\s().-]/g, ''))) {
      toast.error(t('validIndianMobile'));
      return;
    }
    setIsLoading(true);
    try {
      const result = await authService.requestRegistrationOtp({
        full_name: fullName,
        email,
        phone: phone.trim() || undefined,
        password,
        verification_method: method,
      });
      setSession(result);
      setCooldown(result.resend_after);
      setStep('otp');
      toast.success(t(method === 'email' ? 'codeSentByEmail' : 'codeSentBySms'));
    } catch (err: any) {
      toast.error(err.response?.data?.error?.message || t('couldNotSendCode'));
    } finally {
      setIsLoading(false);
    }
  };

  const verifyAndComplete = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!session) return;
    setIsLoading(true);
    try {
      await authService.verifyRegistrationOtp({ verification_session_id: session.verification_session_id, verification_token: session.verification_token, code });
      const result = await authService.completeRegistration({ verification_session_id: session.verification_session_id, verification_token: session.verification_token });
      setUser(result.user);
      toast.success(t('accountReady'));
      navigate('/dashboard');
    } catch (err: any) {
      toast.error(err.response?.data?.error?.message || t('verificationFailed'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-md py-8">
      <Card className="p-8 shadow-xl">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-600 text-white shadow-md shadow-indigo-500/25">
            <Shield className="h-6 w-6" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{t('createAccount')}</h2>
          <p className="mt-1 text-xs text-slate-500">{t('verifyAccountDescription')}</p>
        </div>

        {step === 'details' ? (
          <form onSubmit={requestOtp} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">Account type</label>
              <div className="grid grid-cols-3 gap-2">
                {([['citizen', 'Citizen'], ['officer', 'Officer'], ['field_staff', 'Field Staff']] as const).map(([value, label]) => (
                  <button key={value} type="button" onClick={() => setAccountType(value)} className={`rounded-lg border px-2 py-2 text-xs font-semibold transition ${accountType === value ? 'border-indigo-500 bg-indigo-50 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300' : 'border-slate-200 text-slate-600 dark:border-slate-700 dark:text-slate-300'}`}>{label}</button>
                ))}
              </div>
              {accountType !== 'citizen' && <p className="mt-2 flex gap-1.5 rounded-lg border border-amber-200 bg-amber-50 p-2 text-xs text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200"><AlertCircle className="h-4 w-4 shrink-0" />Staff access requires an authorized administrator invitation.</p>}
            </div>
            <Input label={t('fullName')} value={fullName} onChange={(event) => setFullName(event.target.value)} required leftIcon={<User className="h-4 w-4" />} />
            <Input label={t('emailAddress')} type="email" value={email} onChange={(event) => setEmail(event.target.value)} required leftIcon={<Mail className="h-4 w-4" />} />
            <div className="grid grid-cols-2 gap-2">
              <Button type="button" variant={method === 'email' ? 'primary' : 'outline'} onClick={() => setMethod('email')}>
                <Mail className="mr-2 h-4 w-4" /> Email OTP
              </Button>
              <Button type="button" variant={method === 'sms' ? 'primary' : 'outline'} onClick={() => setMethod('sms')}>
                <Phone className="mr-2 h-4 w-4" /> SMS OTP
              </Button>
            </div>
            {method === 'sms' && (
              <Input label={t('internationalPhone')} placeholder="+919876543210" value={phone} onChange={(event) => setPhone(event.target.value)} required leftIcon={<Phone className="h-4 w-4" />} />
            )}
            <Input label={t('password')} type="password" value={password} onChange={(event) => setPassword(event.target.value)} required leftIcon={<Lock className="h-4 w-4" />} />
            <Input label="Confirm password" type="password" value={passwordConfirmation} onChange={(event) => setPasswordConfirmation(event.target.value)} required leftIcon={<Lock className="h-4 w-4" />} />
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs dark:border-slate-800 dark:bg-slate-900/60" aria-live="polite">
              <p className="mb-2 font-semibold text-slate-700 dark:text-slate-200">Password requirements</p>
              <div className="grid grid-cols-2 gap-1.5 text-slate-500 dark:text-slate-400">
                {Object.entries({ length: '10+ characters', upper: 'Uppercase letter', lower: 'Lowercase letter', number: 'Number', special: 'Special character' }).map(([key, label]) => {
                  const valid = passwordChecks[key as keyof typeof passwordChecks];
                  return <span key={key} className={valid ? 'text-emerald-600 dark:text-emerald-400' : ''}>{valid ? <CheckCircle2 className="mr-1 inline h-3.5 w-3.5" /> : <span className="mr-1 inline-block h-3.5 w-3.5 rounded-full border" />}{label}</span>;
                })}
              </div>
            </div>
            <Button type="submit" size="lg" className="mt-2 w-full" isLoading={isLoading}>{t('sendVerificationCode')}</Button>
          </form>
        ) : (
          <form onSubmit={verifyAndComplete} className="space-y-4">
            <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-xs text-indigo-900">{t('emailVerificationNotice')} {method === 'email' ? email : phone}. {t('verificationOnly')}</div>
            <Input label={t('verificationCode')} inputMode="numeric" autoComplete="one-time-code" value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 8))} required leftIcon={<Shield className="h-4 w-4" />} />
            <Button type="submit" size="lg" className="w-full" isLoading={isLoading} disabled={code.length < 4}>{t('verifyCreateAccount')}</Button>
            <div className="flex items-center justify-between text-xs">
              <button type="button" className="inline-flex items-center text-slate-600 hover:text-indigo-600" onClick={() => { setStep('details'); setCode(''); }}><ArrowLeft className="mr-1 h-3 w-3" /> {t('editDetails')}</button>
              <button type="button" className="inline-flex items-center text-indigo-600 disabled:text-slate-400" disabled={isLoading || cooldown > 0} onClick={() => requestOtp()}><RefreshCw className="mr-1 h-3 w-3" /> {cooldown > 0 ? `${t('resendIn')} ${cooldown}s` : t('resendCode')}</button>
            </div>
          </form>
        )}

        <p className="mt-6 text-center text-xs text-slate-500">{t('alreadyRegistered')} <Link to="/login" className="font-semibold text-indigo-600 hover:underline">{t('signInHere')}</Link></p>
      </Card>
    </div>
  );
};
