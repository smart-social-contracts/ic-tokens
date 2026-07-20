import { AuthClient } from '@dfinity/auth-client';
import { isAuthenticated, principal, userIdentity } from '$lib/stores/auth.js';
import { initBackendWithIdentity } from '$lib/canisters.js';

const II_URL =
  (typeof globalThis !== 'undefined' && globalThis.__CANISTER_IDS?.internet_identity) ||
  'https://identity.ic0.app';

let authClient;

export async function initializeAuthClient() {
  if (authClient) return authClient;
  authClient = await AuthClient.create({
    keyType: 'Ed25519',
    idleOptions: { disableIdle: true },
  });
  return authClient;
}

export async function restoreAuthSession() {
  const client = await initializeAuthClient();
  const authed = await client.isAuthenticated();
  if (!authed) {
    isAuthenticated.set(false);
    principal.set('');
    userIdentity.set(null);
    await initBackendWithIdentity(null);
    return false;
  }
  const identity = client.getIdentity();
  const p = identity.getPrincipal().toText();
  isAuthenticated.set(true);
  principal.set(p);
  userIdentity.set(identity);
  await initBackendWithIdentity(identity);
  return true;
}

export async function login() {
  const client = await initializeAuthClient();
  if (await client.isAuthenticated()) {
    const identity = client.getIdentity();
    const p = identity.getPrincipal().toText();
    isAuthenticated.set(true);
    principal.set(p);
    userIdentity.set(identity);
    await initBackendWithIdentity(identity);
    return p;
  }

  return new Promise((resolve, reject) => {
    client.login({
      identityProvider: II_URL,
      maxTimeToLive: BigInt(7 * 24 * 3600 * 1_000_000_000),
      onSuccess: async () => {
        try {
          const identity = client.getIdentity();
          const p = identity.getPrincipal().toText();
          isAuthenticated.set(true);
          principal.set(p);
          userIdentity.set(identity);
          await initBackendWithIdentity(identity);
          resolve(p);
        } catch (err) {
          reject(err);
        }
      },
      onError: (err) => reject(err instanceof Error ? err : new Error(String(err))),
    });
  });
}

export async function logout() {
  const client = await initializeAuthClient();
  await client.logout();
  isAuthenticated.set(false);
  principal.set('');
  userIdentity.set(null);
  await initBackendWithIdentity(null);
}
