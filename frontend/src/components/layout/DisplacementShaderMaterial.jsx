import * as THREE from 'three';
import { extend } from '@react-three/fiber';
import { shaderMaterial } from '@react-three/drei';

const DisplacementMaterialImpl = shaderMaterial(
  // Initial Uniforms
  {
    uDayTexture: new THREE.Texture(),
    uNightTexture: new THREE.Texture(),
    uDayDepth: new THREE.Texture(),
    uNightDepth: new THREE.Texture(),
    uThemeProgress: 0.0,
    uMouse: new THREE.Vector2(0, 0),
    uTime: 0,
    uImageRes: new THREE.Vector2(1376, 768),
    uScreenRes: new THREE.Vector2(1920, 1080)
  },
  // Vertex Shader
  `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  // Fragment Shader
  `
    precision mediump float;

    uniform sampler2D uDayTexture;
    uniform sampler2D uNightTexture;
    uniform sampler2D uDayDepth;
    uniform sampler2D uNightDepth;
    uniform float uThemeProgress;
    uniform vec2 uMouse;
    uniform float uTime;
    uniform vec2 uImageRes;
    uniform vec2 uScreenRes;
    
    varying vec2 vUv;

    void main() {
      // SAFEGUARD: prevent division by zero by enforcing a min value of 1.0
      vec2 safeScreen = max(uScreenRes, vec2(1.0));
      vec2 safeImage = max(uImageRes, vec2(1.0));

      // CSS object-fit: cover aspect ratio calculation
      vec2 ratio = vec2(
        min((safeScreen.x / safeScreen.y) / (safeImage.x / safeImage.y), 1.0),
        min((safeScreen.y / safeScreen.x) / (safeImage.y / safeImage.x), 1.0)
      );
      
      // Inset UV by ~8% to provide a bleed buffer so parallax & wind never cause edge border clamping
      vec2 centeredUv = (vUv - 0.5) * 0.92;
      vec2 uv = vec2(
        centeredUv.x * ratio.x + 0.5,
        centeredUv.y * ratio.y + 0.5
      );

      // Optimize texture sampling: during static Day or Night, sample only active textures
      float depth;
      if (uThemeProgress < 0.01) {
        depth = texture2D(uDayDepth, uv).r;
      } else if (uThemeProgress > 0.99) {
        depth = texture2D(uNightDepth, uv).r;
      } else {
        float dayDepthVal = texture2D(uDayDepth, uv).r;
        float nightDepthVal = texture2D(uNightDepth, uv).r;
        depth = mix(dayDepthVal, nightDepthVal, uThemeProgress);
      }

      // Parallax based on uMouse and depth (brighter = closer = moves more)
      vec2 parallaxOffset = uMouse * depth * 0.025;
      
      // Continuous organic wind sway on foreground grass (vectorized fast phase evaluation)
      float windStrength = smoothstep(0.35, 1.0, depth) * 0.006;
      vec2 windPhase = vec2(uTime * 1.5 + uv.y * 12.0, uTime * 1.2 + uv.x * 10.0);
      vec2 windOffset = vec2(sin(windPhase.x), cos(windPhase.y) * 0.5) * windStrength;

      vec2 displacedUv = clamp(uv + parallaxOffset + windOffset, 0.0, 1.0);
      
      // Smoothly cross-fade day and night textures based on theme progress
      if (uThemeProgress < 0.01) {
        gl_FragColor = texture2D(uDayTexture, displacedUv);
      } else if (uThemeProgress > 0.99) {
        gl_FragColor = texture2D(uNightTexture, displacedUv);
      } else {
        vec4 dayColor = texture2D(uDayTexture, displacedUv);
        vec4 nightColor = texture2D(uNightTexture, displacedUv);
        gl_FragColor = mix(dayColor, nightColor, uThemeProgress);
      }
    }
  `
);

// Register with R3F
extend({ DisplacementMaterialImpl });

export { DisplacementMaterialImpl };
