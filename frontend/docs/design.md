# Design System v2: Numerical Methods Solver ("Modern Scholar")

A modern, polished, confident learning tool. Friendly on the surface, rigorous underneath.
Think: Linear's precision, Stripe's typography, Desmos's graph-first workspace, Notion's calm, Raycast's speed.

> AI assistants and contributors: read this whole file before touching any UI. Never hard-code colors,
> spacing, radii, shadows or z-index; use tokens. After every UI change, take screenshots and run the
> checklist in section 17. "It looks fine" is not evidence; screenshots and measurements are.

---

## 1. Vision and personality

**Who it is for:** engineering students solving homework, revising for exams and writing lab reports;
teachers checking answers.

**Personality:** precise, friendly, confident, never childish, never cluttered.
Keywords: *clear, fast, trustworthy, teachable, polished.*

**Visual direction:** clean modern product UI.
- Soft depth (subtle layered surfaces and gentle shadows) instead of fully flat.
- One brand gradient used sparingly as a signature, never as wallpaper.
- Color-coded chapters for instant wayfinding.
- Generous whitespace and a strong typographic hierarchy.
- Data zones (tables, steps, graphs) stay calm and high-contrast.

---

## 2. Experience principles (UX)

1. **Answer in 10 seconds.** From landing to a solved example in two clicks, with no sign-up.
2. **Show the work.** Every answer comes with exam-style steps, a table and a graph. The steps are the product.
3. **Never a dead end.** Every empty state, error and failure explains what happened and offers a next action.
4. **Teach while solving.** Theory, formulas, pseudocode and "common mistakes" sit one tab away.
5. **Forgiving input.** Accept pasted symbols (x², √, ×, π), `x =` prefixes, keypad entry and live validation.
6. **Feels instant.** Interactions respond in under 100 ms; use skeletons, never blank screens or layout jumps.
7. **Consistent.** Same patterns everywhere: one layout for all 51 methods.
8. **Respect the student's time.** Defaults that work, examples one click away, results copyable and exportable.

---

## 3. Information architecture

```
Home
 ├─ Chapters (6)  ─ each lists its methods
 │    └─ Method page (solver)  ─ tabs: Answer, Steps, Table, Graph, Theory, Pseudocode, Code
 ├─ Compare methods (Chapter 1 tool, and per-chapter compare toggles)
 ├─ Library: Favorites, Recent, History (local)
 ├─ Help: how to enter expressions, keyboard shortcuts, FAQ
 └─ About: syllabus coverage, credits
```

Navigation model: sidebar (chapters and methods), header (search with Ctrl+K, theme, focus mode, help),
breadcrumbs on method pages (`Home / Chapter 2 / Gauss-Seidel`), previous/next method links at the bottom
of each method page, "Related methods" cards.

URLs are stable and shareable: `/chapters/2`, `/methods/gauss_seidel?inputs=...` (inputs encoded in the query).

---

## 4. Key user journeys

| Journey | Path | Must feel like |
|---|---|---|
| Solve homework | Search "simpson" -> method page -> Load example or enter data -> Solve -> read Steps -> Copy/Export | Fast, no confusion |
| Exam revision | Chapter page -> method -> Exam mode (hide answer) -> attempt -> reveal | Focused, like a worksheet |
| Lab report | Solve -> Export PDF (working principle, pseudocode, code, test case, graph) | Complete, printable |
| Compare methods | Chapter 1 Compare -> tick methods -> table + convergence plot | Insightful |
| Teacher check | Paste a problem -> Solve -> share link | One link, same result |

First visit: a 3-step skippable tour (1: pick a chapter, 2: enter or load an example, 3: read steps and export).

---

## 5. Visual language

### 5.1 Color

**Brand:** indigo to violet. Gradient `--brand-gradient: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)`.
Allowed on: logo mark, primary CTA on landing, hero highlight word (at most one), progress fills, selected-tab
indicator on landing. Not allowed on: tool-page backgrounds, table headers, large panels, body text.

**Themes** (all driven by tokens on `:root[data-theme]`; components never branch on theme):

