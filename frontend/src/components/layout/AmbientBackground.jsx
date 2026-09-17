import React from 'react';
import { useTheme } from '../../context/useTheme';
import WebGLBackground from './WebGLBackground';
import FileErrorBoundary from '../common/FileErrorBoundary';

export default function AmbientBackground({ children }) {
  const { darkMode } = useTheme();

  return (
    <div className={`min-h-screen relative overflow-hidden transition-colors duration-700 ${darkMode ? 'bg-slate-950' : 'bg-emerald-900/10'}`}>
      {/* 
        WebGL Displacement Parallax Background
        Suspense is now correctly managed INSIDE the WebGLBackground Canvas.
      */}
      <FileErrorBoundary fileName="AmbientBackground.jsx">
        <WebGLBackground
          dayTextureUrl="/bg-day.webp"
          nightTextureUrl="/bg-night.webp"
          dayDepthUrl="/depth-day.webp"
          nightDepthUrl="/depth-night.webp"
          theme={darkMode ? 'night' : 'day'}
        />
      </FileErrorBoundary>

      {/* Floating ambient orbs for extra depth */}
      <div
        className="orb orb-green fixed"
        style={{
          top: '-100px',
          left: '-100px',
          opacity: darkMode ? 0.25 : 0.12
        }}
      />
      <div
        className="orb orb-amber fixed"
        style={{
          bottom: '-50px',
          right: '10%',
          animationDelay: '-4s',
          opacity: darkMode ? 0.2 : 0.10
        }}
      />

      {/* Main Content Container */}
      <div className="relative z-10 min-h-screen flex flex-col px-4 py-6 max-w-7xl mx-auto">
        {children}
      </div>
    </div>
  );
}
