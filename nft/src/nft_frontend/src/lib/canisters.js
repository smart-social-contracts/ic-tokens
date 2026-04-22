import { createActor, canisterId as defaultCanisterId } from 'declarations/nft_backend';
import { building, browser } from '$app/environment';

function dummyActor() {
    return new Proxy({}, { get() { throw new Error("Canister invoked while building"); } });
}

function getBackendCanisterId() {
    if (!browser) return defaultCanisterId;
    const params = new URLSearchParams(window.location.search);
    return params.get('backend') || defaultCanisterId;
}

const buildingOrTesting = building || process.env.NODE_ENV === "test";

export const backend = buildingOrTesting
    ? dummyActor()
    : createActor(getBackendCanisterId());
