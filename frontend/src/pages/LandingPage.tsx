import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, Building2, CheckCircle2, Clipboard, Landmark, MapPinned, ShieldCheck, Sparkles, UsersRound } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { departmentService } from '../services/department.service';
import { publicService } from '../services/public.service';
import { useI18n } from '../i18n';
import { CivicLensScene } from '../components/visuals/CivicLensScene';

const formatNumber = (value = 0) => new Intl.NumberFormat('en-IN').format(value);

export const LandingPage: React.FC = () => {
  const { t } = useI18n();
  const { data: summary } = useQuery({ queryKey: ['public-platform'], queryFn: publicService.getPlatformSummary, staleTime: 60_000 });
  const { data: departments = [] } = useQuery({ queryKey: ['departments'], queryFn: departmentService.getDepartments, staleTime: 300_000 });
  const stats = [
    { label: t('issues'), value: formatNumber(summary?.total_complaints), icon: Clipboard },
    { label: t('resolvedFixedIssues'), value: formatNumber(summary?.resolved_complaints), icon: CheckCircle2 },
    { label: t('departmentsTitle'), value: formatNumber(summary?.active_departments), icon: Building2 },
    { label: t('resolutionRate'), value: `${summary?.resolution_rate ?? 0}%`, icon: UsersRound },
  ];
  return <div className="heritage-home space-y-16 py-5 sm:py-8">
    <section className="heritage-hero overflow-hidden rounded-[2rem] border border-[#dec9ab]">
      <div className="heritage-hero-copy">
        <p className="heritage-eyebrow"><Landmark className="w-4 h-4" /> {t('landingEyebrow')}</p>
        <h1>{t('landingHeroTitle')}</h1>
        <p className="heritage-lede">{t('landingHeroDescription')}</p>
        <div className="flex flex-wrap gap-3 pt-2"><Link to="/report"><Button size="lg" rightIcon={<ArrowRight className="w-4 h-4" />}>{t('raiseIssue')}</Button></Link><Link to="/my-complaints"><Button variant="outline" size="lg">{t('trackComplaint')}</Button></Link></div>
        <p className="mt-5 text-xs text-[#66565f]">{t('livePublicIndicators')}</p>
      </div>
      <div className="heritage-hero-art" role="img" aria-label="CivicLens live civic coordination scene"><img src="/images/civiclens-heritage-hero.png" alt="A warm illustrated civic neighbourhood with Indian heritage architecture" /><CivicLensScene /></div>
    </section>
    <section aria-label="Platform impact" className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-5">{stats.map(({ label, value, icon: Icon }) => <Card key={label} className="heritage-stat p-5"><Icon className="w-5 h-5 text-[#e87924]" /><strong>{value}</strong><span>{label}</span></Card>)}</section>
    <section id="how-it-works" className="heritage-section-grid"><div><p className="heritage-kicker">{t('howItWorks')}</p><h2 className="heritage-section-title">{t('howItWorksTitle')}</h2><p className="heritage-subtitle">{t('howItWorksDescription')}</p></div><div className="grid sm:grid-cols-3 gap-4">{[['01', 'raiseStep', 'raiseStepDescription'], ['02', 'coordinateStep', 'coordinateStepDescription'], ['03', 'verifyStep', 'verifyStepDescription']].map(([number, titleKey, descriptionKey]) => <Card className="heritage-step p-5" key={number}><span>{number}</span><h3>{t(titleKey)}</h3><p>{t(descriptionKey)}</p></Card>)}</div></section>
    <section><div className="flex items-end justify-between gap-4 mb-5"><div><p className="heritage-kicker">{t('publicDirectory')}</p><h2 className="heritage-section-title">{t('departmentsTitle')}</h2></div><MapPinned className="hidden sm:block w-8 h-8 text-[#d9a84e]" /></div><div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">{departments.slice(0, 6).map((department) => <Card key={department.id} hoverable className="heritage-department p-5"><Building2 className="w-5 h-5 text-[#286b50]" /><h3>{department.name}</h3><p>{department.description || t('partnerDepartment')}</p><span>{department.code}</span></Card>)}</div></section>
    <section className="grid lg:grid-cols-2 gap-6"><Card className="heritage-panel p-6 sm:p-8"><p className="heritage-kicker">{t('communityOutcomes')}</p><h2 className="heritage-section-title">{t('recentlyResolved')}</h2>{summary?.recent_resolutions.length ? <div className="mt-5 space-y-3">{summary.recent_resolutions.map((item) => <div className="heritage-resolution" key={item.public_id}><CheckCircle2 className="w-4 h-4 text-[#286b50]" /><div><strong>{item.title}</strong><span>{item.public_id} · {item.category_name}</span></div><time>{new Date(item.updated_at).toLocaleDateString('en-IN')}</time></div>)}</div> : <p className="mt-5 text-sm text-[#66565f]">{t('resolvedCasesEmpty')}</p>}</Card><Card id="accessibility" className="heritage-panel heritage-callout p-6 sm:p-8"><ShieldCheck className="w-8 h-8 text-[#d9a84e]" /><p className="heritage-kicker mt-4">{t('designedForParticipation')}</p><h2 className="heritage-section-title">{t('accessibleAccountable')}</h2><p className="heritage-subtitle">{t('accessibilityDescription')}</p><Link className="inline-block mt-6" to="/register"><Button leftIcon={<Sparkles className="w-4 h-4" />}>{t('joinCivicLens')}</Button></Link></Card></section>
  </div>;
};
