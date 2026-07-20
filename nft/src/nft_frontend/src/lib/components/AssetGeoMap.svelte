<script>
  import { onDestroy, onMount, tick } from 'svelte';
  import {
    landColor,
    loadH3Lib,
    loadMapLibre,
    loadMapStyle,
  } from '$lib/geo.js';

  export let geo = null;
  export let compact = false;
  export let label = '';

  let mapContainer;
  let map = null;
  let maplibregl = null;
  let h3 = null;
  let mapReady = false;
  let loadError = '';

  const SOURCE_PARCELS = 'asset-parcels';
  const SOURCE_POINTS = 'asset-points';

  function cellToLatLng(h3Index) {
    if (!h3Index || !h3) return null;
    try {
      const [lat, lng] = h3.cellToLatLng(h3Index);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
      return [lat, lng];
    } catch {
      return null;
    }
  }

  function buildParcelGeoJson() {
    const features = [];
    const color = landColor(geo?.landType || 'unassigned');
    for (const h3Index of geo?.h3Indexes || []) {
      try {
        const boundary = h3.cellToBoundary(h3Index, true);
        features.push({
          type: 'Feature',
          properties: { h3_index: h3Index, color },
          geometry: { type: 'Polygon', coordinates: [boundary] },
        });
      } catch {
        /* skip invalid cell */
      }
    }
    return { type: 'FeatureCollection', features };
  }

  function buildPointGeoJson() {
    const features = [];
    const color = landColor(geo?.landType || 'unassigned');

    for (const h3Index of geo?.h3Indexes || []) {
      const coords = cellToLatLng(h3Index);
      if (!coords) continue;
      features.push({
        type: 'Feature',
        properties: { color, h3_index: h3Index },
        geometry: { type: 'Point', coordinates: [coords[1], coords[0]] },
      });
    }

    if (!features.length && geo?.lat != null && geo?.lng != null) {
      features.push({
        type: 'Feature',
        properties: { color },
        geometry: { type: 'Point', coordinates: [geo.lng, geo.lat] },
      });
    }

    return { type: 'FeatureCollection', features };
  }

  function fitToData() {
    if (!map || !maplibregl) return;
    const bounds = new maplibregl.LngLatBounds();
    let hasBounds = false;

    for (const h3Index of geo?.h3Indexes || []) {
      const coords = cellToLatLng(h3Index);
      if (coords) {
        bounds.extend([coords[1], coords[0]]);
        hasBounds = true;
      }
    }

    if (!hasBounds && geo?.lat != null && geo?.lng != null) {
      bounds.extend([geo.lng, geo.lat]);
      hasBounds = true;
    }

    if (hasBounds) {
      map.fitBounds(bounds, { padding: compact ? 24 : 48, maxZoom: compact ? 11 : 13 });
    }
  }

  function renderData() {
    if (!map || !mapReady) return;
    map.getSource(SOURCE_PARCELS)?.setData(buildParcelGeoJson());
    map.getSource(SOURCE_POINTS)?.setData(buildPointGeoJson());
    fitToData();
  }

  function addLayers() {
    if (!map) return;
    map.addSource(SOURCE_PARCELS, { type: 'geojson', data: buildParcelGeoJson() });
    map.addLayer({
      id: 'asset-parcels-fill',
      type: 'fill',
      source: SOURCE_PARCELS,
      paint: {
        'fill-color': ['get', 'color'],
        'fill-opacity': 0.65,
      },
    });
    map.addLayer({
      id: 'asset-parcels-line',
      type: 'line',
      source: SOURCE_PARCELS,
      paint: {
        'line-color': '#171717',
        'line-width': 2,
      },
    });

    map.addSource(SOURCE_POINTS, { type: 'geojson', data: buildPointGeoJson() });
    map.addLayer({
      id: 'asset-points',
      type: 'circle',
      source: SOURCE_POINTS,
      paint: {
        'circle-radius': compact ? 6 : 8,
        'circle-color': ['get', 'color'],
        'circle-stroke-color': '#ffffff',
        'circle-stroke-width': 2,
      },
    });

    map.on('zoomend', updateLayerVisibility);
    updateLayerVisibility();
  }

  function updateLayerVisibility() {
    if (!map || !mapReady) return;
    const showHex = map.getZoom() >= 10;
    for (const id of ['asset-parcels-fill', 'asset-parcels-line']) {
      if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', showHex ? 'visible' : 'none');
    }
    if (map.getLayer('asset-points')) {
      map.setLayoutProperty('asset-points', 'visibility', showHex ? 'none' : 'visible');
    }
  }

  async function initMap() {
    if (!mapContainer || map || !geo) return;
    loadError = '';
    try {
      maplibregl = await loadMapLibre();
      h3 = await loadH3Lib();
      const style = await loadMapStyle();
      map = new maplibregl.Map({
        container: mapContainer,
        style,
        center: [0, 20],
        zoom: 2,
        attributionControl: !compact,
      });
      map.on('load', async () => {
        addLayers();
        mapReady = true;
        renderData();
        await tick();
        map?.resize();
      });
    } catch (error) {
      loadError = error.message || 'Failed to load map';
    }
  }

  function destroyMap() {
    mapReady = false;
    if (map) {
      map.remove();
      map = null;
    }
  }

  onMount(() => {
    initMap();
  });

  onDestroy(() => {
    destroyMap();
  });

  $: if (mapReady && geo) {
    renderData();
  }

  $: showMap = geo && (geo.h3Indexes?.length > 0 || (geo.lat != null && geo.lng != null));
  $: showGrid = geo && !showMap && geo.gridX != null && geo.gridY != null;
