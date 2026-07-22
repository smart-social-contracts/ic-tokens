import { get, writable } from 'svelte/store';
import { Actor, HttpAgent } from '@dfinity/agent';
import { idlFactory } from 'declarations/token_backend';
import { building, browser } from '$app/environment';

export const backendStore = writable(null);
export const backendReady = writable(false);

function dummyActor() {
  return new Proxy(
    {},
    {
      get() {
        throw new Error('Canister invoked while building');
      },
    }
  );
}

function getBackendCanisterId() {
  if (!browser) {
    return process.env.CANISTER_ID_TOKEN_BACKEND || '';
  }
  const params = new URLSearchParams(window.location.search);
  return params.get('backend') || process.env.CANISTER_ID_TOKEN_BACKEND || '';
}

function agentHost() {
  if (!browser) return 'https://icp0.io';
  const host = window.location.hostname;
  if (host.includes('localhost') || host.includes('127.0.0.1')) {
    return `http://${host}:8000`;
  }
  return 'https://icp0.io';
}

export async function initBackendWithIdentity(identity = null) {
  if (building || !browser) return dummyActor();

  const canisterId = getBackendCanisterId();
  const agent = new HttpAgent({ identity, host: agentHost() });
  if (agentHost().includes('127.0.0.1') || agentHost().includes('localhost')) {
    await agent.fetchRootKey();
  }
  const actor = Actor.createActor(idlFactory, { agent, canisterId });
  backendStore.set(actor);
  backendReady.set(true);
  return actor;
}

const buildingOrTesting = building || process.env.NODE_ENV === 'test';

export const backend = buildingOrTesting
  ? dummyActor()
  : new Proxy(
      {},
      {
        get(_target, prop) {
          const actor = get(backendStore);
          if (!actor) {
            throw new Error('Backend actor not ready');
          }
          const value = actor[prop];
          return typeof value === 'function' ? value.bind(actor) : value;
        },
      }
    );
