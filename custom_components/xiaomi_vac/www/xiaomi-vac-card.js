/**
 * Xiaomi Vac Card — "Atlas".
 * Map-forward, calm, native. Swipe between the vacuum image and the map(s);
 * persistent chrome (status/battery + vibrancy control tray). Infinite loop.
 *
 *   type: custom:xiaomi-vac-card
 *   vacuum: vacuum.kevin_jonas
 * Optional: map (camera), water/fan/activeMap (select), display toggles
 *
 * Map data comes from the integration's vector endpoint
 * (/api/xiaomi_vac/map/{entry_id}) — room polygons, walls, path, dock, etc.
 */

const ACCENT = {            // state-driven accent (information, not decoration)
  cleaning: "#30b65a", returning: "#e8973a", paused: "#e8973a",
  error: "#e2483d", docked: "#5b6470", idle: "#5b6470", unknown: "#5b6470",
};
// room fill palette (translucent so it reads on light or dark floors)
const ROOM_TINTS = [
  ["rgba(90,150,220,.30)", "rgba(90,150,220,.85)"],
  ["rgba(70,185,160,.30)", "rgba(70,185,160,.85)"],
  ["rgba(210,170,90,.32)", "rgba(210,170,90,.9)"],
  ["rgba(170,130,220,.30)", "rgba(170,130,220,.85)"],
  ["rgba(225,120,140,.30)", "rgba(225,120,140,.85)"],
  ["rgba(120,190,90,.30)", "rgba(120,190,90,.85)"],
];
const HTML_ESCAPES = {
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
};
const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : "");
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => HTML_ESCAPES[c]);
const roomIndexById = (rooms) => Object.fromEntries((rooms || []).map((r, i) => [r.id, i]));

// model short-form: "dreame.vacuum.mb1808" -> "dreame.mb1808" (strips the middle "vacuum" segment)
const modelShort = (m) => {
  if (!m) return "";
  const model = String(m);
  const p = model.split(".");
  return (p.length >= 3 && p[1] === "vacuum") ? p[0] + "." + p.slice(2).join(".") : model;
};
// shape 1 is the default fallback for unmapped models
const MODEL_SHAPE = Object.fromEntries([
  [1, ["dreame.mb1808","dreame.mc1808","xiaomi.ov21gl","xiaomi.ov42gl","xiaomi.ov43gb","dreame.md1808","dreame.p2008","dreame.p2140a","dreame.p2140o","dreame.p2140p","ijai.v10","ijai.v14"]],
  [2, ["dreame.p2029","dreame.p2028","dreame.p2028a","dreame.p2150b","dreame.p2150o"]],
  [3, ["ijai.v2","ijai.v3","xiaomi.c104","rockrobo.v1","xiaomi.d110ch","xiaomi.d103cn","xiaomi.d102gl","xiaomi.d102ev","xiaomi.d101","xiaomi.c107","xiaomi.c102gl","xiaomi.c102cn","xiaomi.c101eu","xiaomi.c101","dreame.p2114a","dreame.p2114o","dreame.r2210","dreame.r2209","dreame.r2211o","dreame.r2228","dreame.r2228o","dreame.r2228z","dreame.r2232a","dreame.r2233","dreame.r2246","dreame.r2247","dreame.r2254","dreame.s5"]],
  [4, ["ijai.v17","ijai.v18","ijai.v19","xiaomi.b106eu"]],
  [5, ["dreame.p2041","dreame.p2041o"]],
  [6, ["dreame.p2009","dreame.p2036"]],
  [7, ["dreame.p2157","dreame.p2259","dreame.p1250a"]],
  [8, ["ijai.v13","ijai.v1","viomi.v24"]],
  [9, ["dreame.p1248o"]],
  [10, ["xiaomi.d106gl","xiaomi.c103","xiaomi.b108gl"]],
  [11, ["viomi.v12","xiaomi.ov71gl","viomi.v13","xiaomi.b106bk","xiaomi.d109gl","dreame.r2215","dreame.r2216o","dreame.r2235"]],
  [12, ["xiaomi.b112","xiaomi.b112gl","xiaomi.c108","viomi.v45"]],
  [13, ["xiaomi.b112bk"]],
  [14, ["viomi.v19"]],
  [15, ["viomi.v40","viomi.v17","viomi.v38","viomi.v22","viomi.v15"]],
  [16, ["viomi.v35"]],
  [17, ["viomi.v23"]],
].flatMap(([shape, ids]) => ids.map((id) => [id, shape])));

const lottieSrc = (model, state) => {
  const shape = MODEL_SHAPE[modelShort(model)] || 1;
  const anim = { cleaning: "vacuuming", returning: "returning", paused: "paused" }[state] || "charging";
  return `/xiaomi-vac-card/lottie/shape-${shape}-${anim}.json`;
};
let _lottieP = null;
const _lottieData = {};
const loadLottie = () => {
  if (window.lottie) return Promise.resolve(window.lottie);
  return _lottieP || (_lottieP = new Promise((res) => {
    const s = document.createElement("script");
    s.src = "/xiaomi-vac-card/lottie.min.js";
    s.onload = () => res(window.lottie);
    s.onerror = () => { _lottieP = null; res(null); };
    document.head.appendChild(s);
  }));
};
const fetchLottie = (src) => {
  if (!_lottieData[src]) _lottieData[src] = fetch(src).then((r) => r.json()).catch(() => null);
  return _lottieData[src];
};
// "rgba(90,150,220,.30)" -> [r,g,b,a] for direct canvas pixel writes
const parseRGBA = (s) => {
  const n = (s.match(/[\d.]+/g) || []).map(Number);
  return [n[0] | 0, n[1] | 0, n[2] | 0, n[3] == null ? 1 : n[3]];
};

// Tray icons use HA's bundled MDI set via <ha-icon> so they render identically
// to native cards (the old hand-rolled SVGs were janky and inconsistent).
const MDI = {
  play: "mdi:play", pause: "mdi:pause", dock: "mdi:home-map-marker",
  locate: "mdi:map-marker-radius", fan: "mdi:fan", water: "mdi:water", map: "mdi:layers",
  tools: "mdi:tools",
};
// Consumable sensors created by sensor.py (translation_key/icon/label kept in
// sync with that file's XiaomiSensorDescription catalogue by hand — there is
// no shared source of truth between the Python and JS sides of this card).
const CONSUMABLES = [
  ["main_brush_life", "mdi:broom", "Main brush"],
  ["side_brush_life", "mdi:broom", "Side brush"],
  ["filter_life", "mdi:air-filter", "Filter"],
  ["dust_bag_life", "mdi:trash-can-outline", "Dust bag"],
  ["detergent_life", "mdi:cup-water", "Detergent"],
];
// `charging` overlays a bolt — docked-and-charging reads identically to
// docked-and-full otherwise (same grey accent, same fill bar).
const batteryIcon = (p, charging) =>
  `<svg viewBox="0 0 26 24"><rect x="1" y="6.5" width="20" height="11" rx="2.5" fill="none" stroke="currentColor" stroke-width="1.6"/><rect x="22.5" y="9.5" width="2" height="5" rx="1" fill="currentColor"/><rect x="3" y="8.5" width="${Math.max(0, 0.16 * p)}" height="7" rx="1" fill="currentColor"/>` +
  (charging ? `<path d="M12.4,7 L8.4,12.6 L11,12.6 L10.4,17 L14.4,11.2 L11.8,11.2 Z" fill="var(--xv-card)" stroke="currentColor" stroke-width="0.7" stroke-linejoin="round"/>` : "") +
  `</svg>`;
