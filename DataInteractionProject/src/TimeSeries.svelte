<script>
    import * as d3 from 'd3';

    export let data = [];
    export let animate = false;

    const width = 900;
    const height = 450;
    const margin = { top: 30, right: 30, bottom: 50, left: 70 };

    $: xScale = d3
        .scaleTime()
        .domain(d3.extent(data, d => d.date))
        .range([margin.left, width - margin.right]);

    $: yScale = d3
        .scaleLinear()
        .domain([0, d3.max(data, d => d.value)])
        .nice()
        .range([height - margin.bottom, margin.top]);

    $: line = d3
        .line()
        .x(d => xScale(d.date))
        .y(d => yScale(d.value));

    $: xTicks = xScale.ticks(6);
    $: yTicks = yScale.ticks(5);

    //   brush

    let brushGroup;
    let selectedRange = null;

    $: if (brushGroup && data.length) {
        const brush = d3
        .brushX()
        .extent([
            [margin.left, margin.top],
            [width - margin.right, height - margin.bottom]
        ])
        .on('brush end', (event) => {
            if (!event.selection) {
            selectedRange = null;
            return;
            }

            const [x0, x1] = event.selection;
            selectedRange = [xScale.invert(x0), xScale.invert(x1)];
        });

        d3.select(brushGroup).call(brush);
    }

    $: selectedData = selectedRange
        ? data.filter(d => d.date >= selectedRange[0] && d.date <= selectedRange[1])
        : data;
</script>

{#if data.length}
  <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="auto">
    <!-- x-axis -->
    <g transform={`translate(0, ${height - margin.bottom})`}>
      <line x1={margin.left} x2={width - margin.right} stroke="black" />

      {#each xTicks as tick}
        <g transform={`translate(${xScale(tick)}, 0)`}>
          <line y2="6" stroke="black" />
          <text y="22" text-anchor="middle">{d3.timeFormat('%Y')(tick)}</text>
        </g>
      {/each}
    </g>

    <!-- y-axis -->
    <g transform={`translate(${margin.left}, 0)`}>
      <line y1={margin.top} y2={height - margin.bottom} stroke="black" />

      {#each yTicks as tick}
        <g transform={`translate(0, ${yScale(tick)})`}>
          <line x2="-6" stroke="black" />
          <text x="-10" dy="0.32em" text-anchor="end">{tick}</text>
        </g>
      {/each}
    </g>

    <!-- line -->
    <path
      d={line(data)}
      fill="none"
      stroke="black"
      stroke-width="2"
    />

    <!-- points -->
    {#each data as d}
      <circle
        cx={xScale(d.date)}
        cy={yScale(d.value)}
        r="3"
        fill="black"
      />
    {/each}

    <!-- brush -->
    <g bind:this={brushGroup}></g>
    {#each data as d}
        <circle
            cx={xScale(d.date)}
            cy={yScale(d.value)}
            r={animate ? 5 : 3}
            fill={animate ? 'crimson' : 'black'}
            opacity={selectedRange === null || selectedData.includes(d) ? 1 : 0.2}
        />
    {/each}
  </svg>
{:else}
  <p>No data available.</p>
{/if}

<style>
  svg {
    max-width: 1000px;
    display: block;
    margin: 0 auto;
    background: white;
  }

  text {
    font-size: 12px;
    font-family: sans-serif;
  }
</style>