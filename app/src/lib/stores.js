import { writable } from 'svelte/store';

export const selectedCountries = writable(new Set());
export const dateRange = writable(null);
export const showEvents = writable(false);
