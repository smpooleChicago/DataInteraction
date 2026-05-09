<script>
  import * as d3 from 'd3';
  import { onMount } from 'svelte';
  import Map from './Map.svelte';
  import TimeSeries from './TimeSeries.svelte';

  const example_timeData = [
    { date: new Date('2020-01-01'), value: 10 },
    { date: new Date('2021-01-01'), value: 25 },
    { date: new Date('2022-01-01'), value: 18 },
    { date: new Date('2023-01-01'), value: 40 },
    { date: new Date('2024-01-01'), value: 32 }
  ];

  let geoFeatures = [];

  onMount(async () => {
    const geojson = await d3.json('countries.geo.json');

    geoFeatures = geojson.features.map((feature) => ({
      ...feature,
      properties: {
        ...feature.properties,
        name: feature.properties.name
      }
    }));
  });

  // For animation
  let animate = false; //for button

  function startAnimation() {
    animate = true;
  }

  function resetAnimation() {
    animate = false;
  }
</script>

<main>
  <h1>World Map</h1>

  <button on:click={startAnimation}>Animate</button>
  <button on:click={resetAnimation}>Reset</button>

  <div class="map-container">
    <Map data={geoFeatures} />
  </div>

  <div class="timeSeries-container">
    <TimeSeries data={example_timeData} />
  </div>
</main>

<style>
  main {
    max-width: 900px;
    margin: 0 auto;
    padding: 24px;
    font-family: sans-serif;
  }

  h1 {
    text-align: center;
  }

  p {
    text-align: center;
  }

  .map-container {
    display: flex;
    justify-content: center;
  }
</style>