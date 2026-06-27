/* @ds-bundle: {"format":3,"namespace":"WaterGreenDesignSystem_32a61f","components":[{"name":"Button","sourcePath":"components/buttons/Button.jsx"},{"name":"Dropdown","sourcePath":"components/buttons/Dropdown.jsx"},{"name":"IconButton","sourcePath":"components/buttons/IconButton.jsx"},{"name":"ProductCard","sourcePath":"components/commerce/ProductCard.jsx"},{"name":"Avatar","sourcePath":"components/core/Avatar.jsx"},{"name":"Divider","sourcePath":"components/core/Divider.jsx"},{"name":"Icon","sourcePath":"components/core/Icon.jsx"},{"name":"Skeleton","sourcePath":"components/core/Skeleton.jsx"},{"name":"Badge","sourcePath":"components/feedback/Badge.jsx"},{"name":"Tag","sourcePath":"components/feedback/Tag.jsx"},{"name":"Input","sourcePath":"components/forms/Input.jsx"},{"name":"SearchBar","sourcePath":"components/forms/SearchBar.jsx"},{"name":"Pagination","sourcePath":"components/navigation/Pagination.jsx"},{"name":"SidebarItem","sourcePath":"components/navigation/SidebarItem.jsx"}],"sourceHashes":{"components/buttons/Button.jsx":"3f29043d83a4","components/buttons/Dropdown.jsx":"e1cba318aa37","components/buttons/IconButton.jsx":"8c7f103353d3","components/commerce/ProductCard.jsx":"a46991725604","components/core/Avatar.jsx":"eccd1501b359","components/core/Divider.jsx":"ca60d7c5be24","components/core/Icon.jsx":"fbe00b5f4667","components/core/Skeleton.jsx":"c2d98c72d2bd","components/feedback/Badge.jsx":"3748754a3882","components/feedback/Tag.jsx":"800ea7d69f58","components/forms/Input.jsx":"8d4e1e979941","components/forms/SearchBar.jsx":"45b98d1233e2","components/navigation/Pagination.jsx":"a7bb609af020","components/navigation/SidebarItem.jsx":"b4603a5235ad","ui_kits/storefront/App.jsx":"0827987ceb01","ui_kits/storefront/ChatFAB.jsx":"d0da317adf41","ui_kits/storefront/Footer.jsx":"4d98ac54f7da","ui_kits/storefront/Header.jsx":"fcf4ec421207","ui_kits/storefront/ProductGrid.jsx":"9e2d03a9dac5","ui_kits/storefront/Sidebar.jsx":"db9a63a2ddab","ui_kits/storefront/Toolbar.jsx":"4a13d2a5f483","ui_kits/storefront/data.js":"a91d92e5c83b"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.WaterGreenDesignSystem_32a61f = window.WaterGreenDesignSystem_32a61f || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/core/Divider.jsx
try { (() => {
/**
 * Divider — flat 1px separators built only from --color-border.
 * Variants:
 *  - horizontal (default): full-width 1px rule (section breaks, footer top).
 *  - vertical: fixed-height 1px rule (toolbar: 篩選 | 排序).
 *  - pipe: a text "|" at opacity 0.3 for ultra-tight topbar links.
 */
function Divider({
  orientation = 'horizontal',
  height = 16,
  className = '',
  style = {}
}) {
  if (orientation === 'pipe') {
    return /*#__PURE__*/React.createElement("span", {
      "aria-hidden": "true",
      className: className,
      style: {
        color: 'var(--color-border)',
        opacity: 0.3,
        userSelect: 'none',
        ...style
      }
    }, "|");
  }
  if (orientation === 'vertical') {
    return /*#__PURE__*/React.createElement("span", {
      role: "separator",
      "aria-orientation": "vertical",
      className: className,
      style: {
        display: 'inline-block',
        width: '1px',
        height: typeof height === 'number' ? `${height}px` : height,
        background: 'var(--color-border)',
        flexShrink: 0,
        ...style
      }
    });
  }
  return /*#__PURE__*/React.createElement("hr", {
    className: className,
    style: {
      border: 0,
      width: '100%',
      height: '1px',
      background: 'var(--color-border)',
      margin: 0,
      ...style
    }
  });
}
Object.assign(__ds_scope, { Divider });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Divider.jsx", error: String((e && e.message) || e) }); }

// components/core/Icon.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Icon — renders a Lucide line icon to the brand spec
 * (viewBox 0 0 24 24, stroke-width 1.5, round caps/joins, no fill).
 *
 * The brief forbids hand-authored <svg><path>… markup; all icons come from the
 * Lucide set. This helper reads icon path data from the global `window.lucide`
 * (loaded via the Lucide CDN in cards / UI kits) so components stay dependency-
 * free. In production (Next.js) use `lucide-react` directly: <Search />.
 *
 * `name` accepts kebab ("shopping-cart") or Pascal ("ShoppingCart").
 */
function Icon({
  name,
  size = 24,
  strokeWidth = 1.5,
  className = '',
  style = {},
  color,
  ...rest
}) {
  const node = resolveIconNode(name);
  const merged = {
    width: size,
    height: size,
    color: color || 'currentColor',
    display: 'inline-block',
    flexShrink: 0,
    verticalAlign: 'middle',
    ...style
  };
  if (!node) {
    // Graceful placeholder if Lucide hasn't loaded yet — keeps layout stable.
    return /*#__PURE__*/React.createElement("span", _extends({
      className: className,
      style: {
        ...merged,
        display: 'inline-block'
      },
      "data-lucide": name,
      "aria-hidden": "true"
    }, rest));
  }
  return /*#__PURE__*/React.createElement("svg", _extends({
    className: className,
    xmlns: "http://www.w3.org/2000/svg",
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: strokeWidth,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    style: merged,
    "aria-hidden": "true"
  }, rest), node.map((child, i) => {
    const [tag, attrs] = child;
    return React.createElement(tag, {
      key: i,
      ...camelizeAttrs(attrs)
    });
  }));
}
function resolveIconNode(name) {
  const L = typeof window !== 'undefined' ? window.lucide : null;
  if (!L) return null;
  const icons = L.icons || L;
  const pascal = String(name).split(/[-_\s]/).filter(Boolean).map(s => s[0].toUpperCase() + s.slice(1)).join('');
  const node = icons[name] || icons[pascal];
  if (!node) return null;
  // lucide UMD nodes are ["svg", attrs, [[tag, attrs], …]] — return the children.
  if (Array.isArray(node)) {
    if (node[0] === 'svg' && Array.isArray(node[2])) return node[2];
    return node; // already a children array
  }
  if (node.iconNode && Array.isArray(node.iconNode)) return node.iconNode;
  return null;
}
const ATTR_MAP = {
  'stroke-width': 'strokeWidth',
  'stroke-linecap': 'strokeLinecap',
  'stroke-linejoin': 'strokeLinejoin',
  'fill-rule': 'fillRule',
  'clip-rule': 'clipRule'
};
function camelizeAttrs(attrs) {
  if (!attrs) return {};
  const out = {};
  for (const k in attrs) out[ATTR_MAP[k] || k] = attrs[k];
  return out;
}
Object.assign(__ds_scope, { Icon });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Icon.jsx", error: String((e && e.message) || e) }); }

// components/buttons/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Button — the brand's flat button. Two visual modes that share identical
 * radius + padding so a ghost tab's hover/active shape lines up with a solid one.
 *
 *  variant="solid"  → filled brand block, white text (active tabs, CTAs).
 *  variant="ghost"  → transparent, text only; hover fills with bg-base.
 *
 * No shadows, no translateY, no opacity tricks on press — interaction is a flat
 * color swap only (solid → darker brand on hover).
 */
