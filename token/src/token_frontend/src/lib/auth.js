import { AuthClient } from '@dfinity/auth-client';
import { isAuthenticated, principal, userIdentity } from '$lib/stores/auth.js';
import { initBackendWithIdentity } from '$lib/canisters.js';

const II_URL = 'https://identity.ic0.app';

let authClient;

export async function initializeAuthClient() {
  if (authClient) return authClient;
  authClient = await AuthClient.create({
    keyType: 'Ed25519',
    idleOptions: { disableIdle: true },
  });
  return authClient;
}

async function applyIdentity(identity) {
  const p = identity.getPrincipal().toText();
  isAuthenticated.set(true);
  principal.set(p);
  userIdentity.set(identity);
  await initBackendWithIdentity(identity);
  return p;
}

export async function restoreAuthSession() {
  const client = await initializeAuthClient();
  if (!(await client.isAuthenticated())) {
    isAuthenticated.set(false);
    principal.set('');
    userIdentity.set(null);
    await initBackendWithIdentity(null);
    return false;
  }
  await applyIdentity(client.getIdentity());
  return true;
}

export async function login() {
  const client = await initializeAuthClient();
  if (await client.isAuthenticated()) {
    return applyIdentity(client.getIdentity());
  }

  return new Promise((resolve, reject) => {
    client.login({
      identityProvider: II_URL,
      maxTimeToLive: BigInt(7 * 24 * 3600 * 1_000_000_000),
      onSuccess: async () => {
        try {
          resolve(await applyIdentity(client.getIdentity()));
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
