<script>
  import * as d3 from 'd3';

  export let data = [];
  export let animate = false;

  const width = 1600;
  const height = 900;

  $: featureCollection = {
    type: 'FeatureCollection',
    features: data
  };

  $: projection = data.length
    ? d3.geoNaturalEarth1().fitSize([width, height], featureCollection)
    : null;

  $: path = projection ? d3.geoPath(projection) : null;

  function countryFill(feature) {
    if (!animate) return 'white';

    if (feature.properties.name === 'Canada') return 'red';
    if (feature.properties.name === 'Brazil') return 'green';

    return '#4DA6FF';
  }
</script>

{#if path && data.length}
  <svg 
  viewBox={`0 0 ${width} ${height}`} 
  width="100%" 
  height="auto">
    <g>
      {#each data as feature}
        <path
          d={path(feature)}
          fill={countryFill(feature)}
          stroke="black"
          stroke-width="0.5"
        />
      {/each}
    </g>
  </svg>
{:else}
  <p>Loading map...</p>
{/if}

<style>
  svg {
    width: 95vw;
    max-width: 90vh;
    height: auto;
    background: white;
    display: block;
    margin: 0 auto;
    overflow: visible;
  }

  path {
    transition: fill 1s ease;
    vector-effect: non-scaling-stroke;
  }
</style>