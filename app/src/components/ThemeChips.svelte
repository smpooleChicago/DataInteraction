<script>
  import { createEventDispatcher } from 'svelte';

  // Array of {theme, theme_count} objects (already top-5, sorted)
  export let themes = [];
  // Currently active theme string or null
  export let selected = null;

  const dispatch = createEventDispatcher();

  function formatTheme(raw) {
    return raw
      .split('_')
      .map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join(' ');
  }

  function handleClick(theme) {
    dispatch('select', theme === selected ? null : theme);
  }
</script>

<div class="chips" role="presentation" on:click|stopPropagation>
  {#each themes as t}
    <button
      class="chip"
      class:chip-active={selected === t.theme}
      on:click={() => handleClick(t.theme)}
      title={t.theme}
    >
      {formatTheme(t.theme)}
    </button>
  {/each}
</div>

<style>
  .chips {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .chip {
    padding: 4px 13px;
    border: 1px solid #bbb;
    background: #fff;
    font-family: var(--sans);
    font-size: 12px;
    color: #444;
    cursor: pointer;
    border-radius: 2px;
    white-space: nowrap;
    transition: background 0.1s, color 0.1s, border-color 0.1s;
    letter-spacing: 0.01em;
  }

  .chip:hover:not(.chip-active) {
    border-color: #888;
    color: #111;
  }

  .chip-active {
    background: #c0392b;
    border-color: #c0392b;
    color: #fff;
    font-weight: 600;
  }
</style>
