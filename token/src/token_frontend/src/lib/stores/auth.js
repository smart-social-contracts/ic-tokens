import { writable } from 'svelte/store';

export const isAuthenticated = writable(false);
export const principal = writable('');
export const userIdentity = writable(null);
