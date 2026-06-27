# 意象若水 water_green — Design System

A design system for **water_green (意象若水)**, an e-commerce marketplace built to feel
**professional, trustworthy, and effortless (專業、信任、無負擔)**. It spans desktop, tablet,
and mobile, with core surfaces: marketplace home, product page, checkout, and order lookup.

Guiding philosophy — **生活減法 ("subtraction living")**: strip every non-essential line and
visual distraction; calm but commercially energetic; card-based layout with generous, breathing
whitespace tuned for the visual weight of Traditional-Chinese square characters.

> **Sources.** Built entirely from the written brief `00.tokens` / `01.components` /
> `02.modules` (意象若水). No codebase, Figma file, or brand imagery was attached. Brand hex
> values come straight from the brief; tokens marked *請 AI 自動配色* were filled professionally
> (see Caveats). Target stack in production: Next.js + Tailwind + shadcn/ui (visually overridden).

---

## CONTENT FUNDAMENTALS

- **Language:** Traditional Chinese (繁體中文), Taiwan market. Numerals/Latin in Inter.
- **Voice:** quietly confident, service-oriented, never hype-heavy. Short noun phrases over
  sentences for UI (`加入購物車`, `查看全部`, `綜合排名`, `月銷熱賣`). Addresses the shopper
  implicitly — no aggressive "you/我們" marketing slogans on chrome.
- **Casing:** Chinese has no case; the Latin lockup `water_green` is **lowercase with letter-spacing**.
  Avoid ALL-CAPS Chinese; small Latin labels (e.g. card group headers) may be uppercase.
- **Tone examples:** `寧靜但不失商業動能`, `放大區塊間的留白讓畫面呼吸`, `店取199免運`, `隔日到貨`,
  `庫存緊張`, `交易完成`. Promo copy is factual and compact (`-20%`, `TOP 1`, `月銷 1.2k 件`).
- **Emoji:** **none.** The brand never uses emoji or unicode pictographs as UI. All glyphs are
  Lucide line icons.
- **Numbers/data:** show only meaningful commerce signals — price, discount %, rating, units sold,
  monthly sales. No decorative stat-padding.

---

## VISUAL FOUNDATIONS

**Color.** Green-led brand. Primary `#498428` carries CTAs, active blocks, price, and the focus
ring; secondary `#80B155` and a light analogous **tertiary `#E4EFD9`** (auto-mixed) handle support,
hover-contrast, and lightweight backings (sidebar-active, logistics tags). Accent `#E55B3C`
(warm orange-red) is the single promo/attention color (discount tags, cart badge). Surfaces are
`#F5F7F2` (page floor) vs `#FFFFFF` (cards). The header uses **relative value**: topbar `#336A29`
(darker, recedes) under main nav `#498428` (lighter, steps forward). Light mode **only** — never
add dark-mode variants.

**Type.** Inter + Noto Sans TC. Headings 600/700 at line-height ~1.35 (compact CJK blocks); body
16px / 400 / 1.65 (vertical breathing room); interface labels 14–16px / 500. Prose measure capped
at 800px for readability.

**Spacing & layout.** Strict 8pt grid (4/8/16/24 · 32/48/64 · 80/120/160). Container max 1440px;
footer content max 1200px. Grid: 12-col desktop (24px gap), 8-col tablet (20px), 4-col mobile (16px).
Left category rail fixed at 240px with a 32px gap to content. **Anti-compounding rule:** listed
values are the *final* visual gap — never stack parent gap + child margin.

**Elevation — FLAT.** No `box-shadow`, no `drop-shadow`, no 3D, no gradients anywhere. Depth comes
**only** from `1px solid var(--color-border)`, the bg-base/bg-surface color step, and 8pt whitespace.

**Corners.** 4px tight active chips · 8px buttons/inputs/FAB/control-bar · 12px product cards &
images · full-round only for avatars and notification dots. Never `rounded-full` on buttons/cards.