const vacuumFallbackSvg = () =>
  `<svg class="vac-fallback" viewBox="0 0 220 220" aria-hidden="true">
    <circle cx="110" cy="112" r="86" fill="none" stroke="currentColor" stroke-width="3"/>
    <path d="M24 111c8 3 15 8 19 15 10 41 37 70 67 70s57-29 67-70c4-7 11-12 19-15" fill="none" stroke="currentColor" stroke-width="7" stroke-linecap="round"/>
    <circle cx="110" cy="66" r="23" fill="var(--xv-card)" stroke="currentColor" stroke-width="3"/>
    <rect x="105" y="150" width="10" height="24" rx="5" fill="var(--xv-card)" stroke="currentColor" stroke-width="2"/>
    <path d="M47 102h126" stroke="currentColor" stroke-width="1.4" opacity=".25"/>
  </svg>`;
const TOGGLE_DEFAULTS = {
  show_vacuum_page: true,
  show_map: true,
  show_controls: true,
  show_fan: true,
  show_water: true,
  show_active_map: true,
  show_room_labels: true,
  allow_room_cleaning: true,
  show_consumables: true,
};

class XiaomiVacCard extends HTMLElement {
  static getConfigElement() { return document.createElement("xiaomi-vac-card-editor"); }
  static getStubConfig(hass) {
    const vac = Object.keys(hass.states).find((e) => e.startsWith("vacuum."));
    const map = Object.keys(hass.states).find((e) => e.startsWith("camera.") && e.endsWith("_map"));
    return { vacuum: vac || "vacuum.xiaomi_vac", ...(map ? { map } : {}) };
  }

  setConfig(config) {
    this._config = config || {};
    this._sel = new Set();        // selected room ids
    this._pendSel = {};           // optimistic select values, keyed by entity_id
    this._pendSelT = {};
    this._mapsData = [];          // list of map vectors from the endpoint
    this._pages = [];
    this._pos = 1; this._real = 0;
    this._fetchedFor = null;
    if (this._anim) { this._anim.destroy(); this._anim = null; }
    this._animWrap = null; this._animSrc = null;
    if (this._root) { this.innerHTML = ""; this._root = null; }
  }
  set hass(hass) {
    const prev = this._hass;
    this._hass = hass;
    if (!this._config) return;
    if (!this._root) this._build();
    if (this._hint) return;
    this._maybeFetch();
    // `hass` is replaced on EVERY state change anywhere in HA; only repaint when
    // an entity WE show actually changed (strict-equality per the frontend docs).
    if (prev && !this._relevantChanged(prev, hass)) return;
    try { this._update(); } catch (e) { console.error("[xiaomi-vac-card]", e); }
  }
  _relevantChanged(a, b) {
    const eids = [
      this._config.vacuum,
      `sensor.${this._base()}_battery`,
      this._config.water || `select.${this._base()}_water_level`,
      this._config.fan || `select.${this._base()}_fan_speed`,
      this._activeMapEid(),
      ...CONSUMABLES.map(([key]) => this._consumableEid(key)).filter(Boolean),
    ];
    return eids.some((e) => (a.states[e]) !== (b.states[e]));
  }
  // Auto-detected via the entity registry (device_id + translation_key) rather
  // than guessing an entity_id from the vacuum's object_id — the select's slug
  // isn't guaranteed to match the vacuum's (renamed device, id collision, etc).
  _activeMapEid() {
    if (this._config.activeMap) return this._config.activeMap;
    if (this._cachedMapEid && this._st(this._cachedMapEid)) return this._cachedMapEid;
    const ents = this._hass && this._hass.entities;
    const vacEnt = ents && ents[this._config.vacuum];
    const deviceId = vacEnt && vacEnt.device_id;
    if (ents && deviceId) {
      const found = Object.keys(ents).find((eid) =>
        eid.startsWith("select.") &&
        ents[eid].device_id === deviceId &&
        ents[eid].translation_key === "active_map");
      if (found) { this._cachedMapEid = found; return found; }
    }
    return `select.${this._base()}_active_map`;   // fallback if registry lookup misses
  }
  // Same registry-lookup pattern as _activeMapEid(): the consumable sensors'
  // entity_id can carry an area-name prefix HA auto-generates on first setup
  // (e.g. "sensor.nappali_julika_neni_main_brush_life"), so guessing from the
  // vacuum's own object_id would miss them — resolve by device_id + the
  // translation_key sensor.py assigns each one instead.
  _consumableEid(key) {
    this._consumEidCache = this._consumEidCache || {};
    if (this._consumEidCache[key] && this._st(this._consumEidCache[key])) return this._consumEidCache[key];
    const ents = this._hass && this._hass.entities;
    const vacEnt = ents && ents[this._config.vacuum];
    const deviceId = vacEnt && vacEnt.device_id;
    if (ents && deviceId) {
      const found = Object.keys(ents).find((eid) =>
        eid.startsWith("sensor.") &&
        ents[eid].device_id === deviceId &&
        ents[eid].translation_key === key);
      if (found) { this._consumEidCache[key] = found; return found; }
    }
    return null;
  }
  getCardSize() { return 10; }   // ~50px/unit; the card is a fixed 520px
  connectedCallback() {
    this._poll = setInterval(() => this._refreshMap(), 8000);
    // Pause polling while scrolled off-screen (a long dashboard mounts every
    // card at once); _refreshMap also guards on document visibility.
    if ("IntersectionObserver" in window) {
      this._io = new IntersectionObserver((es) => { this._onScreen = es.some((e) => e.isIntersecting); });
      this._io.observe(this);
    } else { this._onScreen = true; }
  }
  disconnectedCallback() {
    clearInterval(this._poll);
    if (this._io) { this._io.disconnect(); this._io = null; }
    if (this._ro) { this._ro.disconnect(); this._ro = null; }
    if (this._anim) { this._anim.destroy(); this._anim = null; }
  }

