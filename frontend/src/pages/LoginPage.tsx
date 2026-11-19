import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { Lock, Mail, Shield, ArrowRight } from 'lucide-react';
import toast from 'react-hot-toast';
import { authService } from '../services/auth.service';
import { useAuthStore } from '../store/authStore';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Card } from '../components/ui/Card';
import { DEMO_USERS } from '../config/constants';
import { useI18n } from '../i18n';

export const LoginPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setUser } = useAuthStore();
  const { t } = useI18n();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState(import.meta.env.DEV ? DEMO_USERS[0].password : '');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const urlEmail = searchParams.get('email');
    if (urlEmail) {
      setEmail(urlEmail);
    } else if (import.meta.env.DEV) {
      setEmail(DEMO_USERS[0].email);
    } else {
      setEmail('');
    }
  }, [searchParams]);

  const loginWithCredentials = async (loginEmail: string, loginPassword: string) => {
    setIsLoading(true);
    try {
      const res = await authService.login({ email: loginEmail, password: loginPassword });
      setUser(res.user);
      toast.success(`${t('signIn')}: ${res.user.full_name}`);

      // Route according to user role
      const primaryRole = res.user.roles?.[0] || 'citizen';
      if (primaryRole === 'admin') navigate('/admin');
      else if (primaryRole === 'officer') navigate('/officer/triage');
      else if (primaryRole === 'field_staff') navigate('/field/tasks');
      else navigate('/dashboard');
    } catch (err: any) {
      toast.error(err.response?.data?.error?.message || t('loginFailed'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogin = async (event?: React.FormEvent) => {
    event?.preventDefault();
    await loginWithCredentials(email, password);
  };

  const handleDemoLogin = async (demoEmail: string) => {
    const demo = DEMO_USERS.find((item) => item.email === demoEmail);
    if (!demo || !import.meta.env.DEV) return;
    setEmail(demo.email);
    setPassword(demo.password);
    await loginWithCredentials(demo.email, demo.password);
  };

  return (
    <div className="max-w-md mx-auto py-8">
      <Card className="p-8 shadow-xl">
        <div className="text-center mb-6">
          <div className="w-12 h-12 rounded-2xl bg-[var(--heritage-plum)] text-[var(--heritage-ivory)] flex items-center justify-center mx-auto mb-3 shadow-md shadow-[var(--heritage-plum)]/25">
            <Shield className="w-6 h-6" />
          </div>
          <h2 className="text-2xl font-bold text-[var(--heritage-charcoal)] dark:text-[var(--heritage-ivory)]">{t('loginToCivicLens')}</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{t('impact')}</p>
        </div>

        {import.meta.env.DEV && (
          <div className="mb-6 rounded-xl border border-[#dcc6a7] bg-[#fffaf3] p-3 dark:border-[#3d3344] dark:bg-[#2a2230]">
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              {t('developmentAccounts')}
            </p>
            <div className="grid grid-cols-2 gap-1.5">
              {DEMO_USERS.map((demo) => (
                <button
                  key={demo.role}
                  type="button"
                  onClick={() => void handleDemoLogin(demo.email)}
                  disabled={isLoading}
                  className={`rounded-lg border px-2 py-1.5 text-left text-xs transition-all ${
                    email === demo.email
                      ? 'border-[var(--heritage-plum)] bg-[var(--heritage-plum)]/10 font-medium text-[var(--heritage-plum)] dark:bg-[var(--heritage-gold)]/15 dark:text-[var(--heritage-gold)] dark:border-[var(--heritage-gold)]'
                      : 'border-slate-200 text-slate-600 hover:bg-white dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700'
                  }`}
                >
                  {demo.role}
                </button>
              ))}
            </div>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <Input
            label={t('emailAddress')}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            leftIcon={<Mail className="w-4 h-4" />}
          />

          <Input
            label={t('password')}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            leftIcon={<Lock className="w-4 h-4" />}
          />

          <Button type="submit" size="lg" className="w-full mt-2" isLoading={isLoading}>
            {t('signIn')} <ArrowRight className="w-4 h-4 ml-1" />
          </Button>
        </form>

        <p className="text-center text-xs text-slate-500 mt-6">
          {t('dontHaveAccount')}{' '}
          <Link to="/register" className="text-[var(--heritage-plum)] dark:text-[var(--heritage-gold)] font-semibold hover:underline">
            {t('register')}
          </Link>
        </p>
      </Card>
    </div>
  );
};
