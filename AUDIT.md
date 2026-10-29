# HealthCore frontend performance audit

Measured on October 28, 2026, 9:52 PM EDT, before the corrections in this project. Both frontends were already in this monorepo. The public site is the static files in `uis/healthcore-website`. It has no Next.js app and no `npm run build`, so production for that site is the files themselves, served over HTTP. The backoffice is `uis/backoffice`, measured with `npm run build` and then `npm run start` on port 43123. The backoffice overview was measured with a signed-in session, because `AuthGuard` otherwise replaces that page with the login screen.

Lighthouse 12.8.2 in Chrome. INP is not produced by a cold load, so Total Blocking Time is the lab stand-in. No agent skills were installed. The optional skills in the brief were not needed: the category scores were already at the brief’s targets except the two items below.

## Initial scores

| Page | Mode | Performance | Accessibility | Best Practices | SEO | TTFB | LCP | CLS | TBT |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Public home | Desktop | 100 | 100 | 96 | 100 | 2 ms | 424 ms | 0.001 | 0 ms |
| Public home | Mobile | 100 | 100 | 96 | 100 | 1 ms | 1.52 s | 0.000 | 0 ms |
| Patient enquiry | Desktop | 100 | 100 | 96 | 100 | 0 ms | 419 ms | 0.002 | 0 ms |
| Patient enquiry | Mobile | 100 | 100 | 96 | 100 | 0 ms | 1.52 s | 0.016 | 0 ms |
| Backoffice overview | Desktop | 100 | 100 | 100 | 100 | 5 ms | 257 ms | 0 | 0 ms |
| Backoffice overview | Mobile | 99 | 100 | 100 | 100 | 2 ms | 917 ms | 0 | 98 ms |

Screenshots are in `audit/before/`.

## Root causes

**Public site, Best Practices 96.** The only failing audit was `errors-in-console`. Chrome requested `/favicon.ico` and the static server returned 404. The HTML did not link a favicon, and no icon file existed. Performance stayed at 100. LCP on mobile was 1.52 s, under the 2.5 s mark. CLS was under 0.1. Render-blocking Google Fonts CSS and unminified CSS were listed as diagnostics with zero weight, so they did not lower the Performance score.

**Backoffice, mobile Performance 99.** Total Blocking Time was 98 ms (audit display 100 ms, score 0.98, weight 30). The main-thread time was script evaluation in the Next.js production chunks, about 0.3 s of bootup, not a long task from a page-specific image or layout shift. CLS was 0. Desktop was already 100. TTFB was 2–5 ms.

**Production build, separate from the Lighthouse scores.** `npm run build` failed type-checking in `register-form.tsx` and `profile-form.tsx`. `Field` and `ProfileField` combined an input’s event `onChange` with a custom `onChange` that receives a string. TypeScript 5.9.3 reported eight `TS2345` errors. The forms still ran under `next dev`. This blocked the production server the audit has to use.

**Backoffice font.** `globals.css` set `--font-sans: var(--font-sans)`, a circular reference. The layout loads Geist on `--font-geist-sans`, and `html` applies `font-sans`. The computed font was Times New Roman. The mono line next to it already pointed at `--font-geist-mono`.

## Refactor candidates

**1. Labeled inputs in the backoffice.** `register-form.tsx` defined a local `Field`. `profile-form.tsx` defined a local `ProfileField`. `login-form.tsx` repeated the same label-plus-input markup without a helper. Each one wires a label, an input, and a string `onChange`. The shared unit is one `FormField` used by all three forms. That keeps validation and submit behavior in each form.

**2. Public site header.** `index.html` and `application.html` each contain the same header: logo, primary navigation, and the EN/ES switch. A shared partial would remove that copy. It was not extracted. The public site has no component build, and the brief says not to restructure either frontend.