function Button({
  children,
  variant = 'solid',
  size = 'md',
  active = false,
  accent = false,
  block = false,
  iconLeft,
  iconRight,
  disabled = false,
  type = 'button',
  className = '',
  style = {},
  onClick,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  const sizes = {
    sm: {
      padding: '6px 16px',
      font: 'var(--fs-label)',
      icon: 16,
      gap: 6
    },
    md: {
      padding: '8px 20px',
      font: 'var(--fs-label)',
      icon: 18,
      gap: 8
    },
    lg: {
      padding: '12px 28px',
      font: 'var(--fs-body)',
      icon: 20,
      gap: 8
    }
  };
  const s = sizes[size] || sizes.md;
  const base = accent ? 'var(--color-accent)' : 'var(--color-primary)';
  const baseHover = accent ? 'var(--color-accent-strong)' : 'var(--color-primary-strong)';
  const isSolid = variant === 'solid' || active;
  let bg, color, border;
  if (disabled) {
    bg = 'var(--color-disabled-bg)';
    color = 'var(--color-disabled-text)';
    border = '1px solid transparent';
  } else if (isSolid) {
    bg = hover ? baseHover : base;
    color = '#FFFFFF';
    border = '1px solid transparent';
  } else {
    bg = hover ? 'var(--color-bg-base)' : 'transparent';
    color = hover ? 'var(--color-primary)' : 'var(--color-text-main)';
    border = '1px solid transparent';
  }
  return /*#__PURE__*/React.createElement("button", _extends({
    type: type,
    disabled: disabled,
    onClick: onClick,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    className: className,
    style: {
      display: block ? 'flex' : 'inline-flex',
      width: block ? '100%' : undefined,
      alignItems: 'center',
      justifyContent: 'center',
      gap: s.gap,
      padding: s.padding,
      font: 'inherit',
      fontSize: s.font,
      fontWeight: 'var(--fw-medium)',
      lineHeight: 1.2,
      color,
      background: bg,
      border,
      borderRadius: 'var(--radius-md)',
      cursor: disabled ? 'not-allowed' : 'pointer',
      transition: 'var(--transition-base)',
      whiteSpace: 'nowrap',
      ...style
    }
  }, rest), iconLeft && /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: iconLeft,
    size: s.icon
  }), children, iconRight && /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: iconRight,
    size: s.icon
  }));
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/buttons/Button.jsx", error: String((e && e.message) || e) }); }

// components/buttons/Dropdown.jsx
try { (() => {
/**
 * Dropdown — sort/select trigger + flat panel, implementing the brand's
 * "open-to-activate" state machine:
 *  - The trigger turns into a solid primary block the MOMENT the panel opens
 *    (active = isOpen OR value-in-group), not only after a child is chosen.
 *  - Closing without choosing reverts (value is untouched here).
 *  - Reversed-text guard: while active, label + chevron stay white #FFFFFF even
 *    if open — never primary-on-primary invisible text.
 * Panel has a 1px border and NO shadow. Active item gets a primary "•" dot.
 */
function Dropdown({
  options = [],
  value,
  onChange,
  placeholder = '選項',
  width = 128,
  onOpenChange,
  className = '',
  style = {}
}) {
  const [open, setOpen] = React.useState(false);
  const [hoverTrigger, setHoverTrigger] = React.useState(false);
  const ref = React.useRef(null);
  React.useEffect(() => {
    if (!open) return;
    const onDoc = e => {
      if (ref.current && !ref.current.contains(e.target)) toggle(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);
  const toggle = next => {
    const v = typeof next === 'boolean' ? next : !open;
    setOpen(v);
    onOpenChange && onOpenChange(v);
  };
  const selected = options.find(o => o.id === value);
  const active = open || !!selected;
  const label = selected ? selected.label : placeholder;
  return /*#__PURE__*/React.createElement("div", {
    ref: ref,
    className: className,
    style: {
      position: 'relative',
      display: 'inline-block',
      ...style
    }
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: () => toggle(),
    onMouseEnter: () => setHoverTrigger(true),
    onMouseLeave: () => setHoverTrigger(false),
    style: {
      width,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 8,
      padding: '8px 16px',
      fontSize: 'var(--fs-label)',
      fontWeight: 'var(--fw-medium)',
      lineHeight: 1.2,
      // reversed-text guard wins: white when active regardless of open
      color: active ? '#FFFFFF' : 'var(--color-text-main)',
      background: active ? hoverTrigger ? 'var(--color-primary-strong)' : 'var(--color-primary)' : hoverTrigger ? 'var(--color-bg-base)' : 'var(--color-bg-surface)',
      border: active ? '1px solid var(--color-primary)' : 'var(--border-hairline)',
      borderRadius: 'var(--radius-md)',
      cursor: 'pointer',
      transition: 'var(--transition-base)',
      whiteSpace: 'nowrap'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      overflow: 'hidden',
      textOverflow: 'ellipsis'
    }
  }, label), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "chevron-down",
    size: 16,
    style: {
      color: active ? '#FFFFFF' : 'var(--color-text-muted)',
      transition: 'var(--transition-base)'
    }
  })), open && /*#__PURE__*/React.createElement("div", {
    role: "listbox",
    style: {
      position: 'absolute',
      top: 'calc(100% + 6px)',
      left: 0,
      minWidth: '100%',
      background: 'var(--color-bg-surface)',
      border: 'var(--border-hairline)',
      borderRadius: 'var(--radius-md)',
      padding: '4px',
      zIndex: 40,
      maxHeight: 320,
      overflowY: 'auto'
    }
  }, options.map(o => /*#__PURE__*/React.createElement(DropdownItem, {
    key: o.id,
    option: o,
    active: o.id === value,
    onSelect: () => {
      onChange && onChange(o.id);
      toggle(false);
    }
  }))));
}
function DropdownItem({
  option,
  active,
  onSelect
}) {
  const [hover, setHover] = React.useState(false);
  return /*#__PURE__*/React.createElement("button", {
    type: "button",
    role: "option",
    "aria-selected": active,
    onClick: onSelect,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      width: '100%',
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      padding: '8px 12px',
      textAlign: 'left',
      fontSize: 'var(--fs-label)',
      fontWeight: active ? 'var(--fw-medium)' : 'var(--fw-regular)',
      color: active ? 'var(--color-primary)' : 'var(--color-text-main)',
      background: hover ? 'var(--color-bg-base)' : 'transparent',
      border: 'none',
      borderRadius: 'var(--radius-sm)',
      cursor: 'pointer',
      transition: 'var(--transition-base)',
      whiteSpace: 'nowrap'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 6,
      height: 6,
      borderRadius: 'var(--radius-full)',
      background: active ? 'var(--color-primary)' : 'transparent',
      flexShrink: 0
    }
  }), option.label);
}
Object.assign(__ds_scope, { Dropdown });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/buttons/Dropdown.jsx", error: String((e && e.message) || e) }); }

// components/buttons/IconButton.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * IconButton — icon-only action button.
 *  variant="ghost"    → no border/fill; hover darkens icon to brand (cart, toolbar).
 *  variant="circular" → translucent white circle (carousel arrows); hover deepens bg.
 *  variant="solid"    → filled brand circle/block.
 * No Z-axis lift or shadow on hover — color change only.
 */