| Token | Light | Paper | Dark |
|---|---|---|---|
| `--bg` | #F6F7FB | #FAF7F0 | #0A0C14 |
| `--surface` | #FFFFFF | #FFFDF8 | #10131D |
| `--surface-2` | #F1F3F9 | #F3EEE2 | #161A26 |
| `--surface-3` | #E8EBF4 | #EAE3D3 | #1D2230 |
| `--border` | #E2E6F0 | #E0D8C6 | #262C3B |
| `--border-strong` | #CDD3E3 | #CFC5AE | #343B4F |
| `--text` | #0F1424 | #1F1A14 | #E8EAF2 |
| `--text-muted` | #475467 | #5E5648 | #A0A8BC |
| `--text-subtle` | #667085 | #7A705E | #7C869D |
| `--accent` | #4F46E5 | #2B4C9B | #8B8CF8 |
| `--accent-hover` | #4338CA | #223D7E | #A5A6FA |
| `--accent-soft` | #EEF0FF | #E8EDF9 | #1E2142 |
| `--success` | #15803D | #166534 | #4ADE80 |
| `--warning` | #B45309 | #92400E | #FBBF24 |
| `--error` | #B91C1C | #991B1B | #F87171 |
| `--info` | #1D4ED8 | #1E40AF | #60A5FA |

Every semantic color has a `-soft` background tint (about 10% in light, 16% in dark) for chips and alerts.
`--text-subtle` is for captions and placeholders only, never for essential information.

**Chapter colors** (wayfinding: icon tile, sidebar dot, chapter card accent, method chip stripe). Each has a
`-soft` tint:

| Chapter | Name | Color |
|---|---|---|
| 1 | Non-linear Equations | Indigo #4F46E5 |
| 2 | Linear Systems | Sky #0284C7 |
| 3 | Interpolation | Emerald #059669 |
| 4 | Differentiation and Integration | Amber #D97706 |
| 5 | Ordinary Differential Equations | Rose #E11D48 |
| 6 | Partial Differential Equations | Violet #7C3AED |

Use chapter colors for small accents only (icon tiles, dots, thin top borders). Never as large fills.

**Rules:** all text/background pairs meet WCAG AA (4.5:1 body, 3:1 large text and UI). Color never carries
meaning alone (add an icon or text). Dark theme: lighter borders and a faint top inner highlight create
elevation; no heavy shadows.

### 5.2 Surfaces and elevation

| Level | Use | Light | Dark |
|---|---|---|---|
| e0 | Page background, table rows | `--bg` | `--bg` |
| e1 | Cards, panels | surface + 1 px border + `0 1px 2px rgba(16,24,40,.04)` | surface + 1 px border |
| e2 | Hover on interactive cards, sticky toolbars | `0 4px 12px rgba(16,24,40,.08)` | border-strong + inner highlight |
| e3 | Popovers, palette, flyout, toasts | `0 12px 32px rgba(16,24,40,.14)` | `0 12px 32px rgba(0,0,0,.5)` + border |

### 5.3 Radius and spacing

- Radius: 8 (controls), 12 (cards, panels, rail buttons), 16 (hero blocks, large panels), 999 (chips).
- Spacing scale (4 px base): 4, 8, 12, 16, 24, 32, 48, 64, 96. Section spacing on landing 64 to 96; between
  cards 16 to 24; inside cards 16 to 24 (12 in compact density).

### 5.4 Typography

- **Inter** variable (UI), **JetBrains Mono** (numbers, code). Self-hosted, subset, `font-display: swap`.
- Serif (Source Serif 4) only in Paper theme for headings, Theory and narration.
- `font-variant-numeric: tabular-nums` on every numeric element.

| Role | Size / line height | Weight | Tracking |
|---|---|---|---|
| Display (landing hero) | 56 / 60 (40 / 44 mobile) | 700 | -0.03em |
| H1 | 32 / 38 | 700 | -0.02em |
| H2 | 24 / 30 | 650 | -0.015em |
| H3 | 18 / 26 | 600 | -0.01em |
| Body | 14 (15 comfortable) / 22 | 400 | 0 |
| Secondary | 13 / 20 | 400 | 0 |
| Caption / label | 12 / 16 | 500 | 0.02em, uppercase only for section labels |
| Result figure | 32 / 38 mono | 600 | 0 |

