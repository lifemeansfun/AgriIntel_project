import React, { useState, useRef, useEffect, Suspense } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { useTexture } from '@react-three/drei';
import * as THREE from 'three';
import FileErrorBoundary from '../common/FileErrorBoundary';
import './DisplacementShaderMaterial'; // Ensure shaderMaterial is registered

// Hoist static vector allocation outside component render loop to prevent GC churn
const IMAGE_RESOLUTION = new THREE.Vector2(1376, 768);

export default function WebGLBackground({ dayTextureUrl, nightTextureUrl, dayDepthUrl, nightDepthUrl, theme }) {
  const [isVisible, setIsVisible] = useState(() => (typeof document !== 'undefined' ? !document.hidden : true));

  // Pause render loop when browser tab or window is inactive to conserve battery and thermals
  useEffect(() => {
    const handleVisibilityChange = () => {
      setIsVisible(!document.hidden);
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  return (
    <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none">
      <FileErrorBoundary fileName="WebGLBackground.jsx - Canvas Root">
        <Canvas 
          camera={{ position: [0, 0, 1], near: 0.1, far: 100 }}
          dpr={1}
          frameloop={isVisible ? 'always' : 'never'}
          gl={{ antialias: false, powerPreference: 'low-power' }}
        >
          {/* Suspense handles async texture loading cleanly */}
          <Suspense fallback={null}>
            <Scene 
              dayTextureUrl={dayTextureUrl}
              nightTextureUrl={nightTextureUrl}
              dayDepthUrl={dayDepthUrl}
              nightDepthUrl={nightDepthUrl}
              theme={theme}
            />
          </Suspense>
        </Canvas>
      </FileErrorBoundary>
    </div>
  );
}

function Scene({ dayTextureUrl, nightTextureUrl, dayDepthUrl, nightDepthUrl, theme }) {
  // Pass onLoad callback to configure colorSpace at construction time (React Compiler compliant)
  const [day, night, dayDepth, nightDepth] = useTexture(
    [dayTextureUrl, nightTextureUrl, dayDepthUrl, nightDepthUrl],
    (loadedTextures) => {
      const [tDay, tNight, tDayDepth, tNightDepth] = loadedTextures;
      if (tDay) tDay.colorSpace = THREE.SRGBColorSpace;
      if (tNight) tNight.colorSpace = THREE.SRGBColorSpace;
      if (tDayDepth) tDayDepth.colorSpace = THREE.NoColorSpace;
      if (tNightDepth) tNightDepth.colorSpace = THREE.NoColorSpace;
    }
  );

  const materialRef = useRef(null);
  const { viewport, size } = useThree();

  const themeProgressRef = useRef(theme === 'night' ? 1.0 : 0.0);
  const targetThemeProgress = theme === 'night' ? 1.0 : 0.0;

  const targetMouse = useRef(new THREE.Vector2(0, 0));
  const currentMouse = useRef(new THREE.Vector2(0, 0));

  // Update screen resolution uniform ONLY when viewport size changes, avoiding 60-120 uniform writes/sec
  useEffect(() => {
    if (materialRef.current?.uScreenRes) {
      materialRef.current.uScreenRes.set(size.width, size.height);
    }
  }, [size.width, size.height]);

  // Global mouse tracking across the window so parallax functions smoothly even with pointer-events-none on canvas
  useEffect(() => {
    const handlePointerMove = (e) => {
      const x = (e.clientX / window.innerWidth) * 2 - 1;
      const y = -(e.clientY / window.innerHeight) * 2 + 1;
      targetMouse.current.set(x, y);
    };

    window.addEventListener('pointermove', handlePointerMove, { passive: true });
    return () => window.removeEventListener('pointermove', handlePointerMove);
  }, []);

  useFrame((state, delta) => {
    if (!materialRef.current) return;

    // Smooth critically damped spring lerp for theme transition (~0.6s smooth organic cross-fade)
    themeProgressRef.current = THREE.MathUtils.damp(
      themeProgressRef.current,
      targetThemeProgress,
      4.5,
      delta
    );
    materialRef.current.uThemeProgress = themeProgressRef.current;

    // Organic lerp for smooth physics-based mouse sway
    currentMouse.current.lerp(targetMouse.current, 4.0 * delta);
    materialRef.current.uMouse = currentMouse.current;
    
    // Use R3F's managed clock to prevent THREE.Clock deprecation warnings
    materialRef.current.uTime = state.clock.elapsedTime;
  });

  return (
    <mesh position={[0, 0, 0]} scale={[viewport.width, viewport.height, 1]}>
      <planeGeometry args={[1, 1]} />
      <displacementMaterialImpl 
        ref={materialRef}
        uDayTexture={day}
        uNightTexture={night}
        uDayDepth={dayDepth}
        uNightDepth={nightDepth}
        uImageRes={IMAGE_RESOLUTION}
      />
    </mesh>
  );
}