function IconButton({
  icon,
  label,
  variant = 'ghost',
  size = 40,
  iconSize,
  disabled = false,
  className = '',
  style = {},
  onClick,
  children,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  const isCircle = variant === 'circular' || variant === 'solid';
  let bg = 'transparent';
  let color = 'var(--color-text-main)';
  if (disabled) {
    color = 'var(--color-disabled-text)';
  } else if (variant === 'circular') {
    bg = hover ? 'rgba(255,255,255,0.95)' : 'rgba(255,255,255,0.8)';
  } else if (variant === 'solid') {
    bg = hover ? 'var(--color-primary-strong)' : 'var(--color-primary)';
    color = '#FFFFFF';
  } else if (hover) {
    color = 'var(--color-primary)';
  }
  return /*#__PURE__*/React.createElement("button", _extends({
    type: "button",
    "aria-label": label,
    title: label,
    disabled: disabled,
    onClick: onClick,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    className: className,
    style: {
      position: 'relative',
      width: size,
      height: size,
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: bg,
      color,
      border: 'none',
      borderRadius: isCircle ? 'var(--radius-full)' : 'var(--radius-md)',
      cursor: disabled ? 'not-allowed' : 'pointer',
      transition: 'var(--transition-base)',
      padding: 0,
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: iconSize || Math.round(size * 0.55)
  }), children);
}
Object.assign(__ds_scope, { IconButton });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/buttons/IconButton.jsx", error: String((e && e.message) || e) }); }

// components/core/Avatar.jsx
try { (() => {
/**
 * Avatar — circular, WHITE background with brand-primary text/icon.
 * Strict rule: never use accent/grey as the avatar fill. No shadow.
 * Pass `initials`, `name` (first char used), or `icon` (Lucide name).
 */
function Avatar({
  initials,
  name,
  icon = 'user',
  size = 24,
  bordered = true,
  className = '',
  style = {}
}) {
  const label = initials || (name ? name.trim().charAt(0) : null);
  const fontSize = Math.max(10, Math.round(size * 0.42));
  return /*#__PURE__*/React.createElement("span", {
    className: className,
    style: {
      width: size,
      height: size,
      borderRadius: 'var(--radius-full)',
      background: 'var(--color-bg-surface)',
      color: 'var(--color-primary)',
      border: bordered ? 'var(--border-hairline)' : 'none',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontWeight: 'var(--fw-medium)',
      fontSize,
      lineHeight: 1,
      overflow: 'hidden',
      transition: 'var(--transition-base)',
      ...style
    },
    "aria-label": name || initials || 'user'
  }, label ? label.toUpperCase() : /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: Math.round(size * 0.62)
  }));
}
Object.assign(__ds_scope, { Avatar });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Avatar.jsx", error: String((e && e.message) || e) }); }

// components/core/Skeleton.jsx
try { (() => {
/**
 * Skeleton — flat grey placeholder (#F3F4F6) with a gentle opacity pulse.
 * NO shimmer, NO gradient, NO shadow. Match the radius/ratio of the real
 * content it stands in for so layout doesn't jump (CLS).
 */
function Skeleton({
  width = '100%',
  height,
  radius = 'md',
  ratio,
  circle = false,
  className = '',
  style = {}
}) {
  const radiusMap = {
    sm: 'var(--radius-sm)',
    md: 'var(--radius-md)',
    lg: 'var(--radius-lg)',
    full: 'var(--radius-full)',
    none: '0'
  };
  const r = circle ? 'var(--radius-full)' : radiusMap[radius] ?? radius;
  return /*#__PURE__*/React.createElement("div", {
    "aria-hidden": "true",
    className: className,
    style: {
      width: typeof width === 'number' ? `${width}px` : width,
      height: height != null ? typeof height === 'number' ? `${height}px` : height : undefined,
      aspectRatio: ratio,
      borderRadius: r,
      background: 'var(--color-skeleton)',
      animation: 'wg-pulse 1.6s ease-in-out infinite',
      ...style
    }
  });
}
Object.assign(__ds_scope, { Skeleton });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Skeleton.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Badge.jsx
try { (() => {
/**
 * Badge — small count indicator (cart, notifications). Accent fill, white text,
 * 10–12px. `floating` absolutely positions it over a trigger (cart icon) at the
 * top-right, nudging onto the handle, never the basket body. Multi-digit values
 * stretch into a pill (px padding) instead of bloating into a big circle.
 */
function Badge({
  count,
  max = 99,
  floating = false,
  color = 'var(--color-accent)',
  className = '',
  style = {},
  children
}) {
  const display = children != null ? children : typeof count === 'number' && count > max ? `${max}+` : count;
  const multi = String(display ?? '').length > 1;
  return /*#__PURE__*/React.createElement("span", {
    className: className,
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      minWidth: 18,
      height: 18,
      padding: multi ? '0 6px' : 0,
      fontSize: 'var(--fs-caption)',
      fontWeight: 'var(--fw-medium)',
      lineHeight: 1,
      color: '#FFFFFF',
      background: color,
      borderRadius: 'var(--radius-full)',
      border: floating ? '2px solid var(--color-header-bg)' : 'none',
      ...(floating ? {
        position: 'absolute',
        top: -4,
        right: -8
      } : {}),
      ...style
    }
  }, display);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Badge.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Tag.jsx
try { (() => {
/**
 * Tag — flat label chips. Variants map 1:1 to the spec:
 *  - promo        : solid accent block, white text (discount / TOP rank). Top-left overlay.
 *  - logistics    : solid tertiary, dark text (1st logistics tag, e.g. 免運). Bottom-left.
 *  - logistics-alt: solid secondary, white text (2nd logistics tag).
 *  - feature      : outline (transparent + 1px border, primary), e.g. 可客製.
 *  - rating       : light bg, warning star + muted text (★ 5.0 / 已售出 33).
 * NO gradients, NO shadow. Overlay tags are clean solid blocks (no dark mask).
 */
function Tag({
  variant = 'feature',
  children,
  icon,
  className = '',
  style = {}
}) {
  const base = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    fontSize: 'var(--fs-caption)',
    fontWeight: 'var(--fw-medium)',
    lineHeight: 1,
    padding: '4px 8px',
    borderRadius: 'var(--radius-sm)',
    whiteSpace: 'nowrap'
  };
  const variants = {
    promo: {
      background: 'var(--color-accent)',
      color: '#FFFFFF'
    },
    logistics: {
      background: 'var(--color-tertiary)',
      color: 'var(--color-text-main)'
    },
    'logistics-alt': {
      background: 'var(--color-secondary)',
      color: '#FFFFFF'
    },
    feature: {
      background: 'transparent',
      color: 'var(--color-primary)',
      border: '1px solid var(--color-primary)',
      fontWeight: 'var(--fw-regular)'
    },
    rating: {
      background: 'var(--color-bg-base)',
      color: 'var(--color-text-muted)',
      fontWeight: 'var(--fw-regular)'
    }
  };
  return /*#__PURE__*/React.createElement("span", {
    className: className,
    style: {
      ...base,
      ...variants[variant],
      ...style
    }
  }, variant === 'rating' && /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "star",
    size: 13,
    color: "var(--color-warning)",
    strokeWidth: 2
  }), icon && variant !== 'rating' && /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: 13
  }), children);
}
Object.assign(__ds_scope, { Tag });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Tag.jsx", error: String((e && e.message) || e) }); }

// components/commerce/ProductCard.jsx
try { (() => {
/**
 * ProductCard — the storefront product tile. 1px border, white surface, 12px
 * radius. Image is 1:1 (or 3:4), object-cover, scales to 1.05 on card hover
 * (overflow hidden) — NO shadow, NO lift. Promo tag overlays top-left (accent);
 * logistics tags overlay bottom-left (tertiary, then secondary). Price is the
 * biggest/boldest text in primary green. Title clamps to 2 lines.
 *
 * `compact` = homepage variant: hides rating/feature tags, optional top-left
 * rank badge, and a bottom full-width info bar (e.g. monthly sales).
 */
function ProductCard({
  image,
  title,
  price,
  originalPrice,
  currency = 'NT$',
  promo,
  rank,
  logistics = [],
  features = [],
  rating,
  sold,
  ratio = '1 / 1',
  compact = false,
  infoBar,
  onClick,
  className = '',
  style = {}
}) {
  const [hover, setHover] = React.useState(false);
  const topLeft = compact ? rank : promo;
  return /*#__PURE__*/React.createElement("article", {
    onClick: onClick,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    className: className,
    style: {
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--color-bg-surface)',
      border: 'var(--border-hairline)',
      borderRadius: 'var(--radius-lg)',
      overflow: 'hidden',
      cursor: onClick ? 'pointer' : 'default',
      transition: 'var(--transition-base)',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      width: '100%',
      aspectRatio: ratio,
      overflow: 'hidden',
      background: 'var(--color-skeleton)'
    }
  }, image ? /*#__PURE__*/React.createElement("img", {
    src: image,
    alt: title,
    loading: "lazy",
    style: {
      width: '100%',
      height: '100%',
      objectFit: 'cover',
      display: 'block',
      transform: hover ? 'scale(1.05)' : 'scale(1)',
      transition: 'var(--transition-base)'
    }
  }) : /*#__PURE__*/React.createElement("div", {
    style: {
      width: '100%',
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: 'var(--color-disabled-text)'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "image",
    size: 40
  })), topLeft && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 8,
      left: 8
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Tag, {
    variant: "promo"
  }, topLeft)), !compact && logistics.length > 0 && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      bottom: 8,
      left: 8,
      display: 'flex',
      gap: 4
    }
  }, logistics.slice(0, 2).map((t, i) => /*#__PURE__*/React.createElement(__ds_scope.Tag, {
    key: i,
    variant: i === 0 ? 'logistics' : 'logistics-alt'
  }, t))), compact && infoBar && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 0,
      bottom: 0,
      width: '100%',
      padding: '6px 8px',
      textAlign: 'center',
      fontSize: 'var(--fs-caption)',
      color: '#FFFFFF',
      background: 'rgba(42,54,38,0.72)'
    }
  }, infoBar)), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
      padding: 16
    }
  }, /*#__PURE__*/React.createElement("h3", {
    style: {
      margin: 0,
      fontSize: 'var(--fs-body)',
      fontWeight: 'var(--fw-regular)',
      lineHeight: 1.4,
      color: 'var(--color-text-main)',
      display: '-webkit-box',
      WebkitLineClamp: 2,
      WebkitBoxOrient: 'vertical',
      overflow: 'hidden'
    }
  }, title), !compact && features.length > 0 && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: 4
    }
  }, features.map((f, i) => /*#__PURE__*/React.createElement(__ds_scope.Tag, {
    key: i,
    variant: "feature"
  }, f))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'baseline',
      gap: 6
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--fs-h4)',
      fontWeight: 'var(--fw-bold)',
      color: 'var(--color-primary)'
    }
  }, currency, formatPrice(price)), originalPrice != null && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--fs-caption)',
      color: 'var(--color-text-muted)',
      textDecoration: 'line-through'
    }
  }, currency, formatPrice(originalPrice))), !compact && (rating != null || sold != null) && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 6,
      fontSize: 'var(--fs-caption)',
      color: 'var(--color-text-muted)'
    }
  }, rating != null && /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 4
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "star",
    size: 13,
    color: "var(--color-warning)",
    strokeWidth: 2
  }), rating), rating != null && sold != null && /*#__PURE__*/React.createElement("span", {
    style: {
      opacity: 0.4
    }
  }, "|"), sold != null && /*#__PURE__*/React.createElement("span", null, "\u5DF2\u552E\u51FA ", sold))));
}
function formatPrice(n) {
  if (n == null) return '';
  return Number(n).toLocaleString('en-US');
}
Object.assign(__ds_scope, { ProductCard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/commerce/ProductCard.jsx", error: String((e && e.message) || e) }); }

// components/forms/Input.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Input — base text field. 8px radius, muted placeholder, smooth 0.2s state
 * transitions. Focus = 2px primary outline (no glow shadow). Error = solid
 * error border only (no red glow, no bg change). Disabled = disabled tokens.
 */
function Input({
  value,
  defaultValue,
  onChange,
  placeholder,
  type = 'text',
  error = false,
  disabled = false,
  block = true,
  className = '',
  style = {},
  ...rest
}) {
  const [focus, setFocus] = React.useState(false);
  let border = 'var(--border-hairline)';
  if (error) border = '1px solid var(--color-error)';
  return /*#__PURE__*/React.createElement("input", _extends({
    type: type,
    value: value,
    defaultValue: defaultValue,
    onChange: onChange,
    placeholder: placeholder,
    disabled: disabled,
    onFocus: () => setFocus(true),
    onBlur: () => setFocus(false),
    className: className,
    style: {
      width: block ? '100%' : undefined,
      minHeight: 44,
      padding: '10px 16px',
      fontFamily: 'inherit',
      fontSize: 'var(--fs-body)',
      color: disabled ? 'var(--color-disabled-text)' : 'var(--color-text-main)',
      background: disabled ? 'var(--color-disabled-bg)' : 'var(--color-bg-surface)',
      border,
      borderRadius: 'var(--radius-md)',
      outline: focus && !disabled ? 'var(--focus-ring)' : 'none',
      outlineOffset: 'var(--focus-offset)',
      cursor: disabled ? 'not-allowed' : 'text',
      transition: 'var(--transition-base)',
      ...style
    }
  }, rest));
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Input.jsx", error: String((e && e.message) || e) }); }

// components/forms/SearchBar.jsx
try { (() => {
/**
 * SearchBar — the large header search combo. White input that stretches
 * (flex-1), seamlessly fused to a wide solid-primary search button on the
 * right (h-full, inherits the container's right radius, white icon, NO margin
 * around the button). Single 8px-radius outer container.
 */
function SearchBar({
  value,
  onChange,
  onSearch,
  placeholder = '搜尋商品、品牌與店家',
  buttonLabel,
  maxWidth = 800,
  className = '',
  style = {}
}) {
  const [focus, setFocus] = React.useState(false);
  const [hoverBtn, setHoverBtn] = React.useState(false);
  const submit = () => onSearch && onSearch(value);
  return /*#__PURE__*/React.createElement("div", {
    className: className,
    style: {
      display: 'flex',
      alignItems: 'stretch',
      width: '100%',
      maxWidth,
      minHeight: 'var(--search-min-h)',
      background: 'var(--color-bg-surface)',
      border: focus ? '1px solid var(--color-primary)' : 'var(--border-hairline)',
      borderRadius: 'var(--radius-md)',
      overflow: 'hidden',
      transition: 'var(--transition-base)',
      ...style
    }
  }, /*#__PURE__*/React.createElement("input", {
    value: value,
    onChange: e => onChange && onChange(e.target.value),
    onKeyDown: e => e.key === 'Enter' && submit(),
    onFocus: () => setFocus(true),
    onBlur: () => setFocus(false),
    placeholder: placeholder,
    style: {
      flex: 1,
      minWidth: 0,
      border: 'none',
      outline: 'none',
      background: 'transparent',
      padding: '0 16px',
      fontFamily: 'inherit',
      fontSize: 'var(--fs-body)',
      color: 'var(--color-text-main)'
    }
  }), /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: submit,
    onMouseEnter: () => setHoverBtn(true),
    onMouseLeave: () => setHoverBtn(false),
    "aria-label": "\u641C\u5C0B",
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 8,
      padding: buttonLabel ? '0 28px' : '0 24px',
      minWidth: buttonLabel ? undefined : 80,
      height: 'auto',
      alignSelf: 'stretch',
      color: '#FFFFFF',
      background: hoverBtn ? 'var(--color-primary-strong)' : 'var(--color-primary)',
      border: 'none',
      cursor: 'pointer',
      fontSize: 'var(--fs-label)',
      fontWeight: 'var(--fw-medium)',
      transition: 'var(--transition-base)',
      whiteSpace: 'nowrap'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "search",
    size: 20
  }), buttonLabel));
}
Object.assign(__ds_scope, { SearchBar });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/SearchBar.jsx", error: String((e && e.message) || e) }); }

// components/navigation/Pagination.jsx
try { (() => {
/**
 * Pagination — the oversized bottom pager. 48×48 hit targets, 20–24px digits
 * at REGULAR/light weight (never bold), generous gap. Active = solid primary
 * block, white text, weight stays regular, radius 4–8px (never full round).
 * Inactive = borderless ghost, muted text. Arrows disable at the bounds.
 */
function Pagination({
  page = 1,
  totalPages = 1,
  siblings = 1,
  onChange,
  className = '',
  style = {}
}) {
  const go = p => {
    if (p < 1 || p > totalPages || p === page) return;
    onChange && onChange(p);
  };
  const items = buildRange(page, totalPages, siblings);
  return /*#__PURE__*/React.createElement("nav", {
    className: className,
    "aria-label": "\u5206\u9801\u5C0E\u89BD",
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 16,
      ...style
    }
  }, /*#__PURE__*/React.createElement(PageButton, {
    arrow: true,
    disabled: page <= 1,
    onClick: () => go(page - 1),
    label: "\u4E0A\u4E00\u9801"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "chevron-left",
    size: 22,
    strokeWidth: 1.5
  })), items.map((it, i) => it === '…' ? /*#__PURE__*/React.createElement("span", {
    key: `e${i}`,
    style: {
      width: 'var(--pagination-hit)',
      height: 'var(--pagination-hit)',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: 'var(--fs-pagination)',
      fontWeight: 'var(--fw-regular)',
      color: 'var(--color-text-muted)'
    }
  }, "\u2026") : /*#__PURE__*/React.createElement(PageButton, {
    key: it,
    active: it === page,
    onClick: () => go(it)
  }, it)), /*#__PURE__*/React.createElement(PageButton, {
    arrow: true,
    disabled: page >= totalPages,
    onClick: () => go(page + 1),
    label: "\u4E0B\u4E00\u9801"
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "chevron-right",
    size: 22,
    strokeWidth: 1.5
  })));
}
function PageButton({
  children,
  active = false,
  disabled = false,
  arrow = false,
  onClick,
  label
}) {
  const [hover, setHover] = React.useState(false);
  let bg = 'transparent';
  let color = 'var(--color-text-muted)';
  if (disabled) {
    color = 'var(--color-disabled-text)';
  } else if (active) {
    bg = 'var(--color-primary)';
    color = '#FFFFFF';
  } else if (hover) {
    bg = 'var(--color-bg-base)';
    color = 'var(--color-text-main)';
  }
  return /*#__PURE__*/React.createElement("button", {
    type: "button",
    "aria-label": label,
    "aria-current": active ? 'page' : undefined,
    disabled: disabled,
    onClick: onClick,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      width: 'var(--pagination-hit)',
      height: 'var(--pagination-hit)',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: arrow ? undefined : 'var(--fs-pagination)',
      fontWeight: 'var(--fw-regular)',
      color,
      background: bg,
      border: 'none',
      borderRadius: 'var(--radius-sm)',
      cursor: disabled ? 'not-allowed' : 'pointer',
      transition: 'var(--transition-base)',
      padding: 0
    }
  }, children);
}
function buildRange(page, total, siblings) {
  const range = [];
  const left = Math.max(2, page - siblings);
  const right = Math.min(total - 1, page + siblings);
  range.push(1);
  if (left > 2) range.push('…');
  for (let i = left; i <= right; i++) range.push(i);
  if (right < total - 1) range.push('…');
  if (total > 1) range.push(total);
  return range;
}
Object.assign(__ds_scope, { Pagination });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/Pagination.jsx", error: String((e && e.message) || e) }); }

// components/navigation/SidebarItem.jsx
try { (() => {
/**
 * SidebarItem — left category rail row. Flat, blends into the page (no card).
 * Active: tertiary backing + 4px primary left-anchor border + text stays dark.
 * Hover: tertiary fill only — no lift, no text shift, no shadow.
 * Children rows indent 16px; top-level rows are medium-weight.
 */
function SidebarItem({
  label,
  icon,
  active = false,
  level = 0,
  hasChildren = false,
  onClick,
  className = '',
  style = {}
}) {
  const [hover, setHover] = React.useState(false);
  const showFill = active || hover;
  return /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: onClick,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    className: className,
    style: {
      width: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 8,
      padding: '10px 12px',
      paddingLeft: level > 0 ? 12 + 16 * level : 12,
      textAlign: 'left',
      fontSize: 'var(--fs-body)',
      fontWeight: level === 0 ? 'var(--fw-medium)' : 'var(--fw-regular)',
      color: 'var(--color-text-main)',
      background: showFill ? 'var(--color-tertiary)' : 'transparent',
      border: 'none',
      borderLeft: `var(--sidebar-accent-width) solid ${active ? 'var(--color-primary)' : 'transparent'}`,
      borderRadius: 0,
      cursor: 'pointer',
      transition: 'var(--transition-base)',
      ...style
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 8,
      minWidth: 0
    }
  }, icon && /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: 18
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap'
    }
  }, label)), hasChildren && /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "chevron-right",
    size: 16,
    color: "var(--color-text-muted)"
  }));
}
Object.assign(__ds_scope, { SidebarItem });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/SidebarItem.jsx", error: String((e && e.message) || e) }); }