Prose max width 70ch. Never wrap one word per line. Long expressions scroll inside their own container.

### 5.5 Iconography and illustration

- One outline icon set (Lucide), 20 px, stroke 1.75, `currentColor`. No emoji, no text glyphs.
- Chapter icons in a 40 px rounded-xl tile tinted with the chapter's `-soft` color and icon in the chapter color.
- Illustrations: simple line-and-shape diagrams made from tokens (a curve with a root marker, a matrix grid,
  a spline through points, an area under a curve, a slope field, a heat map). Used on the landing page,
  chapter headers and empty states. Never stock photos.

### 5.6 Motion

- Durations: 120 ms (hover, focus), 180 ms (panels, tabs, popovers), 240 ms (page-level fades). Easing
  `cubic-bezier(0.2, 0, 0, 1)`.
- Allowed: hover lift (translateY(-1px) plus e2) on clickable cards, tab indicator slide, panel slide, result
  fade-in, skeleton shimmer, toast slide, graph iteration player.
- Not allowed: bouncing, parallax, looping decorative animation, animated gradients.
- `prefers-reduced-motion` removes all non-essential motion.

---

## 6. Layout and responsive

- Header 56 px: flat surface, 1 px bottom border, subtle backdrop blur allowed only when scrolled.
- Hamburger (40x40) and all rail icons are centered at **x = 28 px** (+/- 0.5 px). Header left cell is 56 px wide.
- Sidebar: Expanded (240 to 420, default 280), Rail (56), Hidden (0 plus Menu tab). One `{mode, width}`
  state; hidden content is unmounted or inert. Ctrl/Cmd+B cycles; F toggles Focus mode (never while typing).
- Workspace: fluid with 24 px gutters up to 1760 px on solver pages; landing content up to 1200 px.

| Breakpoint | Behavior |
|---|---|
| >= 1280 | Two-pane solver, sidebar rail or expanded |
| 1024 to 1279 | Two-pane solver, sidebar rail by default |
| 768 to 1023 | Single column; inputs collapse into an accordion above results; drawer navigation |
| < 768 | Single column; sticky bottom action bar (Solve, Examples, Export); full-width tabs scroll horizontally; tables scroll inside containers |

Touch targets at least 40 px. No page-level horizontal scroll at any width. Plot height adapts (min 280 px mobile).

---

## 7. Pages

### 7.1 Landing page (the expressive page)
1. **Hero:** headline ("Numerical methods, solved step by step."), one-line subtitle, primary CTA (Explore
   chapters, brand gradient) and secondary (Try Bisection). To the right, a **live interactive demo card**
   (real solve of an example with a small converging plot and stat chips), not a static mock. Stats row:
   methods ready, chapters, exports.
2. **How it works:** three steps with icons (Enter your problem, See every step, Export your report).
3. **Chapter grid:** six tiles in chapter colors (icon tile, name, "N methods", progress bar, top 3 methods as
   links). Hover lift.
4. **Why it is different:** four feature blocks with small illustrations (exam-style steps, interactive
   graphs and iteration player, compare methods, PDF/CSV lab reports).
5. **Syllabus coverage:** compact table of ENSH 252 topics with Available / Coming soon chips.
6. **Footer:** links, shortcuts, about, version.
Keep animation minimal; background is the plain `--bg` with at most one soft radial tint behind the hero.

### 7.2 Chapter page
- Header: chapter-colored icon tile, title, one-sentence description, progress ("9 of 9 methods ready").
- Method list as rows: name, one-line description, key use case chip (e.g. "bracketing", "iterative",
  "needs equal spacing"), status chip, favorite star, chevron. Filter chips (All, Available, Coming soon) and
  quick search. "Start here" suggestion for beginners.
- Coming-soon methods show theory and pseudocode, clearly labeled.

