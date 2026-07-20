import { Actor, HttpAgent } from '@dfinity/agent';
import { IDL } from '@dfinity/candid';
import { metaNat, metaText, normalizeTokenMetadata } from '$lib/metadata.js';

const STYLE_URL = 'https://tiles.openfreemap.org/styles/positron';

const realmIdlFactory = ({ IDL: I }) => {
  const ExtensionCallResponse = I.Record({
    success: I.Bool,
    response: I.Text,
  });
  return I.Service({
    extension_call: I.Func(
      [I.Text, I.Text, I.Text],
      [ExtensionCallResponse],
      ['query'],
    ),
  });
};

function agentHost() {
  if (typeof window === 'undefined') return 'https://icp0.io';
  const host = window.location.hostname;
  if (host.includes('localhost') || host.includes('127.0.0.1')) {
    return `http://${host}:8000`;
  }
  return 'https://icp0.io';
}

function parseLandMetadata(raw) {
  if (!raw) return {};
  try {
    return typeof raw === 'string' ? JSON.parse(raw) : raw;
  } catch {
    return {};
  }
}

export function isValidCanisterId(value) {
  if (!value || typeof value !== 'string') return false;
  if (value === 'aaaaa-aa') return false; // management / placeholder
  if (value === 'ic0') return false;
  return /^[a-z0-9-]{5,}$/.test(value) && value.length > 5;
}

function h3IndexesFromLand(land) {
  if (!land) return [];
  const indexes = [];
  if (land.h3_indexes?.length) {
    indexes.push(...land.h3_indexes.map(String));
  }
  if (land.h3_index) indexes.push(String(land.h3_index));
  if (land.zones?.length) {
    for (const zone of land.zones) {
      if (zone?.h3_index) indexes.push(String(zone.h3_index));
    }
  }
  const meta = parseLandMetadata(land.metadata);
  if (meta.h3_indexes?.length) {
    indexes.push(...meta.h3_indexes.map(String));
  }
  if (meta.parent_zone) indexes.push(String(meta.parent_zone));
  return [...new Set(indexes.filter(Boolean))];
}

export function extractGeoFromMetadata(metadata) {
  const entries = normalizeTokenMetadata(metadata);
  const h3Indexes = [];
  const h3List = metaText(entries, 'h3_indexes');
  if (h3List) {
    try {
      const parsed = JSON.parse(h3List);
      if (Array.isArray(parsed)) h3Indexes.push(...parsed.map(String));
    } catch {
      h3List.split(/[,\s]+/).forEach((part) => {
        if (part) h3Indexes.push(part);
      });
    }
  }
  const single = metaText(entries, 'h3_index');
  if (single) h3Indexes.push(single);

  const lat =
    metaNat(entries, 'latitude') ??
    metaNat(entries, 'lat') ??
    null;
  const lng =
    metaNat(entries, 'longitude') ??
    metaNat(entries, 'lng') ??
    metaNat(entries, 'lon') ??
    null;

  const gridX = metaNat(entries, 'x_coordinate');
  const gridY = metaNat(entries, 'y_coordinate');

  return {
    h3Indexes: [...new Set(h3Indexes.filter(Boolean))],
    lat,
    lng,
    gridX,
    gridY,
    landId: metaText(entries, 'land_id'),
    realmCanister: metaText(entries, 'realm_canister'),
    landType: metaText(entries, 'land_type') || metaText(entries, 'asset_type'),
  };
}

export function hasGeoMetadata(metadata) {
  const geo = extractGeoFromMetadata(metadata);
  return (
    geo.h3Indexes.length > 0 ||
    (geo.lat != null && geo.lng != null) ||
    (geo.gridX != null && geo.gridY != null)
  );
}

const landGeoCache = new Map();

export async function resolveTokenGeo(metadata) {
  const geo = extractGeoFromMetadata(metadata);
  if (geo.h3Indexes.length > 0 || (geo.lat != null && geo.lng != null)) {
    return geo;
  }
  if (!geo.landId || !geo.realmCanister || !isValidCanisterId(geo.realmCanister)) {
    return geo;
  }

  const cacheKey = `${geo.realmCanister}:${geo.landId}`;
  if (landGeoCache.has(cacheKey)) {
    const cached = landGeoCache.get(cacheKey);
    return { ...geo, h3Indexes: cached.h3Indexes, landType: geo.landType || cached.landType };
  }

  try {
    const agent = new HttpAgent({ host: agentHost() });
    if (agentHost().includes('127.0.0.1') || agentHost().includes('localhost')) {
      await agent.fetchRootKey();
    }
    const actor = Actor.createActor(realmIdlFactory, {
      agent,
      canisterId: geo.realmCanister,
    });
    const result = await actor.extension_call(
      'land_registry',
      'get_land',
      JSON.stringify({ land_id: geo.landId }),
    );
    if (!result?.success) return geo;
    const parsed = JSON.parse(result.response || '{}');
    if (!parsed.success || !parsed.data) return geo;
    const h3Indexes = h3IndexesFromLand(parsed.data);
    landGeoCache.set(cacheKey, {
      h3Indexes,
      landType: parsed.data.land_type || geo.landType,
    });
    return {
      ...geo,
      h3Indexes,
      landType: geo.landType || parsed.data.land_type || '',
      gridX: geo.gridX ?? parsed.data.x_coordinate ?? null,
      gridY: geo.gridY ?? parsed.data.y_coordinate ?? null,
    };
  } catch (error) {
    console.warn('Failed to resolve land geo from realm:', error);
    return geo;
  }
}

export function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve();
      return;
    }
    const script = document.createElement('script');
    script.src = src;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.head.appendChild(script);
  });
}

export function loadStylesheet(href) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`link[href="${href}"]`)) {
      resolve();
      return;
    }
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    link.onload = () => resolve();
    link.onerror = () => reject(new Error(`Failed to load ${href}`));
    document.head.appendChild(link);
  });
}

export async function loadMapLibre() {
  await loadStylesheet('https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.css');
  await loadScript('https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.js');
  return window.maplibregl;
}

export async function loadH3Lib() {
  if (window.h3) return window.h3;
  const res = await fetch('https://unpkg.com/h3-js@4.2.1/dist/h3-js.umd.js');
  if (!res.ok) throw new Error(`Failed to load h3-js: HTTP ${res.status}`);
  // eslint-disable-next-line no-eval
  (0, eval)(await res.text());
  return window.h3;
}

export async function loadMapStyle() {
  try {
    const res = await fetch(STYLE_URL);
    if (!res.ok) return STYLE_URL;
    const style = await res.json();
    if (!style?.layers) return STYLE_URL;
    const filtered = { ...style, layers: [] };
    for (const layer of style.layers) {
      const id = String(layer.id || '').toLowerCase();
      const sourceLayer = String(layer['source-layer'] || '').toLowerCase();
      const type = String(layer.type || '').toLowerCase();
      const isBoundary =
        sourceLayer.includes('boundary') || sourceLayer === 'admin' || id.includes('boundary');
      const isLabel = type === 'symbol' || id.includes('label') || sourceLayer.includes('place');
      if (!isBoundary && !isLabel) filtered.layers.push(layer);
    }
    delete filtered.light;
    return filtered;
  } catch {
    return STYLE_URL;
  }
}

export const LAND_COLORS = {
  residential: '#4ade80',
  agricultural: '#fbbf24',
  industrial: '#6b7280',
  commercial: '#3b82f6',
  unassigned: '#e5e7eb',
};

export function landColor(type) {
  return LAND_COLORS[type] || LAND_COLORS.unassigned;
}