// ui_kits/storefront/App.jsx
try { (() => {
// App.jsx — composes the 意象若水 marketplace storefront and holds page state.
const WGa = window.WaterGreenDesignSystem_32a61f;
function sortProducts(list, sort) {
  const a = [...list];
  if (sort === 'price-asc') return a.sort((x, y) => x.price - y.price);
  if (sort === 'price-desc') return a.sort((x, y) => y.price - x.price);
  if (sort === 'hot') return a.sort((x, y) => (y.sold || 0) - (x.sold || 0));
  if (sort === 'newest') return a.slice().reverse();
  return a;
}
function App() {
  const [query, setQuery] = React.useState('');
  const [cart, setCart] = React.useState([]);
  const [cartOpen, setCartOpen] = React.useState(false);
  const [sort, setSort] = React.useState('overall');
  const [page, setPage] = React.useState(1);
  const [cat, setCat] = React.useState('all');
  const totalPages = 8;
  const products = React.useMemo(() => sortProducts(window.WG_DATA.products, sort), [sort]);
  const addToCart = p => {
    setCart(c => [p, ...c].slice(0, 8));
    setCartOpen(true);
  };
  return /*#__PURE__*/React.createElement("div", {
    style: {
      minHeight: '100vh',
      background: 'var(--color-bg-base)'
    }
  }, /*#__PURE__*/React.createElement(Header, {
    query: query,
    onQuery: setQuery,
    onSearch: () => {},
    cartItems: cart,
    cartOpen: cartOpen,
    onToggleCart: () => setCartOpen(o => !o)
  }), /*#__PURE__*/React.createElement("main", {
    style: {
      maxWidth: 'var(--container-max)',
      margin: '0 auto',
      padding: '32px 24px 0',
      display: 'flex',
      gap: 'var(--sidebar-gap)',
      alignItems: 'flex-start'
    }
  }, /*#__PURE__*/React.createElement(Sidebar, {
    active: cat,
    onSelect: setCat
  }), /*#__PURE__*/React.createElement("section", {
    style: {
      flex: 1,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement(Toolbar, {
    sort: sort,
    onSort: setSort,
    page: page,
    totalPages: totalPages,
    onPage: setPage
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 24
    }
  }, /*#__PURE__*/React.createElement(ProductGrid, {
    products: products,
    onAdd: addToCart
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 64
    }
  }, /*#__PURE__*/React.createElement(WGa.Pagination, {
    page: page,
    totalPages: totalPages,
    onChange: setPage
  })))), /*#__PURE__*/React.createElement(Footer, null), /*#__PURE__*/React.createElement(ChatFAB, {
    unread: true
  }));
}
ReactDOM.createRoot(document.getElementById('root')).render(/*#__PURE__*/React.createElement(App, null));
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/storefront/App.jsx", error: String((e && e.message) || e) }); }

// ui_kits/storefront/ChatFAB.jsx
try { (() => {
// ChatFAB.jsx — floating customer-chat button, bottom-right, primary fill,
// 8px radius (not pill), accent notification dot with white ring.
const WGc = window.WaterGreenDesignSystem_32a61f;
function ChatFAB({
  unread
}) {
  const [h, setH] = React.useState(false);
  return /*#__PURE__*/React.createElement("button", {
    type: "button",
    onMouseEnter: () => setH(true),
    onMouseLeave: () => setH(false),
    style: {
      position: 'fixed',
      right: 16,
      bottom: 32,
      zIndex: 70,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 8,
      padding: '10px 20px',
      fontSize: 'var(--fs-h5)',
      fontWeight: 'var(--fw-medium)',
      color: '#fff',
      background: h ? 'var(--color-primary-strong)' : 'var(--color-primary)',
      border: 'none',
      borderRadius: 'var(--radius-md)',
      cursor: 'pointer',
      transition: 'var(--transition-base)'
    }
  }, /*#__PURE__*/React.createElement(WGc.Icon, {
    name: "message-circle-more",
    size: 24
  }), "\u804A\u804A", unread && /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      top: -4,
      right: -4,
      width: 12,
      height: 12,
      background: 'var(--color-accent)',
      borderRadius: 'var(--radius-full)',
      border: '2px solid #fff'
    }
  }));
}
window.ChatFAB = ChatFAB;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/storefront/ChatFAB.jsx", error: String((e && e.message) || e) }); }

// ui_kits/storefront/Footer.jsx
try { (() => {
// Footer.jsx — global footer. Muted links, monochrome partner icons, 1px top border.
const WGf = window.WaterGreenDesignSystem_32a61f;
function FootLink({
  children
}) {
  const [h, setH] = React.useState(false);
  return /*#__PURE__*/React.createElement("a", {
    href: "#",
    onMouseEnter: () => setH(true),
    onMouseLeave: () => setH(false),
    style: {
      fontSize: 'var(--fs-label)',
      color: 'var(--color-text-muted)',
      textDecoration: h ? 'underline' : 'none',
      display: 'block',
      padding: '4px 0'
    }
  }, children);
}
function FootCol({
  title,
  links
}) {
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h5", {
    style: {
      fontSize: 'var(--fs-label)',
      fontWeight: 'var(--fw-semibold)',
      marginBottom: 12
    }
  }, title), links.map(l => /*#__PURE__*/React.createElement(FootLink, {
    key: l
  }, l)));
}
function Footer() {
  return /*#__PURE__*/React.createElement("footer", {
    style: {
      width: '100%',
      background: 'var(--color-bg-surface)',
      borderTop: 'var(--border-hairline)',
      marginTop: 48
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 'var(--footer-max)',
      margin: '0 auto',
      padding: '48px 16px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(4, 1fr)',
      gap: 32
    }
  }, /*#__PURE__*/React.createElement(FootCol, {
    title: "\u5BA2\u670D\u4E2D\u5FC3",
    links: ['幫助中心', '如何購買', '退換貨政策', '聯絡客服']
  }), /*#__PURE__*/React.createElement(FootCol, {
    title: "\u95DC\u65BC\u610F\u8C61\u82E5\u6C34",
    links: ['品牌故事', '加入我們', '隱私權政策', '服務條款']
  }), /*#__PURE__*/React.createElement(FootCol, {
    title: "\u4ED8\u6B3E\u65B9\u5F0F",
    links: ['信用卡', '貨到付款', '超商代碼', '行動支付']
  }), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h5", {
    style: {
      fontSize: 'var(--fs-label)',
      fontWeight: 'var(--fw-semibold)',
      marginBottom: 12
    }
  }, "\u95DC\u6CE8\u6211\u5011"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 16,
      color: 'var(--color-text-muted)'
    }
  }, /*#__PURE__*/React.createElement(WGf.Icon, {
    name: "facebook",
    size: 20
  }), /*#__PURE__*/React.createElement(WGf.Icon, {
    name: "instagram",
    size: 20
  }), /*#__PURE__*/React.createElement(WGf.Icon, {
    name: "message-circle",
    size: 20
  })))), /*#__PURE__*/React.createElement(WGf.Divider, {
    style: {
      margin: '32px 0 16px'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--fs-caption)',
      color: 'var(--color-text-muted)'
    }
  }, "\xA9 2026 \u610F\u8C61\u82E5\u6C34 water_green. \u5BE7\u975C\u4F46\u4E0D\u5931\u5546\u696D\u52D5\u80FD\u7684\u8CFC\u7269\u9AD4\u9A57\u3002")));
}
window.Footer = Footer;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/storefront/Footer.jsx", error: String((e && e.message) || e) }); }