### 7.3 Solver page (the priority; anatomy)
```
[Breadcrumb]   Home / Chapter 1 / Newton-Raphson                         [Favorite] [Share] [Export]
[Title row]    Newton-Raphson Method   [chapter chip]   [status chip appears after solve]
[Subtitle]     One sentence: when to use it. Link: "Theory"
------------------------------------------------------------------------------------------------
| INPUT PANEL (sticky, scrolls internally)         | RESULT PANE                                   |
| 1. Problem  (function / matrix / data table)     | Result header: status chip + headline answer   |
|    keypad toggle, live KaTeX preview, validation | Stat row: iterations, final error, order, time |
| 2. Parameters (x0, tolerance, max iterations)    | Tabs: Answer | Steps | Table | Graph | Theory |  |
| 3. Options (collapsed "Advanced")                |       Pseudocode | Code                        |
| Examples chips (3 to 5)                          | Tab content with its own toolbar (copy, CSV)   |
| [ Solve  Ctrl+Enter ]  [ Reset ]                 | Footer: Next steps (Compare, Try example,      |
|                                                  |        Related methods, Previous / Next)       |
------------------------------------------------------------------------------------------------
```
- Draggable divider between panes; the input panel can collapse to give results full width.
- **Before first solve (empty state):** a friendly panel with a small illustration, "Enter a problem or load an
  example", and the example chips. Never a blank pane.
- **During solve:** skeleton for the result header, steps and plot; Solve button shows a spinner; inputs stay editable.
- **After solve:** result fades in (180 ms), focus moves to the result heading (announce to screen readers),
  the URL updates with the inputs.
- **Failure or divergence:** a prominent alert in the result pane (cause, why it matters, suggested fix such as
  "try a different starting guess" with one-click actions), plus whatever partial steps were computed.

### 7.4 Command palette (Ctrl+K)
Search methods, chapters, help; ranked results with chapter color dots and status; recent items on open;
shows shortcuts; works on mobile as a full-width sheet.

