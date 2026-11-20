# Promptly frontend

React 19 and Vite power the conversation workspace, authentication forms, model controls, and voice recorder. Start with the [root README](../../../README.md) for full setup, screenshots, architecture, and deployment.

```sh
npm ci
npm run dev
npm run lint -- --max-warnings 0
npm test
npm run build
```

Set `VITE_API_BASE_URL` in `.env.local` for an API on a separate origin. Local development defaults to `http://localhost:5000`; production defaults to the same origin. All Vite variables are public.

`AuthContext.jsx` owns the provider, while `authContext.js` exposes the context and hook. `useModelParameters.js` manages per-model preferences; `modelParameters.js` filters capabilities using the shared JSON definition. `aiResponse.js` normalizes successful responses and upstream errors. Components retain the existing architecture and call the Flask API through `api.js`.