// ui_kits/storefront/Header.jsx
try { (() => {
// Header.jsx — Topbar (announcement) + Main masthead + Cart preview panel.
// Sticky, full-module. Composes design-system primitives from the bundle.
const WG = window.WaterGreenDesignSystem_32a61f;
const {
  SearchBar,
  IconButton,
  Badge,
  Avatar,
  Divider,
  Icon,
  Button
} = WG;
function TopLink({
  icon,
  children
}) {
  const [h, setH] = React.useState(false);
  return /*#__PURE__*/React.createElement("button", {
    onMouseEnter: () => setH(true),
    onMouseLeave: () => setH(false),
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 4,
      background: 'none',
      border: 'none',
      color: 'var(--color-topbar-text)',
      cursor: 'pointer',
      fontSize: 'var(--fs-caption)',
      opacity: h ? 0.8 : 1,
      transition: 'var(--transition-base)',
      padding: 0
    }
  }, icon && /*#__PURE__*/React.createElement(Icon, {
    name: icon,
    size: 14
  }), children);
}
function Topbar() {
  const [h, setH] = React.useState(false);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--color-topbar-bg)',
      color: 'var(--color-topbar-text)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 'var(--container-max)',
      margin: '0 auto',
      padding: '0 24px',
      height: 'var(--topbar-height)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      fontSize: 'var(--fs-caption)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 12
    }
  }, /*#__PURE__*/React.createElement(TopLink, {
    icon: "store"
  }, "\u8CE3\u5BB6\u4E2D\u5FC3"), /*#__PURE__*/React.createElement(Divider, {
    orientation: "pipe"
  }), /*#__PURE__*/React.createElement(TopLink, {
    icon: "arrow-down-to-line"
  }, "\u4E0B\u8F09 App"), /*#__PURE__*/React.createElement(Divider, {
    orientation: "pipe"
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement(TopLink, {
    icon: "facebook"
  }), /*#__PURE__*/React.createElement(TopLink, {
    icon: "instagram"
  }), /*#__PURE__*/React.createElement(TopLink, {
    icon: "message-circle"
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 12
    }
  }, /*#__PURE__*/React.createElement(TopLink, {
    icon: "bell"
  }, "\u901A\u77E5"), /*#__PURE__*/React.createElement(Divider, {
    orientation: "pipe"
  }), /*#__PURE__*/React.createElement(TopLink, {
    icon: "circle-help"
  }, "\u5E6B\u52A9\u4E2D\u5FC3"), /*#__PURE__*/React.createElement(Divider, {
    orientation: "pipe"
  }), /*#__PURE__*/React.createElement("button", {
    onMouseEnter: () => setH(true),
    onMouseLeave: () => setH(false),
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 4,
      background: 'none',
      border: 'none',
      color: 'var(--color-topbar-text)',
      cursor: 'pointer',
      fontSize: 'var(--fs-caption)',
      opacity: h ? 0.8 : 1,
      transition: 'var(--transition-base)',
      padding: 0
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "globe",
    size: 14
  }), "\u7E41\u9AD4\u4E2D\u6587", /*#__PURE__*/React.createElement(Icon, {
    name: "chevron-down",
    size: 14
  })), /*#__PURE__*/React.createElement(Divider, {
    orientation: "pipe"
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6
    }
  }, /*#__PURE__*/React.createElement(Avatar, {
    name: "\u6703",
    size: 20
  }), /*#__PURE__*/React.createElement(TopLink, null, "\u767B\u5165 / \u8A3B\u518A")))));
}
function CartPanel({
  items,
  onClose
}) {
  const subtotal = items.reduce((s, i) => s + i.price, 0);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 'calc(100% + 12px)',
      right: 0,
      width: 360,
      zIndex: 60,
      background: 'var(--color-bg-surface)',
      border: 'var(--border-hairline)',
      borderRadius: 'var(--radius-md)',
      padding: 16
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: -7,
      right: 18,
      width: 12,
      height: 12,
      background: 'var(--color-bg-surface)',
      borderLeft: 'var(--border-hairline)',
      borderTop: 'var(--border-hairline)',
      transform: 'rotate(45deg)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--fs-label)',
      color: 'var(--color-text-muted)',
      marginBottom: 12
    }
  }, "\u6700\u8FD1\u52A0\u5165\u7684\u5546\u54C1"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      maxHeight: 280,
      overflowY: 'auto'
    }
  }, items.length === 0 ? /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: 'center',
      color: 'var(--color-text-muted)',
      padding: '32px 0',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "shopping-cart",
    size: 32
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--fs-label)'
    }
  }, "\u8CFC\u7269\u8ECA\u662F\u7A7A\u7684")) : items.map(it => /*#__PURE__*/React.createElement(CartRow, {
    key: it.id,
    item: it
  }))), items.length > 0 && /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 12
    }
  }, /*#__PURE__*/React.createElement(Divider, null), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'baseline',
      padding: '12px 0'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--fs-label)',
      color: 'var(--color-text-muted)'
    }
  }, "\u5C0F\u8A08"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--fs-h5)',
      fontWeight: 'var(--fw-bold)',
      color: 'var(--color-primary)'
    }
  }, "NT$", subtotal.toLocaleString())), /*#__PURE__*/React.createElement(Button, {
    block: true,
    onClick: onClose
  }, "\u67E5\u770B\u8CFC\u7269\u8ECA")));
}
function CartRow({
  item
}) {
  const [h, setH] = React.useState(false);
  return /*#__PURE__*/React.createElement("div", {
    onMouseEnter: () => setH(true),
    onMouseLeave: () => setH(false),
    style: {
      display: 'flex',
      gap: 12,
      padding: 8,
      borderRadius: 'var(--radius-md)',
      background: h ? 'var(--color-bg-base)' : 'transparent',
      transition: 'var(--transition-base)'
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: window.WG_IMG(item.seed),
    alt: "",
    style: {
      width: 48,
      height: 48,
      borderRadius: 'var(--radius-md)',
      objectFit: 'cover',
      flexShrink: 0
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--fs-label)',
      color: 'var(--color-text-main)',
      whiteSpace: 'nowrap',
      overflow: 'hidden',
      textOverflow: 'ellipsis'
    }
  }, item.title), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--fs-caption)',
      color: 'var(--color-text-muted)'
    }
  }, "x1")), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--fs-label)',
      color: 'var(--color-primary)',
      fontWeight: 'var(--fw-medium)'
    }
  }, "NT$", item.price));
}
function Header({
  query,
  onQuery,
  onSearch,
  cartItems,
  cartOpen,
  onToggleCart
}) {
  return /*#__PURE__*/React.createElement("header", {
    style: {
      position: 'sticky',
      top: 0,
      zIndex: 50
    }
  }, /*#__PURE__*/React.createElement(Topbar, null), /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--color-header-bg)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 'var(--container-max)',
      margin: '0 auto',
      padding: '16px 24px',
      display: 'flex',
      alignItems: 'center',
      gap: 32
    }
  }, /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      flex: '0 0 auto',
      display: 'flex',
      flexDirection: 'column',
      lineHeight: 1.1,
      textDecoration: 'none'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--fs-h3)',
      fontWeight: 'var(--fw-semibold)',
      letterSpacing: '.06em',
      color: '#fff'
    }
  }, "\u610F\u8C61\u82E5\u6C34"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--fs-caption)',
      letterSpacing: '.24em',
      color: 'rgba(255,255,255,.85)'
    }
  }, "water_green")), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 6
    }
  }, /*#__PURE__*/React.createElement(SearchBar, {
    value: query,
    onChange: onQuery,
    onSearch: onSearch
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexWrap: 'wrap',
      alignItems: 'center',
      height: 20,
      overflow: 'hidden',
      gap: '0 16px',
      width: '100%',
      maxWidth: 800,
      paddingLeft: 4
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--fs-caption)',
      color: '#fff',
      fontWeight: 'var(--fw-medium)'
    }
  }, "\u71B1\u641C"), window.WG_DATA.hotSearches.map(t => /*#__PURE__*/React.createElement("a", {
    key: t,
    href: "#",
    style: {
      fontSize: 'var(--fs-caption)',
      color: 'rgba(255,255,255,.8)'
    }
  }, t)))), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: '0 0 auto',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      position: 'relative'
    }
  }, /*#__PURE__*/React.createElement(IconButton, {
    icon: "shopping-cart",
    label: "\u8CFC\u7269\u8ECA",
    onClick: onToggleCart,
    style: {
      color: '#fff'
    }
  }, cartItems.length > 0 && /*#__PURE__*/React.createElement(Badge, {
    count: cartItems.length,
    floating: true
  })), cartOpen && /*#__PURE__*/React.createElement(CartPanel, {
    items: cartItems,
    onClose: onToggleCart
  })))));
}
window.Header = Header;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/storefront/Header.jsx", error: String((e && e.message) || e) }); }