  _base() { return (this._config.vacuum || "").split(".")[1] || ""; }
  _st(eid) { return this._hass && this._hass.states[eid]; }
  _svc(d, s, data = {}) { this._hass.callService(d, s, data); }
  _enabled(name) { return this._config[name] !== false; }
  _mapOffset() { return this._enabled("show_vacuum_page") ? 1 : 0; }
  _entryId() {
    const eid = this._config.map || this._config.vacuum;
    const ent = this._hass && this._hass.entities && this._hass.entities[eid];
    return ent && ent.config_entry_id;
  }

  /* ---------------- data ---------------- */
  _maybeFetch() {
    const target = this._config.map || this._config.vacuum;
    if (this._fetchedFor === target) return;
    this._fetchedFor = target;
    this._refreshMap();
  }
  async _refreshMap() {
    if (!this._hass || !this._config.vacuum) return;
    if (!this._enabled("show_map")) return;
    // Don't poll the API for a tab in the background or a card scrolled out of
    // view. `_onScreen` is undefined until the observer first fires — treat that
    // as visible so the very first fetch isn't skipped.
    if (document.visibilityState === "hidden" || this._onScreen === false) return;
    // Resolve server-side from the entity_id (robust); fall back to entry_id.
    const target = this._entryId() || this._config.map || this._config.vacuum;
    try {
      const r = await this._hass.callApi("GET", `xiaomi_vac/map/${encodeURIComponent(target)}`);
      const maps = (r && Array.isArray(r.maps)) ? r.maps : [];
      const changed = JSON.stringify(maps) !== JSON.stringify(this._mapsData);
      this._mapsData = maps;
      if (changed) { this._rebuild(); this._update(); }
    } catch (e) {
      if (!this._warned) { this._warned = true; console.warn("[xiaomi-vac-card] map fetch failed:", e && e.message ? e.message : e); }
      if (this._mapsData.length) { this._mapsData = []; this._rebuild(); this._update(); }
    }
  }
  // Rebuilding the track resets the DOM; never do it mid-swipe (it would yank the
  // carousel). Defer to the next settle, and keep the user on their current page.
  _rebuild() {
    const track = this._root && this._root.querySelector(".track");
    if (this._down || (track && track.classList.contains("anim"))) { this._pendingRebuild = true; return; }
    this._buildPages(true);
  }

