<script>
  import * as d3 from 'd3';

  export let data = [];          // [{date: Date, value: number|null}] — 7-day smoothed
  export let activeRange = null; // [Date, Date] | null
  export let label = '';

  let W = 800;
  const H = 70;
  const PAD = 8;

  $: IW = W - PAD * 2;

  $: xScale = data.length > 0 && IW > 0
    ? d3.scaleTime()
        .domain([d3.min(data, d => d.date), d3.max(data, d => d.date)])
        .range([0, IW])
    : null;

  $: yMax = data.length > 0 ? (d3.max(data, d => d.value ?? 0) * 1.1 || 10) : 10;
  $: yScale = d3.scaleLinear().domain([0, yMax]).range([H - 2, 2]);

  $: lineGen = xScale
    ? d3.line()
        .x(d => xScale(d.date))
        .y(d => yScale(d.value))
        .defined(d => d.value != null)
        .curve(d3.curveMonotoneX)
    : null;

  $: greyPath = lineGen && data.length > 0 ? lineGen(data) : '';

  $: redData = activeRange && xScale
    ? data.filter(d => d.date >= activeRange[0] && d.date <= activeRange[1] && d.value != null)
    : [];

  $: redPath = lineGen && redData.length > 0 ? lineGen(redData) : '';

  $: dot = (() => {
    if (!activeRange || !xScale || redData.length === 0) return null;
    const midTime = (activeRange[0].getTime() + activeRange[1].getTime()) / 2;
    const midDate = new Date(midTime);
    const closest = redData.reduce((a, b) =>
      Math.abs(b.date - midDate) < Math.abs(a.date - midDate) ? b : a
    );
    return { x: xScale(closest.date), y: yScale(closest.value) };
  })();
</script>

<div class="spark-wrap" bind:clientWidth={W}>
  {#if label}
    <div class="spark-label">{label}</div>
  {/if}
  {#if data.length > 0 && xScale}
    <svg width={W} height={H} style="display:block;overflow:visible;">
      <g transform="translate({PAD},0)">
        {#if greyPath}
          <path d={greyPath} fill="none" stroke="#ccc" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" />
        {/if}
        {#if redPath}
          <path d={redPath} fill="none" stroke="#e3120b" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
        {/if}
        {#if dot}
          <circle cx={dot.x} cy={dot.y} r="3.5" fill="#e3120b" />
        {/if}
      </g>
    </svg>
  {/if}
</div>

<style>
  .spark-wrap {
    width: 100%;
  }
  .spark-label {
    font-family: var(--sans);
    font-size: 12px;
    color: #555;
    margin-bottom: 3px;
  }
</style>
