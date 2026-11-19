import React from 'react';

export const Footer: React.FC = () => (
  <footer className="border-t border-[#dcc6a7] bg-[#f4e8d5] py-6 px-4 text-center text-xs text-[#66565f]">
    <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
      <div>CivicLens © 2026. Your Voice. Our Collective Progress.</div>
      <div className="flex items-center gap-6"><a href="/docs" className="hover:text-[#4b205b]">API Documentation</a><a href="/#how-it-works" className="hover:text-[#4b205b]">How it works</a><a href="/#accessibility" className="hover:text-[#4b205b]">Accessibility</a></div>
    </div>
  </footer>
);