  /* ---------------- build shell ---------------- */
  _build() {
    this._root = document.createElement("ha-card");
    if (!this._config.vacuum) {
      this._hint = true;
      this._root.innerHTML =
        `<div style="padding:18px;color:var(--secondary-text-color);font-size:14px">` +
        `Set a <b style="color:var(--primary-text-color)">vacuum</b> entity in the card configuration.</div>`;
      this.appendChild(this._root);
      return;
    }
    this._hint = false;
    this._root.innerHTML = `
      <style>
        :host,ha-card{--xv-accent:${ACCENT.docked};
          --xv-card:var(--ha-card-background,var(--card-background-color,#fff));
          --xv-ink:var(--primary-text-color);--xv-muted:var(--secondary-text-color);
          --xv-floor:var(--secondary-background-color,#eef1f5);}
        ha-card{overflow:hidden;position:relative;height:520px;border-radius:var(--ha-card-border-radius,20px);container-type:inline-size}
        .vp{position:absolute;inset:0;overflow:hidden;touch-action:pan-y}
        .track{display:flex;height:100%;will-change:transform}
        .track.anim{transition:transform .34s cubic-bezier(.32,.72,0,1)}
        .slide{flex:0 0 100%;height:100%;position:relative;overflow:hidden}
        .topbar{position:absolute;top:0;left:0;right:0;z-index:5;display:flex;align-items:center;
          justify-content:space-between;padding:16px 18px;pointer-events:none;
          background:linear-gradient(180deg,var(--xv-card),transparent)}
        .status{display:flex;align-items:center;gap:8px;font-size:15px;font-weight:600;color:var(--xv-ink)}
        .dot{width:9px;height:9px;border-radius:50%;background:var(--xv-accent);
          box-shadow:0 0 0 4px color-mix(in srgb,var(--xv-accent) 18%,transparent);transition:background .3s}
        .batt{display:flex;align-items:center;gap:6px;font-size:14px;font-weight:500;color:var(--xv-ink)}
        .batt .btxt{line-height:1;transform:translateY(1px)}
        .batt .bicon{display:flex}
        .batt svg{width:23px;height:23px;display:block}
        .pg-img{display:flex;flex-direction:column;align-items:center;justify-content:center;
          background:radial-gradient(120% 90% at 50% 0%,var(--xv-card),var(--xv-floor))}
        .pg-img .stage{width:200px;height:200px;display:grid;place-items:center}
        .lottie-wrap{width:100%;height:100%;transform:scale(3);transform-origin:50% 38%}
        .lottie-wrap svg{display:block}
        .vac-fallback{width:100%;height:100%;color:color-mix(in srgb,var(--xv-muted) 55%,transparent);
          transform:scale(.333);transform-origin:50% 38%}
        .pg-img .nm{margin-top:20px;font-size:20px;font-weight:600;color:var(--xv-ink)}
        .pg-img .sub{margin-top:2px;font-size:13px;color:var(--xv-muted)}
        /* pad the map into the visible window so room polygons never draw under
           the status bar or the floating tray — the SVG scales to fit the inset */
        .pg-map{background:radial-gradient(120% 90% at 50% 0%,var(--xv-card),var(--xv-floor));
          box-sizing:border-box;padding:56px 14px 92px}
        .pg-map svg{width:100%;height:100%;display:block}
        .map-badge{position:absolute;top:64px;right:20px;z-index:4;background:var(--xv-accent);color:#fff;
          font-size:11px;font-weight:700;letter-spacing:.03em;text-transform:uppercase;padding:5px 10px;
          border-radius:9px;box-shadow:0 4px 12px color-mix(in srgb,var(--xv-accent) 40%,transparent);
          pointer-events:none}
        .rm{cursor:pointer;transition:stroke-width .12s}
        /* a mouse click triggers :focus (not :focus-visible), so the UA default
           outline paints a near-black ring hugging the path — kill it on tap */
        .rm:focus{outline:none}
        /* selection feedback is driven by the real selected state, not focus, so a
           mouse tap (no :focus-visible) still shows the room outlined in the accent */
        .rm[aria-pressed="true"]{stroke:var(--xv-accent)!important;stroke-width:0.2!important}
        /* keyboard focus ring (mouse taps never match :focus-visible) */
        .rm:focus-visible{outline:none;stroke:var(--xv-accent)!important;stroke-width:0.2!important}
        .dots{position:absolute;left:0;right:0;bottom:84px;z-index:6;display:flex;gap:7px;justify-content:center;pointer-events:none}
        .dots button{pointer-events:auto;padding:8px 3px;margin:-8px 0;border:0;background:none;cursor:pointer;display:flex;align-items:center}
        .dots i{width:6px;height:6px;border-radius:50%;background:color-mix(in srgb,var(--xv-ink) 25%,transparent);transition:.25s}
        .dots i.on{background:var(--xv-accent);width:18px;border-radius:3px}
        .dots button:focus-visible{outline:2px solid var(--xv-accent);outline-offset:3px;border-radius:6px}
        /* transient pill: fan/water level feedback (uniform tray has no inline labels) */
        .toast{position:absolute;left:50%;bottom:108px;z-index:6;transform:translateX(-50%) translateY(4px);
          background:var(--xv-ink);color:var(--xv-card);font-size:12px;font-weight:600;padding:7px 13px;border-radius:11px;
          opacity:0;transition:opacity .18s,transform .18s;pointer-events:none;white-space:nowrap;box-shadow:0 6px 18px rgba(0,0,0,.25)}
        .toast.show{opacity:.96;transform:translateX(-50%) translateY(-2px)}
        .roomtag{position:absolute;left:50%;bottom:108px;z-index:6;transform:translateX(-50%);
          background:var(--xv-accent);color:#fff;font-size:13px;font-weight:600;padding:10px 16px;border-radius:12px;
          box-shadow:0 6px 18px rgba(0,0,0,.25);opacity:0;transition:opacity .18s,transform .18s;
          pointer-events:none;white-space:nowrap;cursor:pointer;border:0}
        .roomtag.show{opacity:1;transform:translateX(-50%) translateY(-5px);pointer-events:auto}
        /* accessory-status panel: a collapsible sheet above the tray, toggled by
           the .act-consumables button — same frosted-glass treatment as .tray */
        .consum-panel{position:absolute;left:14px;right:14px;bottom:74px;z-index:8;
          background:color-mix(in srgb,var(--xv-card) 88%,transparent);
          backdrop-filter:blur(22px) saturate(180%);-webkit-backdrop-filter:blur(22px) saturate(180%);
          border:.5px solid color-mix(in srgb,var(--xv-ink) 8%,transparent);border-radius:16px;
          box-shadow:0 8px 30px rgba(0,0,0,.18);padding:0 14px;max-height:0;overflow:hidden;
          opacity:0;transform:translateY(6px);pointer-events:none;transition:opacity .18s,transform .18s,max-height .22s,padding .22s}
        .consum-panel.show{opacity:1;transform:translateY(0);pointer-events:auto;max-height:280px;overflow:auto;padding:8px 14px}
        .consum-row{display:flex;align-items:center;gap:10px;padding:7px 0}
        .consum-row+.consum-row{border-top:1px solid color-mix(in srgb,var(--xv-ink) 8%,transparent)}
        .consum-row ha-icon{--mdc-icon-size:20px;color:var(--xv-muted);flex:0 0 auto}
        .consum-row .cn{flex:1 1 auto;font-size:13px;color:var(--xv-ink);font-weight:500}
        .consum-row .cbar{width:56px;height:5px;border-radius:3px;
          background:color-mix(in srgb,var(--xv-ink) 10%,transparent);overflow:hidden;flex:0 0 auto}
        .consum-row .cbar i{display:block;height:100%;border-radius:3px}
        .consum-row .cpct{width:34px;text-align:right;font-size:12px;font-weight:600;color:var(--xv-muted);flex:0 0 auto}
        .act-consumables.on{background:var(--xv-accent);color:#fff}
        /* uniform segmented control (cf. the native climate card): every button
           equal width, the active action filled with the state accent */
        .tray{position:absolute;left:14px;right:14px;bottom:14px;z-index:7;
          background:color-mix(in srgb,var(--xv-card) 70%,transparent);
          backdrop-filter:blur(22px) saturate(180%);-webkit-backdrop-filter:blur(22px) saturate(180%);
          border:.5px solid color-mix(in srgb,var(--xv-ink) 8%,transparent);border-radius:18px;
          box-shadow:0 8px 30px rgba(0,0,0,.12);display:flex;align-items:stretch;gap:6px;padding:6px}
        .b{flex:1 1 0;min-width:0;height:48px;border-radius:12px;border:0;cursor:pointer;
          background:color-mix(in srgb,var(--xv-ink) 7%,transparent);color:var(--xv-ink);display:grid;place-items:center;
          transition:transform .08s ease,background .2s,color .2s,box-shadow .2s}
        .b:hover{background:color-mix(in srgb,var(--xv-ink) 13%,transparent)}
        .b:active{transform:scale(.94)}
        .b ha-icon{--mdc-icon-size:24px}
        .b.on{background:var(--xv-accent);color:#fff;
          box-shadow:0 4px 14px color-mix(in srgb,var(--xv-accent) 42%,transparent)}
        .b.on:hover{background:var(--xv-accent)}
        .b:focus-visible{outline:2px solid var(--xv-accent);outline-offset:2px}
        /* narrow cards: shrink uniformly, then drop water before things spill */
        @container (max-width:340px){ .tray{gap:5px;padding:5px} .b{height:44px} .b ha-icon{--mdc-icon-size:22px} }
        @container (max-width:240px){ .cyc-water{display:none} .act-consumables{display:none} }
        @media (prefers-reduced-motion:reduce){.track.anim{transition:none}.dot,.b{transition:none}
          .b:active{transform:none}}
      </style>
      <div class="vp" tabindex="0" role="group" aria-label="Vacuum and map — use left and right arrow keys to switch"><div class="track"></div></div>
      <div class="topbar">
        <div class="status"><span class="dot"></span><span class="stxt" aria-live="polite">—</span></div>
        <div class="batt"><span class="btxt">—</span><span class="bicon"></span></div>
      </div>
      <div class="dots"></div>
      <div class="toast"></div>
      <button class="roomtag"></button>
      <div class="consum-panel"></div>
      <div class="tray">
        <button class="b act-start" title="Start / pause" aria-label="Start or pause"><ha-icon icon="${MDI.play}"></ha-icon></button>
        <button class="b act-dock" title="Return to dock" aria-label="Return to dock"><ha-icon icon="${MDI.dock}"></ha-icon></button>
        <button class="b act-locate" title="Locate" aria-label="Locate vacuum"><ha-icon icon="${MDI.locate}"></ha-icon></button>
        <button class="b cyc-fan" title="Suction" aria-label="Cycle suction level"><ha-icon icon="${MDI.fan}"></ha-icon></button>
        <button class="b cyc-water" title="Water level" aria-label="Cycle water level"><ha-icon icon="${MDI.water}"></ha-icon></button>
        <button class="b cyc-map" title="Active map" aria-label="Cycle active map"><ha-icon icon="${MDI.map}"></ha-icon></button>
        <button class="b act-consumables" title="Accessories" aria-label="Show accessory status"><ha-icon icon="${MDI.tools}"></ha-icon></button>
      </div>`;
    this.appendChild(this._root);

    const q = (s) => this._root.querySelector(s);
    q(".act-start").onclick = () => {
      const st = this._st(this._config.vacuum);
      const cleaning = st && st.state === "cleaning";
      this._setPending(cleaning ? "paused" : "cleaning");
      this._svc("vacuum", cleaning ? "pause" : "start", { entity_id: this._config.vacuum });
    };
    q(".act-dock").onclick = () => {
      this._setPending("returning");
      this._svc("vacuum", "return_to_base", { entity_id: this._config.vacuum });
    };
    q(".act-locate").onclick = () => this._svc("vacuum", "locate", { entity_id: this._config.vacuum });
    q(".cyc-fan").onclick = () => this._cycleFan();
    q(".cyc-water").onclick = () =>
      this._cycleSelect(this._config.water || `select.${this._base()}_water_level`);
    q(".cyc-map").onclick = () => this._cycleSelect(this._activeMapEid());
    q(".roomtag").onclick = () => this._cleanSelected();
    q(".act-consumables").onclick = () => {
      q(".consum-panel").classList.toggle("show");
      q(".act-consumables").classList.toggle("on", q(".consum-panel").classList.contains("show"));
    };

    this._setupSwipe();
    this._buildPages();
  }

