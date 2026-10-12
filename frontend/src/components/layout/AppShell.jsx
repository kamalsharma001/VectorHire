import React from 'react';
import { Header } from './Header';
import { ProgressLine } from './ProgressLine';
import { EvidenceDrawer } from '../evidence/EvidenceDrawer';

export function AppShell({ children }) {
  return (
    <div className="min-h-screen w-screen flex flex-col bg-[#F8FAFC] text-[#0F172A] antialiased selection:bg-[#A5F3FC] selection:text-[#0C4A6E] relative overflow-x-hidden">
      {/* Subtle ambient oceanic AI glow at the top */}
      <div 
        className="pointer-events-none absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(6,182,212,0.12),rgba(3,105,161,0.06),transparent)] -z-10" 
        aria-hidden="true" 
      />

      {/* Top Header with canonical logo, live readiness indicator, and reset session */}
      <Header />

      {/* Persistent 5-stage progress line */}
      <ProgressLine />

      {/* Focused single-stage content view with smooth entrance */}
      <main className="flex-1 overflow-y-auto px-4 py-8 sm:px-6 lg:px-8 relative z-10">
        <div className="w-full motion-safe:animate-fade-in">
          {children}
        </div>
      </main>

      {/* Candidate Deep-Dive Slide-Out Evidence Panel */}
      <EvidenceDrawer />
    </div>
  );
}