</script>

{#if showMap}
  <div class="geo-map-wrap" class:compact>
    {#if label && !compact}
      <div class="geo-map-label">{label}</div>
    {/if}
    {#if loadError}
      <div class="geo-map-fallback">{loadError}</div>
    {:else}
      <div class="geo-map" bind:this={mapContainer}></div>
    {/if}
    {#if geo.h3Indexes?.length}
      <div class="geo-map-meta">
        {#each geo.h3Indexes.slice(0, compact ? 1 : 3) as h3Index}
          <code>{h3Index}</code>
        {/each}
        {#if geo.h3Indexes.length > (compact ? 1 : 3)}
          <span class="muted">+{geo.h3Indexes.length - (compact ? 1 : 3)} more</span>
        {/if}
      </div>
    {/if}
  </div>
{:else if showGrid}
  <div class="geo-grid-wrap" class:compact>
    {#if label && !compact}
      <div class="geo-map-label">{label}</div>
    {/if}
    <div class="geo-grid">
      <span class="geo-grid-label">Grid coordinates</span>
      <strong>{geo.gridX}, {geo.gridY}</strong>
      <span class="muted">Legacy registry grid — geographic map unavailable without H3 data.</span>
    </div>
  </div>
{/if}

<style>
  .geo-map-wrap,
  .geo-grid-wrap {
    margin-top: 12px;
  }

  .geo-map-wrap.compact,
  .geo-grid-wrap.compact {
    margin-top: 0;
  }

  .geo-map-label {
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--color-text-tertiary);
    margin-bottom: 8px;
  }

  .geo-map {
    width: 100%;
    height: 280px;
    border: 1px solid var(--color-border-primary);
    border-radius: 4px;
    overflow: hidden;
    background: #f3f4f6;
  }

  .compact .geo-map {
    height: 120px;
  }

  .geo-map-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 8px;
    align-items: center;
  }

  .geo-map-meta code {
    font-size: 0.72rem;
    padding: 2px 6px;
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border-primary);
    border-radius: 3px;
  }

  .geo-map-fallback,
  .geo-grid {
    border: 1px solid var(--color-border-primary);
    border-radius: 4px;
    padding: 16px;
    background: var(--color-bg-secondary);
  }

  .geo-grid {
    display: grid;
    gap: 6px;
  }

  .geo-grid-label {
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--color-text-tertiary);
  }

  .muted {
    color: var(--color-text-tertiary);
    font-size: 0.82rem;
  }
</style>
