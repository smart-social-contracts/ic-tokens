function isMetadataVec(value) {
  return (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every(
      (entry) =>
        Array.isArray(entry) &&
        entry.length === 2 &&
        typeof entry[0] === 'string' &&
        entry[1] &&
        typeof entry[1] === 'object',
    )
  );
}

export function normalizeTokenMetadata(raw) {
  if (!raw || !Array.isArray(raw) || raw.length === 0) return [];
  if (isMetadataVec(raw)) return raw;
  if (raw.length === 1 && isMetadataVec(raw[0])) return raw[0];
  return [];
}

export function metaText(metadata, key) {
  const entries = normalizeTokenMetadata(metadata);
  if (!entries.length) return '';
  const entry = entries.find((m) => m[0] === key);
  if (!entry?.[1] || !('Text' in entry[1])) return '';
  return entry[1].Text;
}

export function metaNat(metadata, key) {
  const entries = normalizeTokenMetadata(metadata);
  if (!entries.length) return null;
  const entry = entries.find((m) => m[0] === key);
  if (!entry?.[1] || !('Nat' in entry[1])) return null;
  return Number(entry[1].Nat);
}

export function tokenDisplayName(token) {
  const name = metaText(token.metadata, 'name');
  if (name) return name;
  const assetType = metaText(token.metadata, 'asset_type');
  if (assetType) return `${assetType} #${token.id}`;
  return `Asset #${token.id}`;
}

export function tokenSubtitle(token) {
  const parts = [];
  const assetType = metaText(token.metadata, 'asset_type');
  const landId = metaText(token.metadata, 'land_id');
  const realm = metaText(token.metadata, 'realm_canister');
  if (assetType) parts.push(assetType);
  if (landId) parts.push(`land ${landId}`);
  if (realm) parts.push(`realm ${truncate(realm)}`);
  return parts.join(' · ') || 'Registry asset';
}

export function metadataRows(token) {
  const entries = normalizeTokenMetadata(token.metadata);
  if (!entries.length) return [];
  return entries
    .map(([key, value]) => {
      if ('Text' in value) return { key, value: value.Text };
      if ('Nat' in value) return { key, value: String(value.Nat) };
      if ('Int' in value) return { key, value: String(value.Int) };
      return null;
    })
    .filter(Boolean);
}

export function truncate(value, head = 8, tail = 6) {
  if (!value || value.length <= head + tail + 3) return value || '';
  return `${value.slice(0, head)}…${value.slice(-tail)}`;
}
