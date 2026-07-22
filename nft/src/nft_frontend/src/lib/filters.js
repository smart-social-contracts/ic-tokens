import { metaText } from '$lib/metadata.js';

export function tokenAssetType(token) {
  return metaText(token.metadata, 'asset_type') || metaText(token.metadata, 'land_type') || '';
}

export function tokenRealm(token) {
  return metaText(token.metadata, 'realm_canister') || '';
}

export function tokenLandId(token) {
  return metaText(token.metadata, 'land_id') || '';
}

export function uniqueFilterOptions(tokens, extractor) {
  const values = tokens.map(extractor).filter(Boolean);
  return [...new Set(values)].sort();
}

export function filterTokens(tokens, filters) {
  return tokens.filter((token) => {
    if (filters.type && tokenAssetType(token) !== filters.type) return false;
    if (filters.realm && tokenRealm(token) !== filters.realm) return false;
    if (filters.authority && token.authority !== filters.authority) return false;
    if (filters.owner && token.owner !== filters.owner) return false;
    if (filters.frozen && !token.frozen) return false;
    if (filters.mineOnly && token.owner !== filters.viewer) return false;
    if (filters.search) {
      const q = filters.search.toLowerCase();
      const haystack = [
        token.id,
        token.owner,
        token.authority,
        tokenAssetType(token),
        tokenRealm(token),
        tokenLandId(token),
        metaText(token.metadata, 'name'),
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    return true;
  });
}