// ui_kits/storefront/ProductGrid.jsx
try { (() => {
// ProductGrid.jsx — responsive 4-col grid of design-system ProductCards.
const WGg = window.WaterGreenDesignSystem_32a61f;
function ProductGrid({
  products,
  onAdd
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "wg-grid"
  }, products.map(p => /*#__PURE__*/React.createElement(WGg.ProductCard, {
    key: p.id,
    image: window.WG_IMG(p.seed),
    title: p.title,
    price: p.price,
    originalPrice: p.originalPrice,
    promo: p.promo,
    logistics: p.logistics,
    features: p.features,
    rating: p.rating,
    sold: p.sold,
    onClick: () => onAdd(p)
  })));
}
window.ProductGrid = ProductGrid;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/storefront/ProductGrid.jsx", error: String((e && e.message) || e) }); }

// ui_kits/storefront/Sidebar.jsx
try { (() => {
// Sidebar.jsx — left category rail. Transparent, blends into the page floor.
const WGs = window.WaterGreenDesignSystem_32a61f;
function Sidebar({
  active,
  onSelect
}) {
  const cats = window.WG_DATA.categories;
  const [expanded, setExpanded] = React.useState('home');
  return /*#__PURE__*/React.createElement("aside", {
    style: {
      width: 'var(--sidebar-width)',
      flex: 'none',
      background: 'transparent'
    }
  }, cats.map(c => /*#__PURE__*/React.createElement(React.Fragment, {
    key: c.id
  }, /*#__PURE__*/React.createElement(WGs.SidebarItem, {
    icon: c.icon,
    label: c.label,
    level: 0,
    active: active === c.id,
    hasChildren: c.hasChildren,
    onClick: () => {
      onSelect(c.id);
      if (c.hasChildren) setExpanded(expanded === c.id ? null : c.id);
    }
  }), c.children && expanded === c.id && c.children.map(s => /*#__PURE__*/React.createElement(WGs.SidebarItem, {
    key: s.id,
    label: s.label,
    level: 1,
    active: active === s.id,
    onClick: () => onSelect(s.id)
  })))));
}
window.Sidebar = Sidebar;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/storefront/Sidebar.jsx", error: String((e && e.message) || e) }); }

// ui_kits/storefront/Toolbar.jsx
try { (() => {
// Toolbar.jsx — sort + filter control bar (card) with single-source-of-truth
// sorting and the open-to-activate price dropdown, plus the right mini pager.
const WGt = window.WaterGreenDesignSystem_32a61f;
function SegButton({
  icon,
  disabled,
  onClick,
  side
}) {
  const [h, setH] = React.useState(false);
  return /*#__PURE__*/React.createElement("button", {
    type: "button",
    disabled: disabled,
    onClick: onClick,
    onMouseEnter: () => setH(true),
    onMouseLeave: () => setH(false),
    style: {
      width: 32,
      height: 32,
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: disabled ? 'var(--color-disabled-bg)' : h ? 'var(--color-bg-base)' : 'var(--color-bg-surface)',
      color: disabled ? 'var(--color-disabled-text)' : 'var(--color-text-main)',
      border: 'var(--border-hairline)',
      borderRight: side === 'left' ? 'none' : 'var(--border-hairline)',
      borderTopLeftRadius: side === 'left' ? 'var(--radius-md)' : 0,
      borderBottomLeftRadius: side === 'left' ? 'var(--radius-md)' : 0,
      borderTopRightRadius: side === 'right' ? 'var(--radius-md)' : 0,
      borderBottomRightRadius: side === 'right' ? 'var(--radius-md)' : 0,
      cursor: disabled ? 'not-allowed' : 'pointer',
      transition: 'var(--transition-base)',
      padding: 0
    }
  }, /*#__PURE__*/React.createElement(WGt.Icon, {
    name: icon,
    size: 16
  }));
}
function Toolbar({
  sort,
  onSort,
  page,
  totalPages,
  onPage
}) {
  const [priceOpen, setPriceOpen] = React.useState(false);
  const {
    sortTabs,
    priceOptions
  } = window.WG_DATA;
  const priceValue = String(sort).startsWith('price') ? sort : undefined;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      background: 'var(--color-bg-surface)',
      border: 'var(--border-hairline)',
      borderRadius: 'var(--radius-lg)',
      padding: '12px 12px 12px 20px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement(WGt.Button, {
    variant: "ghost",
    size: "sm",
    iconLeft: "sliders-horizontal"
  }, "\u7BE9\u9078"), /*#__PURE__*/React.createElement(WGt.Divider, {
    orientation: "vertical",
    height: 16,
    style: {
      margin: '0 8px'
    }
  }), sortTabs.map(t => /*#__PURE__*/React.createElement(WGt.Button, {
    key: t.id,
    size: "sm",
    variant: sort === t.id && !priceOpen ? 'solid' : 'ghost',
    active: sort === t.id && !priceOpen,
    onClick: () => onSort(t.id)
  }, t.label)), /*#__PURE__*/React.createElement(WGt.Dropdown, {
    placeholder: "\u50F9\u683C",
    width: 132,
    value: priceValue,
    onChange: onSort,
    onOpenChange: setPriceOpen,
    options: priceOptions
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      paddingRight: 8
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--fs-label)',
      color: 'var(--color-text-muted)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--color-primary)',
      fontWeight: 'var(--fw-medium)'
    }
  }, page), " / ", totalPages), /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex'
    }
  }, /*#__PURE__*/React.createElement(SegButton, {
    icon: "chevron-left",
    side: "left",
    disabled: page <= 1,
    onClick: () => onPage(page - 1)
  }), /*#__PURE__*/React.createElement(SegButton, {
    icon: "chevron-right",
    side: "right",
    disabled: page >= totalPages,
    onClick: () => onPage(page + 1)
  }))));
}
window.Toolbar = Toolbar;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/storefront/Toolbar.jsx", error: String((e && e.message) || e) }); }

