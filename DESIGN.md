# Slice of Pi — Design System

## Brand Identity

| Token | Hex | Role |
|-------|-----|------|
| `#121A11` | Near-black green | Page background (`void`) |
| `#9DD522` | Electric lime | Primary accent — buttons, links, active states |
| `#D3ED2F` | Acid lime | Bright highlight — hover glows, bright accents |
| `#5A6656` | Muted slate gray | Mid-tones, secondary text, muted borders |
| `#E9ECE0` | Off-white silver | Primary text, high-contrast elements |

### Extended Palette

| Token | Hex | Role |
|-------|-----|------|
| `#354A21` | Charcoal green-gray | Dark tactical surfaces |
| `#364948` | Gunmetal teal | Dark accent, dividers |
| `#699520` | Olive-lime | Secondary green |
| `#4B5F2C` | Moss green | Muted tech green |
| `#E0E8A4` | Pale yellow-green | Soft reflection highlight |
| `#C99A2E – #E6B13A` | Golden yellow-orange | Slice/pie accent |

---

## Typography

| Token | Font | Weight | Usage |
|-------|------|--------|-------|
| `font-display` | Clash Display | 500–700 | Headings, logo |
| `font-body` | Satoshi | 400–700 | Body text, labels, buttons |
| `font-mono` | JetBrains Mono | 400–500 | Code, inputs, terminal, logs |

---

## Text Input Fields

All text inputs follow a single pattern:

```
background: transparent
backdrop-filter: blur(4px)
border: 1px solid rgba(233,236,224,0.15)   // #E9ECE0 at 15%
border-radius: 12px
color: #E9ECE0
padding: 10px 12px

placeholder color: rgba(233,236,224,0.20)

focus:
  border-color: #9DD522   // lime accent
```

**CSS class**: `input-base`

For `<select>` elements and cases where `input-base` cannot be applied directly, use the inline equivalent:
```
class="bg-transparent backdrop-blur-sm border border-white/12 rounded-btn px-2 py-1.5 text-xs text-text-tertiary outline-none"
```

### Apply to:
- Chat message input
- Search fields
- Agent name / create fields
- Credential name/value fields
- MCP key fields
- Settings fields
- Session name field
- Schedule fields
- Login form fields
- Agent detail edit fields
- Audit log filter fields
- Any text `input`, `textarea`, or `select`

### Files already using `input-base`:
- `ChatHistoryDropdown.vue` — session name editor
- `CredentialsPanel.vue` — name + value inputs
- `McpKeysPanel.vue` — key name + value inputs
- `Agents.vue` — create name + search inputs

### Files using inline transparent+blur (will be migrated to `input-base`):
- `Login.vue` — login/register fields (CSS class `.login-field input`)
- `AgentDetail.vue` — edit form fields (CSS class `.edit-field input`)
- `AuditLog.vue` — filter inputs (CSS classes `.filter-select`, `.filter-input`, `.filter-date`)
- `Agents.vue` — status filter `<select>`

---

## Buttons

| Type | Background | Text | Border | Hover |
|------|-----------|------|--------|-------|
| Primary | `#9DD522` | `#121A11` | none | `#8BC01E` |
| Secondary | transparent | `#E9ECE0` at 65% | `rgba(233,236,224,0.15)` | bg at 5%, text full |
| Ghost | transparent | `#E9ECE0` at 35% | none | bg at 5% |
| Danger | `#EF4444` | white | none | darker red |

---

## Surfaces & Borders

| Token | Value | Usage |
|-------|-------|-------|
| `surface` | `rgba(233,236,224,0.03)` | Card/section backgrounds |
| `surface-hover` | `rgba(233,236,224,0.05)` | Card hover |
| `surface-raised` | `rgba(233,236,224,0.06)` | Raised elements |
| `border` | `rgba(233,236,224,0.08)` | Default borders |
| `border-hover` | `rgba(233,236,224,0.12)` | Hover borders |
| `border-strong` | `rgba(233,236,224,0.18)` | Strong borders, inputs |

---

## Glass / Blur Effects

```
background: transparent
backdrop-filter: blur(4px)    // inputs
backdrop-filter: blur(8px)     // modals, overlays
backdrop-filter: blur(32px) saturate(1.4)   // nav bar
```

Glass is always transparent background + backdrop blur + a subtle border.

---

## Spacing

| Token | px | rem |
|-------|----|-----|
| `gap-xs` | 4 | 0.25 |
| `gap-sm` | 8 | 0.5 |
| `gap-md` | 12 | 0.75 |
| `gap-lg` | 16 | 1 |
| `gap-xl` | 24 | 1.5 |
| `pad-xs` | 4 | 0.25 |
| `pad-sm` | 8 | 0.5 |
| `pad-md` | 12 | 0.75 |
| `pad-lg` | 16 | 1 |
| `pad-xl` | 24 | 1.5 |

---

## Radius

| Token | Value | Usage |
|-------|-------|-------|
| `rounded-btn` | 12px | Buttons, inputs, cards |
| `rounded-card` | 20px | Cards, panels |
| `rounded-pill` | 9999px | Badges, pills |

---

## How to Edit

### Changing accent color
Edit `dashboard/tailwind.config.js` → `colors.accent`:
```js
accent: {
  DEFAULT: '#9DD522',
  hover: '#8BC01E',
  muted: 'rgba(157,213,34,0.12)',
  glow: 'rgba(157,213,34,0.25)',
}
```

### Changing input styles
All text inputs should use `input-base` from `assets/main.css`.
To change all inputs globally, edit the `.input-base` class there.

### Adding a new brand color
1. Add the hex to `tailwind.config.js` under `colors`
2. Use it as `text-{name}`, `bg-{name}`, `border-{name}` in components
3. Never hardcode hex values in Vue files — always use a Tailwind token or CSS variable
