# Jobfolio Design System & Tokens

## Visual Identity & Philosophy

Jobfolio uses an organic, tactile, and editorial design aesthetic tailored for professional job seekers:
- **Primary Tone**: Deep forest greens (`#173e32`, `#246952`), calm sage accents (`#dde9df`, `#cfe7d8`), and crisp dark ink (`#253a35`) on soft off-white canvas (`#f5f7f6`).
- **Typography**: Manrope Variable font (`'Manrope Variable', sans-serif`) with subtle letter-spacing adjustments for high legibility in headings and CV body copy.
- **Surfaces**: Pure white cards (`#ffffff`) with restrained border outlines (`#dde5e0`, `#cbd9cf`) and crisp contrast for document review.
- **Tactility**: Native form controls with 44px min-touch targets on mobile and clear 3px focus rings (`#467d62`).

## Design Tokens (`frontend/src/shared/styles/tokens.css`)

```css
:root {
  /* Brand Palette */
  --color-brand-dark: #173e32;
  --color-brand-primary: #246952;
  --color-brand-hover: #1d5543;
  --color-brand-subtle: #eaf0e4;
  --color-brand-accent: #aed8b9;

  /* Surfaces & Backgrounds */
  --color-bg-app: #f5f7f6;
  --color-bg-card: #ffffff;
  --color-bg-topbar: #fafbf9;
  --color-bg-sidebar: #173e32;
  --color-bg-highlight: #e8f1e7;

  /* Typography Colors */
  --color-text-main: #253a35;
  --color-text-muted: #65736e;
  --color-text-inverse: #ffffff;

  /* Borders & Dividers */
  --color-border-subtle: #dde5e0;
  --color-border-focus: #467d62;

  /* Semantic Feedback */
  --color-success: #355e35;
  --color-warning: #765721;
  --color-error: #8c453b;
  --color-info: #375d7c;

  /* Spacing Units */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;

  /* Border Radii */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 10px;
  --radius-pill: 9999px;
}
```

## Core UI Components

1. **`Button` (`frontend/src/shared/ui/Button.tsx`)**:
   - Variants: `default` (white subtle border), `primary` (forest green), `text` (inline link button), `icon` (frameless icon).
   - Accessible disabled states with opacity and `aria-disabled`.

2. **`Badge` (`frontend/src/shared/ui/Badge.tsx`)**:
   - Status indicators: `awaiting_review`, `needs_input`, `uncertain` (amber/tan), `approved`, `submitted` (sage/green), `skipped` (muted gray).
   - Includes circular status dot.

3. **`Field` (`frontend/src/shared/ui/Field.tsx`)**:
   - Accessible `<label>` wrapping inputs with semantic `<span>{label}</span>` text and `<small>` helper/error text.
   - Preserves exact label name matching for assistive tech and Playwright tests.

4. **`DynamicField` (`frontend/src/features/applications/components/DynamicField.tsx`)**:
   - Dynamically renders application question inputs.
   - Translates radio question options into semantic `<fieldset>` groups with `<legend>` and native `<input type="radio">`.
   - Displays clear local file upload notice when employer requests file attachments.

5. **`Notice` (`frontend/src/shared/ui/Notice.tsx`)**:
   - High-contrast alert banners (`info`, `success`, `warning`, `error`) with matching Lucide icons.

## Responsive Layouts & Breakpoints

- **Desktop (>1200px)**: Full fixed 232px sidebar with workspace switcher, local privacy indicators, and responsive two-column layouts.
- **Tablet (900px - 1200px)**: Compact sidebar (210px), optimized grid spacing.
- **Mobile (<900px)**: Top horizontal navigation bar, single-column stacked forms, sticky bottom save actions, and 100% viewport width without horizontal overflow. Verified across 390px (iPhone) and 1440px (Desktop).