  /* ---------------- pages / carousel ---------------- */
  _maps() {
    // active map first, then any other floors the device reported
    return (this._mapsData || [])
      .filter((m) => m && m.rooms)
      .sort((a, b) => (b.active ? 1 : 0) - (a.active ? 1 : 0));
  }
  _buildPages(keep) {
    const vac = this._st(this._config.vacuum);
    const name = (vac && vac.attributes.friendly_name) || "Vacuum";
    const model = vac && vac.attributes.model;
    const imgPage = this._enabled("show_vacuum_page")
      ?
      `<div class="slide pg-img"><div class="stage"><div class="lottie-wrap">${vacuumFallbackSvg()}</div></div>` +
      `<div class="nm">${esc(name)}</div><div class="sub">${esc(model || "")}</div></div>`
      : "";
    const mapOffset = this._mapOffset();
    const mapPages = this._enabled("show_map")
      ? this._maps().map((m, i) =>
          `<div class="slide pg-map" data-mi="${i + mapOffset}">` +
          (m.active ? `<div class="map-badge">Active</div>` : "") +
          `${this._mapSVG(m)}</div>`)
      : [];
    this._pages = [...(imgPage ? [imgPage] : []), ...mapPages];

    const track = this._root.querySelector(".track");
    const N = this._pages.length;
    // on a live rebuild (map poll) keep the user on the page they were viewing
    const want = keep ? Math.min(Math.max(this._real | 0, 0), N - 1) : 0;
    if (N > 1) {
      // clone last+first onto the ends so the carousel loops seamlessly
      track.innerHTML = this._pages[N - 1] + this._pages.join("") + this._pages[0];
      this._pos = want + 1;
    } else {
      track.innerHTML = this._pages[0] || "";
      this._pos = 0;
    }
    this._real = N > 1 ? this._pos - 1 : 0;
    this._wirePage();
    this._renderDots();
    requestAnimationFrame(() => { this._w = this._root.querySelector(".vp").clientWidth; this._setX(false); });
  }
  _renderDots() {
    const dots = this._root.querySelector(".dots");
    const N = this._pages.length;
    dots.innerHTML = N > 1
      ? this._pages.map((_, i) =>
          `<button data-i="${i}" aria-label="${i === 0 ? "Vacuum" : "Map " + i}"${i === this._real ? ' aria-current="true"' : ""}><i class="${i === this._real ? "on" : ""}"></i></button>`).join("")
      : "";
    dots.querySelectorAll("button").forEach((b) => { b.onclick = () => this._goTo(Number(b.dataset.i)); });
  }
  // Jump straight to a real page (dots / future buttons). Ignored mid-flight so a
  // tap during the snap can't strand the track on a clone.
  _goTo(i) {
    const N = this._pages.length;
    if (N <= 1 || i === this._real) return;
    const track = this._root.querySelector(".track");
    if (track.classList.contains("anim") || this._down) return;
    this._pos = i + 1;
    this._setX(true);
  }
  _wirePage() {
    this._root.querySelectorAll(".rm").forEach((r) => {
      const toggle = () => {
        if (this._blockClick || !this._enabled("allow_room_cleaning")) return;
        const id = Number(r.dataset.id);
        this._sel.has(id) ? this._sel.delete(id) : this._sel.add(id);
        this._syncRooms();
      };
      r.onclick = toggle;
      r.onkeydown = (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); }
      };
    });
  }
  _setX(anim) {
    const track = this._root.querySelector(".track");
    track.classList.toggle("anim", !!anim);
    if (anim) void track.offsetWidth;        // commit the class so the transition runs
    track.style.transform = `translateX(${-this._pos * this._w}px)`;
  }
  _setupSwipe() {
    const vp = this._root.querySelector(".vp");
    const track = this._root.querySelector(".track");
    // Pointer Events (one stream for mouse + touch + pen) with pointer capture —
    // no global window listeners, and a drag can begin mid-animation.
    let down = false, sx = 0, sy = 0, base = 0, moved = false, vert = false, t0 = 0, pid = null;
    const TH = 8, COMMIT = 0.16, VEL = 0.45;
    const N = () => this._pages.length;
    const realPos = () => { const n = N(); return ((this._pos - 1) % n + n) % n + 1; };

    const onDown = (e) => {
      if (N() <= 1) return;
      if (e.pointerType === "mouse" && e.button !== 0) return;
      // Grabbing during the snap settles the in-flight swipe to a real slot first,
      // so we never start a drag from a clone (which would expose blank space).
      if (track.classList.contains("anim")) { track.classList.remove("anim"); this._pos = realPos(); }
      else if (this._pos === 0 || this._pos === N() + 1) this._pos = realPos();
      down = true; this._down = true; moved = false; vert = false; sx = e.clientX; sy = e.clientY; t0 = Date.now();
      base = -this._pos * this._w;
      track.style.transform = `translateX(${base}px)`;
      // Capture is DEFERRED until the gesture actually moves (see onMove). Capturing
      // on every press retargets the subsequent click to .vp, so a stationary tap
      // never reached the room path underneath and room selection silently failed.
      pid = e.pointerId;
    };
    const onMove = (e) => {
      if (!down) return;
      const dx = e.clientX - sx, dy = e.clientY - sy;
      if (!moved && !vert) {
        if (Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > TH) { vert = true; down = false; this._down = false; return; }
        if (Math.abs(dx) > TH) { moved = true; try { vp.setPointerCapture(pid); } catch (_) {} }
      }
      if (moved) { if (e.cancelable) e.preventDefault(); track.style.transform = `translateX(${base + dx}px)`; }
    };
    const onUp = (e) => {
      if (!down) return; down = false; this._down = false;
      if (pid != null) { try { vp.releasePointerCapture(pid); } catch (_) {} pid = null; }
      if (!moved) return;
      const dx = e.clientX - sx, dt = Date.now() - t0, v = Math.abs(dx) / Math.max(dt, 1);
      this._blockClick = true; clearTimeout(this._bcT); this._bcT = setTimeout(() => (this._blockClick = false), 300);
      if (Math.abs(dx) > this._w * COMMIT || v > VEL) this._pos += dx < 0 ? 1 : -1;
      this._setX(true);
    };

    vp.addEventListener("pointerdown", onDown);
    vp.addEventListener("pointermove", onMove);
    vp.addEventListener("pointerup", onUp);
    vp.addEventListener("pointercancel", onUp);
    // Keyboard paging — only when the viewport itself holds focus, so arrowing
    // through a focused room polygon isn't hijacked.
    vp.addEventListener("keydown", (e) => {
      if (N() <= 1 || e.target !== vp) return;
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      const track = this._root.querySelector(".track");
      if (track.classList.contains("anim") || down) return;
      e.preventDefault();
      this._pos += e.key === "ArrowRight" ? 1 : -1;
      this._setX(true);
    });

    track.addEventListener("transitionend", (e) => {
      if (e.propertyName && e.propertyName !== "transform") return;
      const n = N();
      if (this._pos <= 0) { track.classList.remove("anim"); this._pos = n; track.style.transform = `translateX(${-this._pos * this._w}px)`; }
      else if (this._pos >= n + 1) { track.classList.remove("anim"); this._pos = 1; track.style.transform = `translateX(${-this._pos * this._w}px)`; }
      else track.classList.remove("anim");
      this._real = ((this._pos - 1) % n + n) % n;
      this._sel.clear(); this._syncRooms(); this._renderDots();
      // a map refresh that arrived mid-gesture was deferred — apply it now
      if (this._pendingRebuild && !down) { this._pendingRebuild = false; this._buildPages(true); }
    });
    window.addEventListener("resize", () => { this._w = vp.clientWidth; if (!down) this._setX(false); });
    // window 'resize' misses layout changes that don't resize the window —
    // sections/masonry settling, sidebar toggle, the card's own width settling
    // after mount. Any of those leaves this._w stale, so the track under/over-
    // shifts and pages sit off-centre. Track the viewport's real width instead.
    if (this._ro) this._ro.disconnect();
    if ("ResizeObserver" in window) {
      this._ro = new ResizeObserver(() => {
        const w = vp.clientWidth;
        if (!w || w === this._w) return;     // ignore no-ops and hidden (0) states
        this._w = w;
        if (!down) this._setX(false);        // re-snap to the current page at the new width
      });
      this._ro.observe(vp);
    }
  }

  /* ---------------- room fill raster (the segment layer) ----------------
   * Rooms are painted as a pixel image from the labelled grid — exactly what
   * Valetudo does. One canvas pixel per grid cell, nearest-neighbour scaled, no
   * outline, no holes. A raster has no polygon, so it can't ever produce the
   * stray diagonal chords / pinch artefacts that vector tracing did. Selected
   * rooms paint in their saturated tint. Returns SVG <image> placement in metre
   * space, or null if the grid is unavailable (then _mapSVG falls back to vector
   * fills). */
  _roomRaster(m) {
    const g = m.grid_rle, sz = m.size, b = m.bounds, res = m.resolution || 0.05;
    if (!g || !sz || !b || typeof document === "undefined") return null;
    const W = sz.x, H = sz.y;
    if (!W || !H) return null;
    const grid = new Uint8Array(W * H);
    let pos = 0;
    for (let i = 0; i + 1 < g.length; i += 2) {
      const v = g[i], n = g[i + 1];
      grid.fill(v, pos, Math.min(pos + n, grid.length));
      pos += n;
    }
    const rooms = m.rooms || [];
    const idIndex = roomIndexById(rooms);
    const cv = document.createElement("canvas");
    cv.width = W; cv.height = H;
    const ctx = cv.getContext("2d");
    const img = ctx.createImageData(W, H), d = img.data;
    for (let row = 0; row < H; row++) {
      for (let col = 0; col < W; col++) {
        const v = grid[row * W + col];
        let lab = null;
        if (v >= 10 && v <= 59) lab = v;
        else if (v >= 60 && v <= 109) lab = v - 50;  // selected-room cell value
        if (lab == null) continue;
        const t = ROOM_TINTS[(idIndex[lab] ?? 0) % ROOM_TINTS.length];
        const [r, gg, bb, a] = parseRGBA(this._sel.has(lab) ? t[1] : t[0]);
        // grid row increases north (up); image row 0 is the top, so flip
        const o = ((H - 1 - row) * W + col) * 4;
        d[o] = r; d[o + 1] = gg; d[o + 2] = bb; d[o + 3] = Math.round(a * 255);
      }
    }
    ctx.putImageData(img, 0, 0);
    const Wm = W * res, Hm = H * res;
    return { href: cv.toDataURL(), x: b.minX, y: -(b.minY + Hm), w: Wm, h: Hm };
  }
  // Re-paint the active map's fill raster after a selection change (cheap; only
  // the visible page's <image> href is swapped).
  _refreshFill() {
    const m = this._maps()[this._real - this._mapOffset()];
    if (!m) return;
    const r = this._roomRaster(m);
    if (!r) return;
    this._root.querySelectorAll(`.pg-map[data-mi="${this._real}"] image.rmfill`)
      .forEach((im) => im.setAttribute("href", r.href));
  }

  /* ---------------- map svg (metre space, north up) ---------------- */
  _mapSVG(m) {
    const res = m.resolution || 0.05, b = m.bounds || { minX: 0, minY: 0 };
    const cell = (c) => [b.minX + c[0] * res, b.minY + c[1] * res]; // grid cell -> metre
    const chains = m.room_chains || [];
    const rooms = m.rooms || [];
    const idIndex = roomIndexById(rooms);
    // collect extents. Each room is one or more rings (exact grid-cell outlines,
    // in grid coords); a bbox rectangle is the fallback when there are no chains.
    let xs = [], ys = [];
    const polys = chains.length
      ? chains.map((ch) => ({ id: ch.id, rings: ch.rings.map((r) => r.map(cell)) }))
      : rooms.map((r) => ({ id: r.id, rings: [[[r.bbox[0], r.bbox[1]], [r.bbox[2], r.bbox[1]], [r.bbox[2], r.bbox[3]], [r.bbox[0], r.bbox[3]]]] }));
    polys.forEach((p) => p.rings.forEach((ring) => ring.forEach(([x, y]) => { xs.push(x); ys.push(y); })));
    if (m.charger) { xs.push(m.charger.x); ys.push(m.charger.y); }
    if (!xs.length) return "";
    const minx = Math.min(...xs), maxx = Math.max(...xs), miny = Math.min(...ys), maxy = Math.max(...ys);
    const PAD = 0.7;
    const vbx = minx - PAD, vby = -(maxy + PAD), vw = (maxx - minx) + 2 * PAD, vh = (maxy - miny) + 2 * PAD;
    const tx = (x) => x.toFixed(3), ty = (y) => (-y).toFixed(3);
    const ring = (pts) => "M" + pts.map(([x, y]) => `${tx(x)},${ty(y)}`).join("L") + "Z";
    const dpath = (rings) => rings.map(ring).join("");  // multi-ring → even-odd fill

    let s = `<svg viewBox="${vbx} ${vby} ${vw} ${vh}" preserveAspectRatio="xMidYMid meet">`;
    // Room fills: prefer the pixel raster (the segment layer). The traced paths
    // then carry no visible paint — they're just transparent tap/focus targets,
    // so any imperfect ring geometry never shows.
    const raster = this._roomRaster(m);
    if (raster) {
      s += `<image class="rmfill" href="${raster.href}" x="${raster.x}" y="${raster.y}" width="${raster.w}" height="${raster.h}" preserveAspectRatio="none" style="image-rendering:crisp-edges;image-rendering:pixelated"/>`;
    }
    polys.forEach((p) => {
      const t = ROOM_TINTS[(idIndex[p.id] ?? 0) % ROOM_TINTS.length];
      const nm = (rooms[idIndex[p.id]] && rooms[idIndex[p.id]].name) || `Room ${p.id}`;
      // raster present → transparent hit target; no raster → solid vector fill
      const fill = raster ? "transparent" : t[0];
      s += `<path class="rm" data-id="${p.id}" role="button" tabindex="0" aria-pressed="false" aria-label="Clean ${esc(nm)}" d="${dpath(p.rings)}" fill="${fill}" stroke="none"/>`;
    });
    // virtual walls — a user-drawn no-cross line, not real geometry, so render it
    // as a faint dashed hint rather than a solid bar that fights the rooms
    (m.walls || []).forEach((w) => {
      s += `<line x1="${tx(w[0])}" y1="${ty(w[1])}" x2="${tx(w[2])}" y2="${ty(w[3])}" stroke="var(--xv-muted)" stroke-width="0.05" stroke-linecap="round" stroke-dasharray="0.16 0.13" opacity=".35"/>`;
    });
    if (m.path && m.path.length > 1) {
      s += `<polyline points="${m.path.map(([x, y]) => `${tx(x)},${ty(y)}`).join(" ")}" fill="none" stroke="var(--xv-accent)" stroke-width="0.07" stroke-linecap="round" stroke-linejoin="round" opacity=".9"/>`;
    }
    if (this._enabled("show_room_labels")) rooms.forEach((r) => {
      if (r.cx == null || !r.name) return;
      // Full name, uppercased. Let it overflow the room rather than truncate —
      // text-anchor=middle keeps it centred so it spills evenly past the walls.
      const label = r.name.toUpperCase();
      s += `<text x="${tx(r.cx)}" y="${ty(r.cy)}" font-size="0.42" fill="var(--xv-ink)" font-weight="600" text-anchor="middle" dominant-baseline="middle" style="pointer-events:none">${esc(label)}</text>`;
    });
    if (m.charger) {
      s += `<g transform="translate(${tx(m.charger.x)},${ty(m.charger.y)})"><circle r="0.32" fill="var(--xv-card)" stroke="#30b65a" stroke-width="0.07"/><path d="M-0.15,0.04 L0,-0.13 L0.15,0.04 M-0.09,0.02 L-0.09,0.15 L0.09,0.15 L0.09,0.02" fill="none" stroke="#30b65a" stroke-width="0.05" stroke-linejoin="round"/></g>`;
    }
    if (m.vacuum) {
      s += `<g transform="translate(${tx(m.vacuum.x)},${ty(m.vacuum.y)})"><circle r="0.44" fill="var(--xv-accent)" opacity=".16"/><circle r="0.25" fill="var(--xv-accent)" stroke="var(--xv-card)" stroke-width="0.06"/></g>`;
    }
    return s + "</svg>";
  }

  /* ---------------- controls ---------------- */
  _cycleFan() { this._cycleSelect(this._config.fan || `select.${this._base()}_fan_speed`); }
  _cycleSelect(eid) {
    const e = this._st(eid); if (!e) return;
    const opts = e.attributes.options || []; if (!opts.length) return;
    const cur = this._pendSel[eid] != null ? this._pendSel[eid] : e.state;
    const next = opts[(opts.indexOf(cur) + 1) % opts.length];
    this._pendSel[eid] = next;
    clearTimeout(this._pendSelT[eid]);
    this._pendSelT[eid] = setTimeout(() => { delete this._pendSel[eid]; }, 6000);
    this._toast(cap(next));
    this._svc("select", "select_option", { entity_id: eid, option: next });
  }
  // brief pill of feedback for the icon-only cyclers (fan / water level)
  _toast(text) {
    const t = this._root && this._root.querySelector(".toast"); if (!t) return;
    t.textContent = text; t.classList.add("show");
    clearTimeout(this._toastT);
    this._toastT = setTimeout(() => t.classList.remove("show"), 1300);
  }
  _cleanSelected() {
    if (!this._sel.size || !this._enabled("allow_room_cleaning")) return;
    this._svc("xiaomi_vac", "clean_segment", { entity_id: this._config.vacuum, segments: [...this._sel] });
    this._sel.clear(); this._syncRooms();
  }

  /* ---------------- live update ---------------- */
  async _updateAnim(state, model) {
    const wrap = this._root && this._root.querySelector(".lottie-wrap");
    if (!wrap) return;
    const src = lottieSrc(model, state);
    if (this._animWrap === wrap && this._animSrc === src) return;
    if (this._anim) { this._anim.destroy(); this._anim = null; }
    this._animWrap = wrap;
    this._animSrc = src;
    wrap.innerHTML = vacuumFallbackSvg();
    const [L, data] = await Promise.all([loadLottie(), fetchLottie(src)]);
    if (!L || !data) return;
    if (!this._root || this._root.querySelector(".lottie-wrap") !== wrap) return;
    wrap.innerHTML = "";
    this._anim = L.loadAnimation({ container: wrap, renderer: "svg", loop: true, autoplay: true, animationData: data });
  }
  _syncRooms() {
    // Selection is shown by repainting the fill raster (selected rooms in their
    // saturated tint); the .rm paths stay transparent hit targets.
    this._root.querySelectorAll(".rm").forEach((r) => {
      r.setAttribute("aria-pressed", this._sel.has(Number(r.dataset.id)) ? "true" : "false");
    });
    this._refreshFill();
    const tag = this._root.querySelector(".roomtag");
    const n = this._sel.size;
    if (n) { tag.textContent = `Clean ${n} room${n > 1 ? "s" : ""}`; tag.classList.add("show"); }
    else tag.classList.remove("show");
  }
  // Optimistic feedback: a tap shows the intended state immediately, then the
  // real device state (after the MIoT round-trip + refresh) takes back over.
  _setPending(state) {
    this._pend = { state, expire: Date.now() + 5000 };
    clearTimeout(this._pendT);
    this._pendT = setTimeout(() => { try { this._update(); } catch (e) {} }, 5050);
    this._update();
  }
  _effState(vac) {
    const real = (vac && vac.state) || "unknown";
    if (this._pend) {
      if (real === this._pend.state || Date.now() > this._pend.expire) this._pend = null;
      else return this._pend.state;
    }
    return real;
  }
  _update() {
    const q = (s) => this._root.querySelector(s);
    const vac = this._st(this._config.vacuum);
    const state = this._effState(vac);
    this._root.style.setProperty("--xv-accent", ACCENT[state] || ACCENT.unknown);

    const battEnt = this._st(`sensor.${this._base()}_battery`);
    const batt = battEnt ? Number(battEnt.state) : (vac && vac.attributes.battery_level);
    const hasBatt = batt != null && !Number.isNaN(batt);
    // No charging flag from the device — docked-and-not-full is the charging tell.
    const charging = state === "docked" && hasBatt && batt < 100;
    q(".btxt").textContent = hasBatt ? `${batt}%` : "—";
    q(".bicon").innerHTML = batteryIcon(hasBatt ? batt : 0, charging);

    // On error, surface the fault code the device reported (0/none = no detail).
    const fault = vac && vac.attributes && vac.attributes.fault;
    q(".stxt").textContent =
      state === "error" && fault ? `Error · fault ${fault}` : cap(state);

    const cleaning = state === "cleaning";
    const startBtn = q(".act-start");
    startBtn.querySelector("ha-icon").setAttribute("icon", cleaning ? MDI.pause : MDI.play);
    startBtn.classList.toggle("on", cleaning);   // accent-fill the active action (cf. AC card)
    q(".tray").style.display = this._enabled("show_controls") ? "" : "none";
    q(".cyc-fan").style.display = this._enabled("show_fan") ? "" : "none";
    q(".cyc-water").style.display = this._enabled("show_water") ? "" : "none";
    q(".cyc-map").style.display =
      this._enabled("show_active_map") && this._st(this._activeMapEid()) ? "" : "none";
    // keep image-page name fresh if it was a placeholder
    const nm = q(".pg-img .nm");
    if (nm && vac) nm.textContent = vac.attributes.friendly_name || "Vacuum";

    const showConsumables = this._enabled("show_consumables") &&
      CONSUMABLES.some(([key]) => this._consumableEid(key));
    q(".act-consumables").style.display = showConsumables ? "" : "none";
    if (showConsumables) {
      q(".consum-panel").innerHTML = CONSUMABLES.map(([key, icon, label]) => {
        const eid = this._consumableEid(key);
        const st = eid && this._st(eid);
        const pct = st ? Number(st.state) : null;
        const has = pct != null && !Number.isNaN(pct);
        const clamped = has ? Math.max(0, Math.min(100, pct)) : 0;
        const color = !has ? "var(--xv-muted)" : clamped < 20 ? "#e05252" : clamped < 50 ? "#e0a952" : "#4caf7d";
        return `<div class="consum-row"><ha-icon icon="${icon}"></ha-icon><span class="cn">${esc(label)}</span>` +
          `<span class="cbar"><i style="width:${clamped}%;background:${color}"></i></span>` +
          `<span class="cpct" style="color:${has ? color : ""}">${has ? clamped + "%" : "—"}</span></div>`;
      }).join("");
    } else {
      q(".consum-panel").classList.remove("show");
      q(".act-consumables").classList.remove("on");
    }

    this._updateAnim(state, vac && vac.attributes.model);
  }
}
if (!customElements.get("xiaomi-vac-card"))
  customElements.define("xiaomi-vac-card", XiaomiVacCard);

