<script>
  import { onMount, onDestroy } from 'svelte';
  import { selectedYearMonth } from '../lib/stores.js';

  const MONTH_NAMES = [
    'January','February','March','April','May','June',
    'July','August','September','October','November','December',
  ];
  const YEARS = [2022, 2023, 2024, 2025, 2026];

  // Data runs 2022-02 through 2026-05 inclusive.
  const MIN_YM = '2022-02';
  const MAX_YM = '2026-05';

  let selectedYear = null;
  let selectedMonth = null; // 1-indexed

  let yearOpen = false;
  let monthOpen = false;

  let yearEl;
  let monthEl;

  function isMonthValid(year, month) {
    if (!year) return false;
    const ym = `${year}-${String(month).padStart(2, '0')}`;
    return ym >= MIN_YM && ym <= MAX_YM;
  }

  function pickYear(year) {
    selectedYear = year;
    yearOpen = false;
    // If the currently selected month is no longer valid for the new year, reset it.
    if (selectedMonth && !isMonthValid(year, selectedMonth)) {
      selectedMonth = null;
    }
    pushToStore();
  }

  function pickMonth(month) {
    if (!isMonthValid(selectedYear, month)) return;
    selectedMonth = month;
    monthOpen = false;
    pushToStore();
  }

  function pushToStore() {
    if (selectedYear && selectedMonth) {
      selectedYearMonth.set(`${selectedYear}-${String(selectedMonth).padStart(2, '0')}`);
    } else {
      selectedYearMonth.set(null);
    }
  }

  // When the store is cleared externally (e.g. choropleth click), reset UI.
  const unsub = selectedYearMonth.subscribe(v => {
    if (v === null) {
      selectedYear = null;
      selectedMonth = null;
    }
  });

  // Close dropdowns when clicking outside either of them.
  function handleDocClick(e) {
    if (yearOpen && yearEl && !yearEl.contains(e.target)) yearOpen = false;
    if (monthOpen && monthEl && !monthEl.contains(e.target)) monthOpen = false;
  }

  onMount(() => document.addEventListener('click', handleDocClick, true));
  onDestroy(() => {
    document.removeEventListener('click', handleDocClick, true);
    unsub();
  });
</script>

<div class="pickers" role="presentation" on:click|stopPropagation>
  <!-- Year dropdown -->
  <div class="dropdown" bind:this={yearEl}>
    <button
      class="dd-btn"
      class:dd-active={selectedYear !== null}
      on:click|stopPropagation={() => { yearOpen = !yearOpen; monthOpen = false; }}
      aria-expanded={yearOpen}
    >
      <span>{selectedYear ?? 'Year'}</span>
      <span class="caret" class:open={yearOpen}>&#9660;</span>
    </button>
    {#if yearOpen}
      <ul class="dd-list" role="listbox">
        {#each YEARS as y}
          <li role="option" aria-selected={selectedYear === y}>
            <button
              class:selected={selectedYear === y}
              on:click|stopPropagation={() => pickYear(y)}
            >{y}</button>
          </li>
        {/each}
      </ul>
    {/if}
  </div>

  <!-- Month dropdown -->
  <div class="dropdown" bind:this={monthEl}>
    <button
      class="dd-btn"
      class:dd-active={selectedMonth !== null}
      on:click|stopPropagation={() => { monthOpen = !monthOpen; yearOpen = false; }}
      aria-expanded={monthOpen}
    >
      <span>{selectedMonth ? MONTH_NAMES[selectedMonth - 1] : 'Month'}</span>
      <span class="caret" class:open={monthOpen}>&#9660;</span>
    </button>
    {#if monthOpen}
      <ul class="dd-list" role="listbox">
        {#each MONTH_NAMES as name, i}
          {@const month = i + 1}
          {@const valid = isMonthValid(selectedYear, month)}
          <li role="option" aria-selected={selectedMonth === month} aria-disabled={!valid}>
            <button
              class:selected={selectedMonth === month}
              class:disabled={!valid}
              on:click|stopPropagation={() => pickMonth(month)}
              tabindex={valid ? 0 : -1}
            >{name}</button>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
</div>

<style>
  .pickers {
    display: flex;
    gap: 10px;
    align-items: flex-start;
  }

  .dropdown {
    position: relative;
  }

  .dd-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 5px 12px;
    border: 1px solid #ccc;
    background: #fff;
    font-family: var(--sans);
    font-size: 13px;
    color: #555;
    cursor: pointer;
    min-width: 110px;
    justify-content: space-between;
    border-radius: 2px;
    transition: border-color 0.1s;
  }

  .dd-btn:hover {
    border-color: #999;
  }

  .dd-btn.dd-active {
    color: #111;
    border-color: #888;
  }

  .caret {
    font-size: 9px;
    color: #aaa;
    transition: transform 0.15s;
    display: inline-block;
  }

  .caret.open {
    transform: rotate(180deg);
  }

  .dd-list {
    position: absolute;
    top: calc(100% + 2px);
    left: 0;
    z-index: 100;
    background: #fff;
    border: 1px solid #ccc;
    border-radius: 2px;
    list-style: none;
    padding: 3px 0;
    margin: 0;
    min-width: 100%;
    box-shadow: 0 3px 10px rgba(0,0,0,0.08);
  }

  .dd-list button {
    display: block;
    width: 100%;
    text-align: left;
    padding: 5px 12px;
    border: none;
    background: none;
    font-family: var(--sans);
    font-size: 13px;
    color: #222;
    cursor: pointer;
  }

  .dd-list button:hover:not(.disabled) {
    background: #f5f5f5;
  }

  .dd-list button.selected {
    color: #c0392b;
    font-weight: 600;
  }

  .dd-list button.disabled {
    color: #ccc;
    cursor: default;
  }
</style>