### 7.5 Help, About, 404
Help: expression syntax cheat sheet (with copyable examples), keypad guide, shortcuts, FAQ ("Why did it
diverge?"). About: syllabus coverage, how results are verified (compared against SciPy/NumPy), credits.
404: illustration, search box, popular methods.

---

## 8. What every method page must show (content contract)

After a successful solve the user must see, without hunting:

| Element | Where | Details |
|---|---|---|
| Headline answer | Result header | Large mono value(s), correct precision, unit or variable name, copy button |
| Status | Chip next to the answer | Converged, Max iterations, Diverged, Failed, with a one-line meaning on hover or below |
| Key metrics | Stat row | Iterations, final error, tolerance used, stopping criterion, order of convergence (where relevant) |
| Input echo | Answer tab | The problem as typed and rendered (KaTeX), method and parameters used |
| Plain-language summary | Answer tab | 1 or 2 sentences: "Newton-Raphson converged to 1.52138 in 4 iterations" |
| Exam-style steps | Steps tab | Numbered, collapsible, real substituted numbers, changed values highlighted |
| Tables | Table tab | Iteration or node tables, final row highlighted, copy and CSV |
| Graph | Graph tab | Function/solution with markers (root, nodes, tangents, spline pieces), legend, hover values |
| Error analysis | Answer or Steps tab | Absolute and relative error, comparison with exact or reference value when available |
| Warnings | Alert above the tabs | Ill-conditioning, extrapolation, not diagonally dominant, step too large, etc., each with a suggested fix |
| Theory | Theory tab | Formula, when to use, assumptions, advantages and limits, common mistakes (exam notes) |
| Pseudocode and Code | Tabs | Copyable, line numbers, runnable Python |
| Next actions | Result footer | Export PDF/CSV, Share link, Compare with other methods, Try an example, Related methods |
| Reproducibility | Footer of the result | Inputs, tolerance, version, timestamp in exports |

Chapter-specific extras: roots (bracket and tangent/secant lines, convergence plot, compare tool), linear
systems (matrix after every operation, pivot explanation, residual check A*x - b), interpolation (difference
tables, basis polynomials, extrapolation warning, fit quality R-squared and residuals), integration (node
table, exact error, convergence slope), ODEs (k-values per step, phase plot, step-size study), PDEs (grid
heat map, time slider, stability number r).

---

## 9. Components

| Component | Spec |
|---|---|
| Button | Primary (accent fill; brand gradient only on landing CTAs), secondary (surface + border), ghost, danger. Height 32 compact / 36 comfortable / 44 on touch. States: hover, pressed (scale .98), focus ring, disabled, loading (spinner, width stays). |
| Input | Height 36, radius 8, 1 px border, accent focus ring, label above, helper text, inline error with icon, unit suffix, clear button. |
| Expression field | Mono font, live KaTeX preview below, keypad toggle at the right, validation as you type, paste normalization. |
| Keypad | Flat panel under the field; tabs Numbers, Operators, Functions, Variables, Edit; large keys; inserts at cursor; remembers show/hide. |
| Matrix and data grid | Cell inputs with tab/arrow navigation, add/remove row and column, paste from Excel/CSV, per-cell validation. |
| Tabs | Underline style with a sliding 2 px accent bar, keyboard accessible, sticky under the toolbar, scroll horizontally on mobile. |
| Card | e1; interactive cards lift to e2 on hover; chapter cards get a 3 px chapter-colored top border. |
| Chip | 999 radius, soft semantic tint, icon plus text. Statuses: Converged, Diverged, Failed, Max iterations, Available, Coming soon, Beta. |
| Alert | Soft tinted background, left icon, title, message, optional actions; variants: info, success, warning, error. |
| Stat tile | Label (12 px, muted), value (mono 20 to 24), optional delta or hint. |
| Table | See section 10. |
| Steps | See section 10. |
| Tooltip | e3, 120 ms fade, on hover and keyboard focus, never the only place for essential info. |
| Toast | Bottom-right, e3, auto-dismiss 4 s, used for copy, export, share confirmations. |
| Skeleton | Shimmer blocks that match the final layout. |
| Empty state | Illustration, title, one-line help, primary action. |
| Breadcrumb, Pagination-free lists | Breadcrumb on method pages; long lists use filters, not pages. |
| Progress bar | 6 px, rounded, brand gradient fill. |
| Favorite star, Recent list | Persist in localStorage (try/catch). |

---

## 10. Data components (where the quality shows)

**Steps.** A vertical timeline: numbered node, title, collapsible card. KaTeX at 16 to 18 px with 1.7 line
height; substituted numbers visible; the value that changed in each step highlighted with `--accent-soft`;
"Expand all / Collapse all"; anchor link and copy-as-text per step; long steps scroll horizontally inside
the card.

**Tables.** Right-aligned numeric columns, mono tabular figures, same precision per column, sticky header and
first column, final row highlighted (accent-soft plus bold), subtle zebra (`--surface-2`), 1 px dividers,
copy cell/row/table, CSV download, density-aware rows, horizontal scroll inside the container with a visible
edge shadow. Column headers use short labels with KaTeX where helpful and tooltips for definitions.

**Graphs (Plotly).** One shared theme built from tokens for every theme:
- Transparent background, 1 px grid at low contrast, token axis and text colors, tabular numbers in hover.
- Colorblind-safe Okabe-Ito series: #0072B2, #E69F00, #009E73, #D55E00, #CC79A7, #56B4E9 (yellow only on dark).
- Legend on top, minimal modebar (zoom, pan, reset, PNG), direct labels where possible.
- Distinct markers for key points (root, nodes, extrema, final value) with hover labels.
- Lazy-loaded; height 360 to 480 desktop; iteration player (play, pause, step, scrub, speed) for iterative methods;
  fullscreen button; "Download PNG".

**KaTeX.** Token colors, scales with density, centered block formulas, scrolls inside its own container.

**Code and pseudocode.** Mono, `--surface-2`, radius 12, line numbers, copy button, per-theme syntax tokens.

---

## 11. Microcopy and tone

Voice: clear, short, encouraging, precise. Say what happened, why, and what to do next.

| Situation | Write | Avoid |
|---|---|---|
| Empty state | "Enter a problem or load an example to see the steps." | "No data." |
| Success | "Converged to 1.52138 in 4 iterations." | "Success!" |
| Failure | "f(a) and f(b) have the same sign, so a root may not be bracketed. Try a wider interval." | "Error 400" |
| Divergence | "The iterates grew without bound. Try a starting guess closer to the root." | "Diverged." |
| Validation | "Use * for multiplication, for example 2*x." | "Invalid input" |
| Warning | "Matrix is not diagonally dominant. Jacobi may not converge." | "Warning!" |
| Buttons | "Solve", "Load example", "Export PDF", "Copy steps" | "Submit", "Go" |
| Coming soon | "Coming soon. Theory and pseudocode are available now." | "Not available" |

Use sentence case, "you" sparingly, no exclamation marks, no jargon without a tooltip.

---

## 12. UX features that make it feel professional

- Command palette (Ctrl+K), keyboard shortcuts sheet (`?`): Ctrl+Enter solve, Ctrl+B sidebar, F focus, / search.
- Shareable URLs with inputs; copy-link toast.
- History, Recent and Favorites (local); "Restore last problem" on return.
- Examples per method (3 to 5), including a failure example that teaches.
- Exam mode: hides the answer and shows a worksheet; reveal on demand.
- Density toggle (compact or comfortable) and theme control (Light, Paper, Dark, System).
- Print stylesheet and PDF export suitable for lab reports.
- Inline help: "?" tooltips beside technical parameters (tolerance, stopping criterion).
- Optimistic and persistent UI: input panel state, tab choice and sidebar mode survive refresh.
- Offline-friendly static assets; graceful message if the backend is unreachable.

---

## 13. Accessibility

WCAG 2.2 AA in all themes; axe reports zero A/AA violations. Everything keyboard operable with visible focus
rings (never clipped); logical tab order; landmarks (header, nav, main); headings in order; `aria-live` for
solve status and toasts; `aria-expanded`, `aria-current`, `role="separator"` with `aria-valuenow/min/max`
on resize handles; tooltips on focus; touch targets at least 40 px; `prefers-reduced-motion` and
`prefers-color-scheme` respected; no meaning by color alone; math has accessible text alternatives.

---

## 14. Performance (perceived and real)

Lazy-load Plotly and heavy routes; self-hosted subset fonts; skeletons that match final layout; no layout shift
on theme or state change; Lighthouse at least 90 on performance, accessibility and best practices; interactions
under 100 ms; long solves show progress and can be cancelled.

---

## 15. Do and don't

| Do | Don't |
|---|---|
| Use tokens for everything | Hard-code `#hex`, px values or `z-index: 9999` |
| Use soft depth (e1 to e3) with restraint | Stack heavy shadows or glow effects |
| Use the brand gradient as a small signature | Fill pages or panels with gradients |
| Color-code chapters in small accents | Use chapter colors as large backgrounds |
| Show empty, loading, error and warning states for every view | Leave blank panes or raw errors |
| Explain failures and offer a fix | Show "Error" or stack traces |
| Right-align numbers, use tabular figures | Mix precisions or alignments in a column |
| Give every page a clear primary action | Hide the Solve action or bury it |
| Let results use the available width | Cap solver pages at a narrow width |
| Test Light, Paper, Dark at 1024, 1280, 1440, 1920 and mobile | Check only one theme or size |

---

## 16. Adding a theme or component

New theme: define every token in section 5.1, verify AA contrast, add the Plotly and syntax variants, add to
the theme control and the rail cycle, add Playwright snapshots, update this file. New component: check if an
existing one fits; build it from tokens; add states (hover, focus, disabled, loading, error); add keyboard
behavior; document it in section 9.

---

## 17. Definition of done and visual QA loop

For every UI change:
- [ ] Uses tokens only; grep finds no hard-coded colors, spacing or shadows
- [ ] Screenshots taken in Light, Paper and Dark at 1024, 1280, 1440, 1920 and 390 px, DPR 1 and 2
- [ ] Self-critique written: hierarchy clear? spacing consistent? alignment on the 4 px grid? one obvious primary action? anything cramped, clipped or low-contrast?
- [ ] Empty, loading, error, warning and success states all designed and checked
- [ ] Content contract (section 8) satisfied for any method page touched
- [ ] No horizontal scroll, clipping or accidental truncation (overflow audit passes)
- [ ] Rail and hamburger centers at x = 28 +/- 0.5 px
- [ ] Keyboard path works, focus visible, axe clean, contrast AA
- [ ] Plotly and KaTeX follow the theme; numbers are tabular
- [ ] Lint, typecheck, unit tests, Playwright, build all pass
- [ ] `docs/ui-qa.md` updated with before and after screenshots and any remaining imperfections