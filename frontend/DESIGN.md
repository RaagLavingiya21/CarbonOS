# Design System — Compact, Data-Dense Direction

## Intent

The design system is **compact, precise, and data-dense** — inspired by Linear, Stripe, and Watershed. It is built for sustainability analysts who scan large tables of footprint data and need every number to be legible, aligned, and auditable. The surface is a warm off-white; the ink is a cool slate; the single brand accent is a muted forest green, used sparingly to guide attention to primary actions and emission hotspots.

This replaces the earlier warm serif-editorial direction. Headings are now sans (Inter Tight), the type scale is tighter, and layouts run denser.

## Typography

| Variable | Font Stack | Role |
|----------|------------|------|
| `--font-sans` | Inter (var), ui-sans-serif, system | Body, UI, default |
| `--font-display` | Inter Tight (var) → Inter, ui-sans-serif | Headings (h1–h4, `.font-display`) |
| `--font-mono` | JetBrains Mono (var), ui-monospace | Numeric detail, code, `.kbd` |
| `--font-serif` | Newsreader → Georgia, ui-serif | **Retired** — kept defined only as a safety fallback; do not use |

Fonts load via `next/font/google` in `app/layout.tsx` (self-hosted at build) and are exposed as CSS variables consumed by the tokens above. **Never point `fontFamily.sans` at a literal font name in `tailwind.config.ts`** — with `next/font` that silently breaks fonts to serif. Drive fonts through the CSS variables + `body { font-family: var(--font-sans) }` only.

**Rules:**
- `body` is 14px / 1.45 / `-0.006em` tracking with `cv11`, `ss01` features — the dense baseline.
- Headings use `--font-display` with `-0.022em` tracking.
- All numeric/data contexts use tabular figures — apply `.num` (or `tabular-nums`).

### Type Scale (compact)

| Class | Size / Line Height | Tracking | Use |
|-------|-------------------|----------|-----|
| `text-display` | 1.75rem / 1.15 | −0.025em | Page hero titles |
| `text-h1` | 1.375rem / 1.2 | −0.02em | Page titles (~22px) |
| `text-h2` | 1.125rem / 1.3 | −0.015em | Section headings |
| `text-h3` | 0.9375rem / 1.35 | −0.01em | Component headings |
| `text-body-lg` | 0.875rem / 1.55 | — | Callouts |
| `text-body` | 0.8125rem / 1.45 | — | Standard body |
| `text-small` | 0.75rem / 1.1rem | — | Secondary labels, metadata |
| `text-caption` | 0.6875rem / 1rem | 0.01em | Footnotes, chips, timestamps |

## CSS Variable Tokens

Tokens are stored as raw HSL triplets (`H S% L%`) and consumed via `hsl(var(--token))`, which also supports opacity modifiers (e.g. `bg-primary/10`). All tokens have light (`:root`) and dark (`.dark`) values. **Dark mode is light-first**: it is kept functional and coherent, not pixel-tuned.

### Surfaces & Ink

| Variable | When to Use |
|----------|-------------|
| `--background` | Page canvas (warm off-white) |
| `--surface` | Cards / raised surfaces (white) |
| `--surface-2` | Quiet panel headers, table heads, footers |
| `--elevated` | Popovers, dropdowns, floating dock |
| `--foreground` | Primary ink (cool slate) |
| `--muted-foreground` | Secondary text |
| `--subtle` | Tertiary/dimmed text (below muted) |
| `--card`, `--popover` (+ `-foreground`) | Contained + floating surfaces |

### Brand & State

| Variable | When to Use |
|----------|-------------|
| `--primary` (+ `-foreground`) | Muted forest green — primary actions, main CTAs only |
| `--secondary` (+ `-foreground`) | Low-emphasis actions |
| `--muted` (+ `-foreground`) | Disabled/placeholder backgrounds |
| `--accent` (+ `-foreground`) | Soft green tint — hover/selected nav |
| `--destructive` (+ `-foreground`) | Errors, deletions |
| `--success`, `--warning`, `--info` (+ `-bg`) | State semantics — **aliased to `--data-low` / `--data-medium` / `--data-info`** so they stay in sync (no duplication) |

### Lines

| Variable | When to Use |
|----------|-------------|
| `--border` | Hairline borders, dividers |
| `--border-strong` | Emphasized dividers, focus-within edges |
| `--input` | Form input borders |
| `--ring` | Focus rings |

### Semantic Data Palette (emission tiers)

`--data-low`, `--data-medium`, `--data-high`, `--data-neutral`, `--data-info`, each with a soft `-bg` pair. Drives emission-tier badges and hotspot visualizations. Readable at a glance for hotspot identification.

## Utilities

- `.num` — tabular numerals (`tnum`, `cv11`) for aligned data columns.
- `.kbd` — keyboard-hint chip (mono, hairline border, surface background).
- `.tabular-nums`, `[data-numeric]` — tabular figures.
- `.text-balance`, `.text-pretty` — wrapping.

## Shape & Elevation

| Variable | Value |
|----------|-------|
| `--radius` | 0.5rem (8px); `md` = 6px, `sm` = 4px |
| `--shadow-xs` | Subtle resting-card shadow |
| `--shadow-overlay` | Popovers / drawers / modals only |

**Rules:** flat surfaces + hairline borders; `shadow-xs` on resting cards; `shadow-overlay` only for floating UI. Depth comes from surface layering (`background` → `surface-2` → `surface` → `elevated`), not heavy shadows.

## Motion

| Variable | Value |
|----------|-------|
| `--dur-micro` | 120ms (color/border feedback) |
| `--dur` | 200ms (component state) |
| `--dur-panel` | 320ms (modals/drawers) |
| `--ease-out`, `--ease-in-out` | cubic-bezier easings |

## Density & Component Sizing

Compact by default (Linear-grade):
- Buttons: `default` h-8 / `sm` h-7 / `lg` h-10 / `icon` h-8; 3.5 icons; gap-1.5.
- Cards: `p-4` header/content/footer (was `p-6`).
- Inputs: h-8, `px-2.5 py-1.5`.
- Badges: `px-1.5 py-0.5`, `text-caption`.
- Dense tables: hairline row borders, `surface-2` heads, sticky first column, grouped headers.

## Rules of Thumb

1. **One accent, used sparingly.** Green marks primary actions and hotspots — avoid accent overload.
2. **Flat surfaces + hairline borders.** Depth via surface layering, not shadows.
3. **Every number is tabular and traceable.** Use `.num`; each aggregate drills down to its source. Never render an invented number — show a clearly-labeled "no data yet" placeholder for values with no backing source.
4. **Dense but scannable.** Tight spacing, but preserve alignment and clear hierarchy.
5. **Dark mode stays coherent.** All tokens have `.dark` values; verify nothing breaks, even if not pixel-tuned.
