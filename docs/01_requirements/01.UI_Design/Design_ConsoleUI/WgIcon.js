// WgIcon — self-contained global icon component (no fetch / no babel needed).
// Loaded via a plain <script src> so it works under file:// as well as http.
// 1) Renders Lucide line icons via the design-system Icon (window.lucide data).
// 2) Seeds window.lucide with embedded fallback icon data ONLY when the Lucide
//    CDN did not load (offline), so icons still render from a local file.
//    When the CDN is present, its real data is used untouched.
(function () {
  // Embedded Lucide node data (children arrays) for every glyph this console uses.
  // Format matches what the design-system Icon expects: [[tag, attrs], ...].
  var FALLBACK = {
    'bot': [['path',{d:'M12 8V4H8'}],['rect',{width:'16',height:'12',x:'4',y:'8',rx:'2'}],['path',{d:'M2 14h2'}],['path',{d:'M20 14h2'}],['path',{d:'M15 13v2'}],['path',{d:'M9 13v2'}]],
    'search': [['circle',{cx:'11',cy:'11',r:'8'}],['path',{d:'m21 21-4.3-4.3'}]],
    'bell': [['path',{d:'M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9'}],['path',{d:'M10.3 21a1.94 1.94 0 0 0 3.4 0'}]],
    'circle-help': [['circle',{cx:'12',cy:'12',r:'10'}],['path',{d:'M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3'}],['path',{d:'M12 17h.01'}]],
    'globe': [['circle',{cx:'12',cy:'12',r:'10'}],['path',{d:'M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20'}],['path',{d:'M2 12h20'}]],
    'clipboard-check': [['rect',{width:'8',height:'4',x:'8',y:'2',rx:'1',ry:'1'}],['path',{d:'M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2'}],['path',{d:'m9 14 2 2 4-4'}]],
    'layout-grid': [['rect',{width:'7',height:'7',x:'3',y:'3',rx:'1'}],['rect',{width:'7',height:'7',x:'14',y:'3',rx:'1'}],['rect',{width:'7',height:'7',x:'14',y:'14',rx:'1'}],['rect',{width:'7',height:'7',x:'3',y:'14',rx:'1'}]],
    'upload': [['path',{d:'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'}],['polyline',{points:'17 8 12 3 7 8'}],['line',{x1:'12',x2:'12',y1:'3',y2:'15'}]],
    'circle-check-big': [['path',{d:'M21.801 10A10 10 0 1 1 17 3.335'}],['path',{d:'m9 11 3 3L22 4'}]],
    'list-checks': [['path',{d:'m3 17 2 2 4-4'}],['path',{d:'m3 7 2 2 4-4'}],['path',{d:'M13 6h8'}],['path',{d:'M13 12h8'}],['path',{d:'M13 18h8'}]],
    'flame': [['path',{d:'M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z'}]],
    'folder': [['path',{d:'M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z'}]],
    'sliders-horizontal': [['line',{x1:'21',x2:'14',y1:'4',y2:'4'}],['line',{x1:'10',x2:'3',y1:'4',y2:'4'}],['line',{x1:'21',x2:'12',y1:'12',y2:'12'}],['line',{x1:'8',x2:'3',y1:'12',y2:'12'}],['line',{x1:'21',x2:'16',y1:'20',y2:'20'}],['line',{x1:'12',x2:'3',y1:'20',y2:'20'}],['line',{x1:'14',x2:'14',y1:'2',y2:'6'}],['line',{x1:'8',x2:'8',y1:'10',y2:'14'}],['line',{x1:'16',x2:'16',y1:'18',y2:'22'}]],
    'chevron-left': [['path',{d:'m15 18-6-6 6-6'}]],
    'chevron-right': [['path',{d:'m9 18 6-6-6-6'}]],
    'plus': [['path',{d:'M5 12h14'}],['path',{d:'M12 5v14'}]],
    'arrow-left': [['path',{d:'m12 19-7-7 7-7'}],['path',{d:'M19 12H5'}]],
    'target': [['circle',{cx:'12',cy:'12',r:'10'}],['circle',{cx:'12',cy:'12',r:'6'}],['circle',{cx:'12',cy:'12',r:'2'}]],
    'file-text': [['path',{d:'M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z'}],['path',{d:'M14 2v4a2 2 0 0 0 2 2h4'}],['path',{d:'M10 9H8'}],['path',{d:'M16 13H8'}],['path',{d:'M16 17H8'}]],
    'shield-alert': [['path',{d:'M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z'}],['path',{d:'M12 8v4'}],['path',{d:'M12 16h.01'}]],
    'check': [['path',{d:'M20 6 9 17l-5-5'}]],
    'check-circle': [['circle',{cx:'12',cy:'12',r:'10'}],['path',{d:'m9 12 2 2 4-4'}]],
    'play': [['polygon',{points:'6 3 20 12 6 21 6 3'}]],
    'pause': [['rect',{x:'14',y:'4',width:'4',height:'16',rx:'1'}],['rect',{x:'6',y:'4',width:'4',height:'16',rx:'1'}]],
    'square': [['rect',{width:'18',height:'18',x:'3',y:'3',rx:'2'}]],
    'history': [['path',{d:'M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8'}],['path',{d:'M3 3v5h5'}],['path',{d:'M12 7v5l4 2'}]],
    'activity': [['path',{d:'M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2'}]],
    'pencil': [['path',{d:'M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z'}],['path',{d:'m15 5 4 4'}]],
    'clock': [['circle',{cx:'12',cy:'12',r:'10'}],['polyline',{points:'12 6 12 12 16 14'}]],
    'repeat': [['path',{d:'m17 2 4 4-4 4'}],['path',{d:'M3 11v-1a4 4 0 0 1 4-4h14'}],['path',{d:'m7 22-4-4 4-4'}],['path',{d:'M21 13v1a4 4 0 0 1-4 4H3'}]],
    'rotate-ccw': [['path',{d:'M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8'}],['path',{d:'M3 3v5h5'}]],
    'upload-cloud': [['path',{d:'M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242'}],['path',{d:'M12 12v9'}],['path',{d:'m16 16-4-4-4 4'}]],
    'sparkles': [['path',{d:'M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .962 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.962 0z'}],['path',{d:'M20 3v4'}],['path',{d:'M22 5h-4'}],['path',{d:'M4 17v2'}],['path',{d:'M5 18H3'}]],
    'lock': [['rect',{width:'18',height:'11',x:'3',y:'11',rx:'2',ry:'2'}],['path',{d:'M7 11V7a5 5 0 0 1 10 0v4'}]],
    'alert-triangle': [['path',{d:'m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3'}],['path',{d:'M12 9v4'}],['path',{d:'M12 17h.01'}]],
    'settings': [['path',{d:'M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z'}],['circle',{cx:'12',cy:'12',r:'3'}]],
    'download': [['path',{d:'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'}],['polyline',{points:'7 10 12 15 17 10'}],['line',{x1:'12',x2:'12',y1:'15',y2:'3'}]],
    'plug': [['path',{d:'M12 22v-5'}],['path',{d:'M9 8V2'}],['path',{d:'M15 8V2'}],['path',{d:'M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z'}]],
    'x': [['path',{d:'M18 6 6 18'}],['path',{d:'m6 6 12 12'}]],
    'alert-circle': [['circle',{cx:'12',cy:'12',r:'10'}],['line',{x1:'12',x2:'12',y1:'8',y2:'12'}],['line',{x1:'12',x2:'12.01',y1:'16',y2:'16'}]]
  };

  if (typeof window !== 'undefined') {
    // Only seed if the Lucide CDN did NOT load (offline / file://). When the CDN
    // is present we leave its richer, authoritative data completely untouched.
    if (!window.lucide) {
      window.lucide = { icons: FALLBACK };
    } else if (!window.lucide.icons) {
      window.lucide.icons = FALLBACK;
    }
  }

  var ATTR_MAP = { 'stroke-width': 'strokeWidth', 'stroke-linecap': 'strokeLinecap', 'stroke-linejoin': 'strokeLinejoin', 'fill-rule': 'fillRule', 'clip-rule': 'clipRule' };
  function camelize(attrs) { var o = {}; for (var k in attrs) o[ATTR_MAP[k] || k] = attrs[k]; return o; }
  function resolveNode(name) {
    var L = (typeof window !== 'undefined') ? window.lucide : null;
    var icons = L ? (L.icons || L) : null;
    var node = null;
    if (icons) {
      var pascal = String(name).split(/[-_\s]/).filter(Boolean).map(function (s) { return s[0].toUpperCase() + s.slice(1); }).join('');
      node = icons[name] || icons[pascal];
    }
    if (!node) node = FALLBACK[name] || null;
    if (!node) return null;
    if (Array.isArray(node)) {
      if (node[0] === 'svg' && Array.isArray(node[2])) return node[2];
      return node;
    }
    if (node.iconNode && Array.isArray(node.iconNode)) return node.iconNode;
    return null;
  }

  function WgIcon(props) {
    var glyph = props.glyph, px = props.px, col = props.col, sw = props.sw;
    var size = px ? Number(px) : 20;
    var node = resolveNode(glyph);
    var style = { width: size, height: size, color: col || 'currentColor', display: 'inline-block', flexShrink: 0, verticalAlign: 'middle' };
    if (!node) return React.createElement('span', { style: style, 'aria-hidden': 'true' });
    return React.createElement('svg', {
      xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'none',
      stroke: 'currentColor', strokeWidth: sw ? Number(sw) : 1.5,
      strokeLinecap: 'round', strokeLinejoin: 'round', style: style, 'aria-hidden': 'true'
    }, node.map(function (child, i) {
      return React.createElement(child[0], Object.assign({ key: i }, camelize(child[1])));
    }));
  }

  if (typeof window !== 'undefined') window.WgIcon = WgIcon;
})();
