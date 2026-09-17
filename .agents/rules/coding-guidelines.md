---
trigger: always_on
---

Academic and research integrity must always be maintained, avoid hard coding or shortcuts.

incorporate defensive coding strategies.

anticipate challenges when implementing the next phase of module of a project and prepare accordingly.

Make sure to identify the challenges that all succeeding modules will face when implementing the current module and mitigate that.

verify and validate each module or phase of a project beforeing moving on the the next module or phase.

Ask for external help whenever necessary.

Robust exception handling to easily identify bugs.

Modular programming to easily identify faults in case of any issues.

Be honest and unbiased.

## Frontend Development Rules

Before writing any React/JSX component to disk, perform a self-audit:
  1. Every JSX symbol (<ComponentName />, icon, hook) MUST have a corresponding import in the same file.
  2. Every import statement MUST be used. Remove all dead/unused imports before finalising a file.
  3. Never embed LaTeX or Markdown notation (e.g., $q_{{50}}$) inside JSX string literals; JSX treats {{ as an object expression and will throw a parse error.

## CSS / Tailwind Rules

Before referencing a CSS utility class in JSX, verify it actually exists:
  1. After writing index.css, list every custom class name defined there.
  2. Cross-check each class name used in JSX exactly matches a class defined in CSS (no typos, no version-mismatch assumptions).
  3. When using Tailwind v4, do NOT assume @theme custom tokens generate utility classes (e.g., text-brand-primary). Use standard Tailwind utilities or plain CSS classes instead.

## Frontend Verification Rules

HTTP 200 from a dev server is NOT sufficient verification that the UI is working:
  1. Always inspect the dev server's stderr/log for [PARSE_ERROR], [Unhandled error], or [console.warn] lines before declaring verification passed.
  2. A browser subagent screenshot or explicit DOM check is required to confirm the UI actually renders.
  3. The master verification check must happen BEFORE the backend and frontend are started as daemons, not after.

## UI Asset Rules

Do NOT use generate_image for website background images unless the user explicitly asks you to generate one:
  1. First ask the user if they want to provide their own image asset, and give them instructions on where to place it (e.g., frontend/public/bg.jpg).
  2. If no asset is provided, use a CSS gradient fallback as the background.
  3. Generated AI art is generally not suitable for professional UI backgrounds and should only be used as a placeholder of last resort.

## 3D WebGL & Canvas Spatial Invariant Rules

In 3D scenes (Three.js, React Three Fiber), never decouple geometry dimensions from camera optics:
  1. Never hardcode arbitrary large dimensions (e.g., <planeGeometry args={[100, 100]} />) for full-screen backgrounds or camera-facing planes.
  2. Always bind mesh scale dynamically to the camera's visible frustum viewport:
     `const { viewport } = useThree();`
     `<mesh scale={[viewport.width, viewport.height, 1]}><planeGeometry args={[1, 1]} /></mesh>`
  3. Shaders sampling textures must enforce UV bleed margins (e.g., inset UV coordinates by 8%) to prevent edge clamping artifacts during mouse parallax or vertex displacements.

## Cross-Cutting DOM Layering & Event Propagation Rules

When layering interactive DOM elements (dashboards, forms, cards) over full-screen canvas/graphics backgrounds:
  1. Never assume canvas-bound pointer listeners will work if the canvas container has `pointer-events-none`.
  2. For ambient visual effects, parallax, or mouse tracking that sit beneath an interactive UI overlay, always bind pointer listeners globally at the `window` level with passive listeners:
     `window.addEventListener('pointermove', handlePointerMove, { passive: true });`
  3. Cleanly unbind all global event listeners in the component cleanup return function to prevent memory leaks across route changes or fast reloads.

## Perceptual & Visual Quality Invariant Rules

Green error boundaries and HTTP 200 do NOT prove visual correctness:
  1. Exception boundaries (FileErrorBoundary, try/catch) only catch JavaScript runtime throws. They cannot detect semantic visual bugs (e.g., looking at an empty cloud, black screen, or z-index occlusion).
  2. Verification of canvas/graphics components MUST include an explicit visual inspection (browser subagent screenshot or pixel variance check) confirming that the expected visual assets are visible, properly framed, and not stuck in a flat monochrome color.
  3. WebGL Canvas lifecycles must be guarded against rapid remount context collisions by ensuring proper resource disposal and singleton canvas wrappers.