// ui_kits/storefront/data.js
try { (() => {
// Storefront sample data for the 意象若水 marketplace UI kit.
// Product imagery uses picsum.photos placeholders (generic stock) — swap for
// real product photos in production.
window.WG_DATA = {
  categories: [{
    id: 'all',
    label: '所有分類',
    icon: 'layout-grid',
    top: true
  }, {
    id: 'home',
    label: '居家生活',
    hasChildren: true,
    children: [{
      id: 'storage',
      label: '收納用品'
    }, {
      id: 'kitchen',
      label: '廚房餐廚'
    }, {
      id: 'bath',
      label: '衛浴清潔'
    }]
  }, {
    id: 'beauty',
    label: '美妝保養',
    hasChildren: true
  }, {
    id: 'food',
    label: '食品飲料',
    hasChildren: true
  }, {
    id: 'apparel',
    label: '服飾配件',
    hasChildren: true
  }, {
    id: 'baby',
    label: '母嬰用品'
  }, {
    id: 'pet',
    label: '寵物天地'
  }, {
    id: 'sport',
    label: '運動戶外'
  }, {
    id: 'stationery',
    label: '文具書籍'
  }],
  hotSearches: ['保溫瓶', '收納盒', '香氛蠟燭', '有機棉', '玻璃罐', '木質托盤'],
  products: [{
    id: 1,
    title: '天然有機棉萬用收納籃 大容量耐重',
    price: 399,
    originalPrice: 499,
    promo: '-20%',
    logistics: ['店取免運', '隔日到貨'],
    features: ['可客製'],
    rating: 5.0,
    sold: 33,
    seed: 'wg-basket'
  }, {
    id: 2,
    title: '北歐風陶瓷馬克杯 啞光釉手感',
    price: 280,
    logistics: ['滿199免運'],
    features: ['多件優惠'],
    rating: 4.9,
    sold: 128,
    seed: 'wg-mug'
  }, {
    id: 3,
    title: '日式無印風玻璃保鮮盒三件組',
    price: 199,
    originalPrice: 259,
    promo: '-23%',
    logistics: ['店取免運'],
    features: ['新上架'],
    rating: 4.8,
    sold: 540,
    seed: 'wg-glass'
  }, {
    id: 4,
    title: '天然大豆香氛蠟燭 森林木質調',
    price: 360,
    logistics: ['隔日到貨'],
    rating: 5.0,
    sold: 76,
    seed: 'wg-candle'
  }, {
    id: 5,
    title: '原木餐桌托盤 防潑水實木',
    price: 580,
    originalPrice: 720,
    promo: '-19%',
    logistics: ['店取免運', '隔日到貨'],
    features: ['可客製'],
    rating: 4.7,
    sold: 42,
    seed: 'wg-tray'
  }, {
    id: 6,
    title: '簡約棉麻抱枕套 米杏色系',
    price: 150,
    logistics: ['滿199免運'],
    features: ['多件優惠'],
    rating: 4.9,
    sold: 312,
    seed: 'wg-pillow'
  }, {
    id: 7,
    title: '不鏽鋼真空保溫瓶 500ml',
    price: 690,
    originalPrice: 890,
    promo: '-22%',
    logistics: ['店取免運'],
    rating: 5.0,
    sold: 1024,
    seed: 'wg-bottle'
  }, {
    id: 8,
    title: '天然竹纖維洗碗布 五入組',
    price: 99,
    logistics: ['滿199免運'],
    features: ['新上架'],
    rating: 4.6,
    sold: 880,
    seed: 'wg-cloth'
  }, {
    id: 9,
    title: '霧面玻璃噴霧分裝瓶 旅行組',
    price: 220,
    logistics: ['隔日到貨'],
    features: ['多件優惠'],
    rating: 4.8,
    sold: 215,
    seed: 'wg-spray'
  }, {
    id: 10,
    title: '北歐陶瓷花瓶 啞光奶油白',
    price: 450,
    originalPrice: 560,
    promo: '-20%',
    logistics: ['店取免運'],
    rating: 4.9,
    sold: 67,
    seed: 'wg-vase'
  }, {
    id: 11,
    title: '純棉針織蓋毯 親膚柔軟',
    price: 780,
    logistics: ['店取免運', '隔日到貨'],
    features: ['可客製'],
    rating: 5.0,
    sold: 154,
    seed: 'wg-blanket'
  }, {
    id: 12,
    title: '木質香氛擴香竹 自然調',
    price: 320,
    logistics: ['滿199免運'],
    rating: 4.7,
    sold: 298,
    seed: 'wg-diffuser'
  }],
  sortTabs: [{
    id: 'overall',
    label: '綜合排名'
  }, {
    id: 'newest',
    label: '最新'
  }, {
    id: 'hot',
    label: '月銷熱賣'
  }],
  priceOptions: [{
    id: 'price-asc',
    label: '價格低到高'
  }, {
    id: 'price-desc',
    label: '價格高到低'
  }]
};
window.WG_IMG = seed => `https://picsum.photos/seed/${seed}/440/440`;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/storefront/data.js", error: String((e && e.message) || e) }); }

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Dropdown = __ds_scope.Dropdown;

__ds_ns.IconButton = __ds_scope.IconButton;

__ds_ns.ProductCard = __ds_scope.ProductCard;

__ds_ns.Avatar = __ds_scope.Avatar;

__ds_ns.Divider = __ds_scope.Divider;

__ds_ns.Icon = __ds_scope.Icon;

__ds_ns.Skeleton = __ds_scope.Skeleton;

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Tag = __ds_scope.Tag;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.SearchBar = __ds_scope.SearchBar;

__ds_ns.Pagination = __ds_scope.Pagination;

__ds_ns.SidebarItem = __ds_scope.SidebarItem;

})();
