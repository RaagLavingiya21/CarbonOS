# Design System — Editorial Direction

## Intent

The design system is warm, calm, and trustworthy. Inspired by Watershed and Claude's principles, it prioritizes clarity and approachability for sustainability analysts who need reliable, auditable results. The palette emphasizes soft, natural tones with disciplined accent usage to guide attention to critical information like emission hotspots.

## CSS Variable Tokens

### Surfaces & Ink

| Variable | Value | When to Use |
|----------|-------|-------------|
| `--background` | 40 33% 98% (warm paper) | Page background, primary canvas |
| `--foreground` | 165 28% 13% (deep forest) | Body text, primary ink |
| `--card` | 40 25% 99% | Card backgrounds, contained surfaces |
| `--card-foreground` | 165 28% 13% | Text on cards |
| `--popover` | 40 25% 99% | Tooltips, dropdowns, floating UI |
| `--popover-foreground` | 165 28% 13% | Text in popovers |

### Brand

| Variable | Value | When to Use |
|----------|-------|-------------|
| `--primary` | 160 58% 24% (deep green) | Primary actions, main CTAs only |
| `--primary-foreground` | 40 33% 98% | Text on primary buttons |
| `--secondary` | 40 20% 94% | Secondary actions, less emphasis |
| `--secondary-foreground` | 165 24% 18% | Text on secondary buttons |
| `--muted` | 40 18% 93% | Disabled state backgrounds |
| `--muted-foreground` | 165 10% 42% | Disabled/placeholder text |
| `--accent` | 155 32% 92% (soft green tint) | Hover states, accents (use sparingly) |
| `--accent-foreground` | 162 48% 22% | Text on accents |
| `--destructive` | 8 58% 47% (alert red) | Errors, deletions, warnings |
| `--destructive-foreground` | 40 33% 98% | Text on destructive elements |

### Lines

| Variable | Value | When to Use |
|----------|-------|-------------|
| `--border` | 40 16% 88% (hairline) | Subtle borders, dividers |
| `--input` | 40 16% 86% | Form input borders |
| `--ring` | 160 58% 30% | Focus rings |

### Semantic Data Palette

| Variable | Value | When to Use |
|----------|-------|-------------|
| `--data-low` | 150 52% 32% (green) | Low emission tier indicator |
| `--data-low-bg` | 150 40% 94% | Low emission badge background |
| `--data-medium` | 36 78% 44% (amber) | Medium emission tier indicator |
| `--data-medium-bg` | 38 80% 93% | Medium emission badge background |
| `--data-high` | 12 68% 47% (red) | High emission/hotspot indicator |
| `--data-high-bg` | 12 70% 95% | High emission badge background |
| `--data-neutral` | 165 8% 48% (gray) | Neutral data or unclassified |
| `--data-neutral-bg` | 165 12% 94% | Neutral badge background |
| `--data-info` | 192 46% 38% (blue) | Informational state |
| `--data-info-bg` | 192 45% 93% | Info badge background |

### Typography

| Variable | Font Stack |
|----------|------------|
| `--font-serif` | Newsreader, Iowan Old Style, Palatino, Georgia, ui-serif |
| `--font-sans` | Geist (var), ui-sans-serif, system fallback |
| `--font-mono` | Geist Mono (var), ui-monospace, SFMono, monospace |

**Rules:**
- Headings (h1–h3) and `.font-display` use serif font.
- Body text uses sans-serif.
- All numeric/data contexts use `tabular-nums` for aligned digits.

### Motion

| Variable | Value |
|----------|-------|
| `--ease-out` | cubic-bezier(0.2, 0, 0, 1) |
| `--ease-in-out` | cubic-bezier(0.4, 0, 0.2, 1) |
| `--dur-micro` | 120ms |
| `--dur` | 200ms |
| `--dur-panel` | 320ms |

**Rules:** Use micro (120ms) for small transitions (color, border); default (200ms) for component state changes; panel (320ms) for modals/drawers.

### Shape & Elevation

| Variable | Value |
|----------|-------|
| `--radius` | 0.625rem (10px) |
| `--shadow-xs` | Subtle card shadow |
| `--shadow-overlay` | Strong shadow for popovers/modals |

**Rules:**
- Use `shadow-xs` on resting cards; applies by default to Card component.
- Use `shadow-overlay` only on popovers and drawers.
- Flat surfaces with hairline borders; no heavy shadows.

## Type Scale

| Scale | Size / Line Height | Letter Spacing | Use Case |
|-------|-------------------|-----------------|----------|
| Display | 3rem / 1.05 | −0.025em | Page titles, hero sections |
| H1 | 2.125rem / 1.15 | −0.02em | Section headings |
| H2 | 1.625rem / 1.25 | −0.015em | Subsection headings |
| H3 | 1.25rem / 1.35 | −0.01em | Component headings |
| Body-lg | 1.0625rem / 1.65 | — | Large body copy, callouts |
| Body | 0.9375rem / 1.6 | — | Standard body text |
| Small | 0.8125rem / 1.25 | — | Secondary labels, metadata |
| Caption | 0.75rem / 1 | 0.01em | Footnotes, timestamps |

## Fonts: Future Swap

Currently using a CSS serif stack (Newsreader → Iowan → Palatino → Georgia) and Geist for body to avoid network font fetches and cold-start delays.

**Intended hosted webfonts (wire via `next/font/google` when available):**
- Display: Fraunces or Newsreader (warm, editorial serif)
- Body: Geist or Inter (clear, efficient sans-serif)

This preserves the editorial warmth while reducing layout shift and improving performance.

## Rules of Thumb

1. **One accent, used sparingly.** The green accent guides attention to primary actions. Avoid accent overload.
2. **Flat surfaces + hairline borders.** No glossy bevels or heavy shadows—clarity comes from thoughtful spacing and subtle boundaries.
3. **Shadows for depth hierarchy.** `shadow-xs` on cards (resting state); `shadow-overlay` only for floating UI (popovers, drawers, modals).
4. **Motion: micro → default → panel.** Snappy micro (120ms) for feedback; smooth default (200ms) for component changes; deliberate panel (320ms) for major transitions.
5. **Semantic colors as narrative.** Data tiers (low/medium/high) and states (info, neutral) are readable at a glance—essential for hotspot identification.
6. **Dark mode ready.** All tokens have light and dark CSS overrides at `.dark` scope, ensuring consistency across themes.
