# HealthCore frontend performance report

Second Lighthouse pass on October 28, 2026, 10:55 PM EDT. Same URLs and the same production setup as `AUDIT.md`: static files for `uis/healthcore-website`, and `npm run build` then `npm run start` for `uis/backoffice`. The backoffice overview was signed in, same as the first pass. Screenshots are in `audit/after/`.

## Corrections

**Public favicon.** The Best Practices score of 96 was the browser console error for `GET /favicon.ico` returning 404. `uis/healthcore-website/favicon.ico` is now the site icon, and both pages link it. No other public-site markup was changed. The stray `}` in `index.html` was left in place: the page still applied its stylesheet and kept valid JSON-LD, and that text was not the console error.

**Backoffice font.** `--font-sans` in `uis/backoffice/src/app/globals.css` pointed at itself, so the loaded Geist face was unused and the computed font was Times New Roman. It now points at `--font-geist-sans`, which is the variable the layout already sets. After the production rebuild the login page computed `Geist, "Geist Fallback"`.

**Shared form field.** `Field` in the registration form and `ProfileField` in the profile form were the same labeled input, and the sign-in form repeated that markup. They are now `FormField` in `uis/backoffice/src/components/form-field.tsx`, used by login, registration, and profile. The custom `onChange` receives a string and is no longer combined with the input’s event handler, which is what made `npm run build` fail type-checking. Submit, validation, and the read-only email on the profile page are unchanged. `npx tsc --noEmit` exits 0, and the existing 10 backoffice tests pass.

The public header is still duplicated in the two HTML files. Extracting it would have added a build step the site does not have.

No agent skills were installed.

## Before and after

| Page | Mode | Before | After |
| --- | --- | --- | --- |
| Public home | Desktop | 100 / 100 / 96 / 100 | 100 / 100 / 100 / 100 |
| Public home | Mobile | 100 / 100 / 96 / 100 | 100 / 100 / 100 / 100 |
| Patient enquiry | Desktop | 100 / 100 / 96 / 100 | 100 / 100 / 100 / 100 |
| Patient enquiry | Mobile | 100 / 100 / 96 / 100 | 100 / 100 / 100 / 100 |
| Backoffice overview | Desktop | 100 / 100 / 100 / 100 | 100 / 100 / 100 / 100 |
| Backoffice overview | Mobile | 99 / 100 / 100 / 100 | 100 / 100 / 100 / 100 |

Scores are Performance, Accessibility, Best Practices, and SEO.

On the public site, `errors-in-console` went from failing to passing on all four runs. Performance was already 100. Mobile LCP stayed about 1.52 s. CLS stayed under 0.02.

On the backoffice, desktop stayed at 100. Mobile Performance went from 99 to 100. Total Blocking Time on that run went from 100 ms to 60 ms. The dashboard does not render the form field. The production change on that page is the font variable.

## Biggest impact

The clearest score change is Best Practices on the public site, 96 to 100, from removing the favicon 404. The backoffice’s category change is mobile Performance, 99 to 100.
