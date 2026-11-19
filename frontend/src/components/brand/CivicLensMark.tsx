import React from 'react';

/** Unique CivicLens mark: lotus + civic lens aperture in the brand palette. */
export const CivicLensMark: React.FC<{ compact?: boolean }> = ({ compact = false }) => (
  <div className="flex items-center gap-2.5">
    <span className="brand-mark" aria-hidden="true">
      <svg viewBox="0 0 48 48" className="h-9 w-9" role="img">
        <defs>
          <linearGradient id="cl-petal" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#E87924" />
            <stop offset="55%" stopColor="#4B205B" />
            <stop offset="100%" stopColor="#286B50" />
          </linearGradient>
          <radialGradient id="cl-core" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#F4E8D5" />
            <stop offset="100%" stopColor="#D9A84E" />
          </radialGradient>
        </defs>
        <circle cx="24" cy="24" r="22" fill="#4B205B" opacity="0.12" />
        <path
          d="M24 6c2.8 6.2 3.4 11.2 0 18-3.4-6.8-2.8-11.8 0-18Z"
          fill="url(#cl-petal)"
        />
        <path
          d="M24 6c2.8 6.2 3.4 11.2 0 18-3.4-6.8-2.8-11.8 0-18Z"
          fill="url(#cl-petal)"
          transform="rotate(60 24 24)"
        />
        <path
          d="M24 6c2.8 6.2 3.4 11.2 0 18-3.4-6.8-2.8-11.8 0-18Z"
          fill="url(#cl-petal)"
          transform="rotate(120 24 24)"
        />
        <circle cx="24" cy="24" r="7.5" fill="url(#cl-core)" stroke="#29232B" strokeWidth="1.2" />
        <circle cx="24" cy="24" r="3.2" fill="#4B205B" />
        <circle cx="24" cy="24" r="1.2" fill="#F4E8D5" />
      </svg>
    </span>
    {!compact && (
      <span>
        <span className="brand-name">CivicLens</span>
        <span className="brand-tagline">Your Voice. Our Collective Progress.</span>
      </span>
    )}
  </div>
);
