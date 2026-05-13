import { writable } from 'svelte/store';

export const selectedCountries = writable(new Set());
export const dateRange = writable(null);
export const showEvents = writable(false);
// "YYYY-MM" string or null — drives the themes panel and time-series highlight rect
export const selectedYearMonth = writable(null);