**Borders & cards.** Cards are white, 12px radius, 1px hairline border, **no shadow**. The left
sidebar is *not* a card — it's transparent and blends into the page floor.

**Imagery.** Product images locked to `1:1` or `3:4`, `object-fit: cover`, `overflow:hidden`.
Hover zooms the image to `scale(1.05)` — never a shadow or card lift. Below-fold images `loading="lazy"`;
a flat grey `#F3F4F6` skeleton holds the slot first (pulse only, no shimmer). Overlay tags are clean
**solid** blocks — never a dark gradient mask over the photo.

**Motion.** Global `transition: all 0.2s ease-out`. Hover = flat color/opacity change only
(`opacity 0.85` or ±5% brightness); never `translateY` lifts or dynamic shadows. Press never shrinks.

**Focus.** Mandatory keyboard ring: `outline: 2px solid var(--color-primary); outline-offset: 2px`.
Never `outline:none` without a replacement. Inputs show the ring on focus — never a glow shadow.

---

## ICONOGRAPHY

- **Single source: Lucide** (line icons). Spec: `viewBox 0 0 24 24`, `stroke-width 1.5`,
  `stroke-linecap/linejoin: round`, `fill:none`. Minimal flat line style — never solid/filled,
  never hand-authored `<svg><path>`.
- In this system, the **`Icon`** component renders Lucide path data from the global `window.lucide`
  (loaded via the Lucide CDN in cards/kits) so components stay dependency-free. **In production use
  `lucide-react`** directly (`import { ShoppingCart } from 'lucide-react'`).
- **Key mappings (locked by the brief):** filter → `sliders-horizontal` (never a funnel); all-categories
  → `layout-grid` (never a hamburger/list); chat FAB → `message-circle-more`; cart → `shopping-cart`;
  topbar → `store`, `arrow-down-to-line`, `bell`, `circle-help` (the brief's `circle-question-mark`
  isn't in this Lucide build — `circle-help` is the match), `globe`, social `facebook`/`instagram`/`message-circle`.
- **Emoji / unicode icons: never.**

---

## INDEX (manifest)

**Root**
- `styles.css` — the single entry consumers link (import list only).
- `tokens/` — `fonts.css`, `colors.css`, `typography.css`, `spacing.css`, `radius.css`, `base.css`.
- `readme.md` (this file), `SKILL.md`.

**Components** (`components/<group>/<Name>.{jsx,d.ts,prompt.md}` + one `@dsCard` HTML per group)
- `core/` — **Icon**, **Avatar**, **Divider**, **Skeleton**
- `buttons/` — **Button**, **IconButton**, **Dropdown** (open-to-activate)
- `forms/` — **Input**, **SearchBar** (large header combo)
- `feedback/` — **Badge**, **Tag** (promo / logistics / feature / rating)
- `navigation/` — **SidebarItem**, **Pagination** (oversized flat pager)
- `commerce/` — **ProductCard** (standard + compact variant)

**UI kits** (`ui_kits/<product>/`)
- `storefront/` — the marketplace listing page: Header (topbar + masthead + cart panel), Sidebar,
  Toolbar (sort + filter + mini pager), ProductGrid, Pagination, Footer, ChatFAB. Interactive:
  search, sort, sidebar select, pagination, add-to-cart preview. Entry: `index.html`.

**Foundation cards** (`guidelines/*.card.html`) — Colors, Type, Spacing, Brand specimens for the
Design System tab.

---

## CAVEATS
- **Fonts** load from the Google Fonts CDN (no binaries were supplied). Inter + Noto Sans TC are the
  exact families named — provide self-hosted files to ship offline.
- **Logo** is a typographic placeholder; the brief describes a calligraphic 「若水」 mark — supply the
  real SVG to replace it.
- **Product imagery** uses `picsum.photos` generic placeholders. Swap for real product photos.
- **Auto-colored tokens:** `--color-tertiary` (`#E4EFD9`) was mixed as a light analogous green;
  confirm it matches your intended brand swatch.
