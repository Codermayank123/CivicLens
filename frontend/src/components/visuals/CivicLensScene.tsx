import React from 'react';
import { Building2, CheckCircle2, MapPin, Sparkles } from 'lucide-react';

/** Lightweight CSS 3D civic scene. It is decorative, responsive, and has no runtime 3D dependency. */
export const CivicLensScene: React.FC = () => (
  <div className="civic-scene" aria-hidden="true">
    <div className="civic-scene-glow civic-scene-glow-one" />
    <div className="civic-scene-glow civic-scene-glow-two" />
    <div className="civic-scene-grid" />
    <div className="civic-scene-orbit civic-scene-orbit-one" />
    <div className="civic-scene-orbit civic-scene-orbit-two" />
    <div className="civic-scene-card civic-scene-card-main">
      <div className="civic-scene-card-topline"><span className="civic-scene-status"><CheckCircle2 /> Live</span><Sparkles /></div>
      <div className="civic-scene-map"><MapPin /><span /><span /><span /></div>
      <strong>One city. Clear action.</strong>
      <small>Every report stays visible from submission to resolution.</small>
    </div>
    <div className="civic-scene-card civic-scene-card-float civic-scene-card-float-one"><Building2 /><span><b>24 departments</b><small>working together</small></span></div>
    <div className="civic-scene-card civic-scene-card-float civic-scene-card-float-two"><CheckCircle2 /><span><b>Resolution trail</b><small>updated in real time</small></span></div>
    <span className="civic-scene-particle civic-scene-particle-one" />
    <span className="civic-scene-particle civic-scene-particle-two" />
    <span className="civic-scene-particle civic-scene-particle-three" />
  </div>
);
