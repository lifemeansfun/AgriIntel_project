import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

export default function SplashScreen({ onComplete }) {
  const [isZooming, setIsZooming] = useState(false);

  useEffect(() => {
    // Stage 1: Emergence (0s - 0.52s) [1.5x scale]
    // Stage 2: Readability hold (0.52s - 1.125s) [1.5x scale]
    // Stage 3: Buttery smooth exponential warp zoom at 1.125s (1125ms)
    const zoomTimer = setTimeout(() => {
      setIsZooming(true);
    }, 1125);

    // Stage 4: Clean unmount at 2.1s (2100ms) [1.5x scale]
    const completeTimer = setTimeout(() => {
      if (onComplete) onComplete();
    }, 2100);

    return () => {
      clearTimeout(zoomTimer);
      clearTimeout(completeTimer);
    };
  }, [onComplete]);

  const handleSkip = () => {
    if (onComplete) onComplete();
  };

  return (
    <motion.div
      initial={{ opacity: 1 }}
      animate={{ opacity: isZooming ? 0 : 1 }}
      exit={{ opacity: 0 }}
      transition={{
        duration: isZooming ? 0.98 : 0.38,
        ease: [0.45, 0, 0.15, 1],
      }}
      onClick={handleSkip}
      className={`fixed inset-0 z-50 flex flex-col items-center justify-center bg-slate-950 overflow-hidden cursor-pointer select-none ${
        isZooming ? 'pointer-events-none' : ''
      }`}
    >
      {/* Background Ambient Glow Orbs — pure gradient falloff without expensive CSS blur filters */}
      <div 
        className="absolute w-[650px] h-[650px] rounded-full pointer-events-none"
        style={{
          background: 'radial-gradient(circle, rgba(16, 185, 129, 0.22) 0%, rgba(6, 78, 59, 0.08) 48%, transparent 72%)',
        }} 
      />
      <div 
        className="absolute w-[500px] h-[500px] rounded-full pointer-events-none"
        style={{
          background: 'radial-gradient(circle, rgba(217, 119, 6, 0.14) 0%, rgba(180, 83, 9, 0.04) 50%, transparent 70%)',
          transform: 'translate3d(120px, 90px, 0)',
        }} 
      />

      {/* Exponential Zoom Container — 100% GPU compositor driven */}
      <motion.div
        initial={{ scale: 0.92, opacity: 0 }}
        animate={
          isZooming
            ? {
                scale: 14,
                opacity: 0,
                transition: {
                  duration: 0.98, // 1.5x scaled duration
                  ease: [0.45, 0, 0.15, 1], // Smooth exponential acceleration curve
                },
              }
            : {
                scale: 1,
                opacity: 1,
                transition: {
                  duration: 0.52, // 1.5x scaled emergence
                  ease: 'easeOut',
                },
              }
        }
        style={{
          willChange: 'transform, opacity',
          transform: 'translate3d(0, 0, 0)',
          backfaceVisibility: 'hidden',
          transformOrigin: 'center center',
        }}
        className="relative z-10 flex flex-col items-center justify-center text-center px-4"
      >
        {/* Massive Project Name */}
        <h1 className="text-6xl sm:text-8xl md:text-9xl lg:text-[10.5rem] font-black tracking-tight leading-none bg-gradient-to-r from-emerald-400 via-teal-200 to-amber-300 bg-clip-text text-transparent drop-shadow-2xl">
          AgriIntel
        </h1>

        {/* Elegant Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={
            isZooming
              ? {
                  opacity: 0,
                  transition: { duration: 0.3, ease: 'easeIn' },
                }
              : {
                  opacity: 1,
                  y: 0,
                  transition: { delay: 0.22, duration: 0.45, ease: 'easeOut' },
                }
          }
          className="mt-4 text-xs sm:text-sm md:text-base font-semibold tracking-[0.25em] uppercase text-emerald-300/80"
        >
          Risk-Adjusted Agricultural Intelligence
        </motion.p>
      </motion.div>

      {/* Subtle Skip Hint */}
      <div className="absolute bottom-8 text-[11px] font-medium tracking-widest uppercase text-slate-500/60 pointer-events-none">
        Click anywhere to skip
      </div>
    </motion.div>
  );
}
