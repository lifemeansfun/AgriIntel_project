# AgriIntel frontend

The React/Vite application provides a five-state historical explorer and a bounded Coimbatore classroom feedback demonstration. It preserves the existing day/night landscape assets and editorial/glass interface.

## Run locally

From the repository root, first complete the backend's documented artifact generation and verification steps. With its API running on port 8000:

```sh
npm --prefix frontend ci
npm --prefix frontend run lint
npm --prefix frontend run test
npm --prefix frontend run build
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173
```

The default API root is `/api`; Vite proxies it to `http://127.0.0.1:8000`. For another backend port or host, set the API root before starting Vite:

```sh
VITE_API_BASE_URL=http://127.0.0.1:8001/api npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
```

The client adds `/v2` to this root. A separately hosted frontend must use an API origin permitted by the backend's CORS configuration. `.env.example` documents the default.

## Demonstration workflow

1. Browse historical locations and compare crop scenarios. All forecasts identify their data year and artifact; modeled money uses 2011-base rupees.
2. Select the Coimbatore classroom scenario. It supplies the scenario's exact state, district and season.
3. Keep the generated participant identity or enter another demo identity. Browser storage remembers this identity; it is not authentication.
4. Compare recommendations and commit a crop. Refresh is required when a quote expires or its ledger revision changes. Viewing recommendations does not reserve acreage.
5. Observe shared commitments and production headroom. Cancel the active commitment to release its original capacity. Another visible browser session checks the shared revision every two seconds and refreshes recommendations when it changes.
6. Start an isolated seeded replay, then step, play or pause it. Static and supply-aware policies share the same constraints; final scenario outcomes are separate from observed farmer income.

Changing the location/season exits feedback mode. Missing financial or yield values stay unavailable. The yield slider interpolates a yield illustration at a fixed central price and cultivation cost; its intermediate positions are not additional calibrated quantiles.

Transport errors on a commitment/cancellation preserve the same request identity and expose a safe retry control. Server conflicts refresh the state and quote. Replay transport errors pause playback and retrieve its saved step.

## Verification

`npm run test` exercises unavailable-value handling, fixed-cost scenario arithmetic and stale-response generation guards with Node's built-in test runner. Lint/build are necessary but do not establish browser correctness. Browser verification must cover two identities, commit/cancel, quote conflicts, replay, all five state selections, mobile/desktop and the visible day/night artwork.

The active application uses one maintained dashboard. Legacy UI components remain in the source tree as historical implementation evidence and are no longer linked from navigation.
