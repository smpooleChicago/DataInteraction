<script>
  import { onMount } from 'svelte';

  export let activeStep = 0;
  export let autoScroll = false;
  export let stopAtStep = Infinity;

  // Timing constants
  const INITIAL_DELAY   = 1800; // ms before the first scroll begins
  const SCROLL_DURATION = 2800; // ms for the custom smooth-scroll animation
  const DWELL_TIME      = 5700; // ms spent reading each step after it arrives
  // px from the viewport top where the step's top edge lands — keeps
  // the eyebrow + title clearly visible.
  const VIEWPORT_OFFSET = 110;

  let storyEl;

  // easeInOutQuart — slow start, fast middle, slow end.
  function ease(t) {
    return t < 0.5 ? 8*t*t*t*t : 1 - Math.pow(-2*t + 2, 4) / 2;
  }

  // Custom RAF-based scroll so we own the duration (browser smooth-scroll
  // speed is not controllable via scrollIntoView).
  function scrollToY(targetY, duration, state) {
    return new Promise(resolve => {
      const startY = window.scrollY;
      const dist   = targetY - startY;
      if (Math.abs(dist) < 2) { resolve(); return; }

      let t0 = null;
      function frame(ts) {
        if (state.cancelled) { resolve(); return; }
        if (t0 === null) t0 = ts;
        const p = Math.min((ts - t0) / duration, 1);
        window.scrollTo(0, startY + dist * ease(p));
        if (p < 1) requestAnimationFrame(frame);
        else resolve();
      }
      requestAnimationFrame(frame);
    });
  }

  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  onMount(() => {
    const steps = Array.from(storyEl.querySelectorAll('.step'));

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const idx = steps.indexOf(entry.target);
            if (idx !== -1) activeStep = idx;
          }
        });
      },
      { rootMargin: '-45% 0px -45% 0px', threshold: 0 }
    );
    steps.forEach(el => observer.observe(el));

    if (!autoScroll || steps.length === 0) return () => observer.disconnect();

    // ── Auto-scroll sequence ───────────────────────────────────────────────
    const state = { cancelled: false };

    function cancel() {
      if (state.cancelled) return;
      state.cancelled = true;
      window.removeEventListener('wheel',      cancel);
      window.removeEventListener('touchstart', cancel);
      window.removeEventListener('keydown',    cancel);
    }

    window.addEventListener('wheel',      cancel, { passive: true });
    window.addEventListener('touchstart', cancel, { passive: true });
    window.addEventListener('keydown',    cancel);

    const target = Math.min(stopAtStep, steps.length - 1);

    async function run() {
      await sleep(INITIAL_DELAY);
      for (let i = 0; i <= target; i++) {
        if (state.cancelled) break;
        // Target Y: step top sits VIEWPORT_OFFSET px below the viewport top.
        const stepTop = steps[i].getBoundingClientRect().top + window.scrollY;
        await scrollToY(stepTop - VIEWPORT_OFFSET, SCROLL_DURATION, state);
        if (state.cancelled) break;
        if (i < target) await sleep(DWELL_TIME);
      }
    }

    run();

    return () => { cancel(); observer.disconnect(); };
  });
</script>

<div class="scrolly">
  <div class="viz"><slot name="viz" /></div>
  <div class="story" bind:this={storyEl}><slot /></div>
</div>

<style>
  .scrolly {
    display: grid;
    grid-template-columns: 1.4fr 1fr;
    gap: 2.5rem;
    align-items: start;
    margin: 2rem 0 4rem;
  }
  .viz {
    position: sticky;
    top: 2rem;
    grid-column: 1;
    grid-row: 1;
    align-self: start;
  }
  .story {
    grid-column: 2;
    grid-row: 1;
  }
  :global(.step) {
    padding: 2rem 0 2rem 1.25rem;
    border-left: 3px solid #e3120b;
    margin-bottom: 1rem;
  }
  :global(.step h2) {
    font-family: var(--serif);
    font-size: 20px;
    margin: 0 0 0.5rem;
    color: #111;
  }
  :global(.step .step-eyebrow) {
    font-family: var(--sans);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #999;
    margin: 0 0 0.4rem;
  }
  :global(.step p) {
    font-family: var(--serif);
    font-size: 15px;
    line-height: 1.55;
    color: #222;
    margin: 0 0 0.8rem;
  }
  :global(.step .callout) {
    font-family: var(--sans);
    font-size: 12.5px;
    color: #555;
    border-top: 1px solid #ddd;
    padding-top: 0.6rem;
    margin-top: 0.8rem;
  }
</style>