class XiaomiVacCardEditor extends HTMLElement {
  setConfig(config) { this._config = config; this._render(); }
  set hass(hass) { this._hass = hass; this._render(); }
  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (s) =>
        ({
          vacuum: "Vacuum",
          map: "Map camera",
          fan: "Fan speed select entity",
          water: "Water level select entity",
          activeMap: "Active map select entity",
          show_vacuum_page: "Show vacuum page",
          show_map: "Show map",
          show_controls: "Show controls",
          show_fan: "Show suction control",
          show_water: "Show water control",
          show_active_map: "Show active map control",
          show_room_labels: "Show room labels",
          allow_room_cleaning: "Allow room cleaning",
          show_consumables: "Show accessory status button",
        }[s.name] || s.name);
      this._form.addEventListener("value-changed", (e) =>
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: e.detail.value }, bubbles: true, composed: true })));
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = { ...TOGGLE_DEFAULTS, ...this._config };
    this._form.schema = [
      { name: "vacuum", required: true, selector: { entity: { domain: "vacuum" } } },
      { name: "map", selector: { entity: { domain: "camera" } } },
      { name: "fan", selector: { entity: { domain: "select" } } },
      { name: "water", selector: { entity: { domain: "select" } } },
      { name: "activeMap", selector: { entity: { domain: "select" } } },
      { name: "show_vacuum_page", selector: { boolean: {} } },
      { name: "show_map", selector: { boolean: {} } },
      { name: "show_controls", selector: { boolean: {} } },
      { name: "show_fan", selector: { boolean: {} } },
      { name: "show_water", selector: { boolean: {} } },
      { name: "show_active_map", selector: { boolean: {} } },
      { name: "show_room_labels", selector: { boolean: {} } },
      { name: "allow_room_cleaning", selector: { boolean: {} } },
      { name: "show_consumables", selector: { boolean: {} } },
    ];
  }
}
if (!customElements.get("xiaomi-vac-card-editor"))
  customElements.define("xiaomi-vac-card-editor", XiaomiVacCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "xiaomi-vac-card",
  name: "Xiaomi Vac Card",
  description: "Rich map based vacuum card - swipe between vacuum and map, tap-to-clean rooms.",
  preview: true,
});
