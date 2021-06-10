

async function stackedBarChart(mode = "day") {
  // get width of the div where the svg will be drawn
  
  const chartDiv = d3.select('#stackedChart')
  const width = chartDiv.node().getBoundingClientRect().width;
  // get raw bat data provided by the database
  const batData = await getAllBatData();
  // transform to stacked data for d3
  const series = prepareStackedBatData(batData, mode);
  
  // color Scale
  const color = d3.scaleOrdinal()
                  .domain(series.map(d => d.key))
                  .range(d3.quantize(t => d3.interpolateViridis(t), series.length));
  
  // set properties of svg
  const margin = ({top:10, right: 10, bottom: 20, left: 40});
  const height = 300;

  // define xScale
  let x = getX(series, margin, width, mode);
  
  let xRef = x.copy();
  
  //define daterange
  const daterange = getDateRange(x, mode);
  
  let xBand = d3.scaleBand().domain(daterange)
                  .range([margin.left, width - margin.right])
                  .padding(0.1);
  // define yScale
  let y = d3.scaleLinear()
              .domain([0, d3.max(series, d => d3.max(d, d => d[1])) * 1.1])
              .range([height - margin.bottom, margin.top]);

  let yRef = y.copy();
  // define xAxis
  function xAxis(g, xScale, mode) {
      // set the number of ticks depending on the length of the x-axis in time; max 8 ticks
      let numberOfTicks = (getDateRange(xScale, mode).length > 8) ? 8 : getDateRange(xScale, mode).length;
      return g.attr("transform", `translate(0,${height - margin.bottom})`)
          .call(d3.axisBottom(xScale).tickSizeOuter(0).ticks(numberOfTicks))
          .call(g => g.selectAll(".domain").remove());     
  }

  // define yAxis
  function yAxis(g, yScale) {
      return g.attr("transform", `translate(${margin.left},0)`)
          .call(d3.axisLeft(yScale).ticks(null, "s"))
          .call(g => g.selectAll(".domain").remove())
          .attr('stroke-opacity', 0.2);
  }

  // define grid
  function grid(g, yScale) {
      d3.selectAll("line").remove();
      return g.attr("stroke", "currentColor")
          .attr("stroke-opacity", 0.1)
          .call(g => g.append("g")
              .selectAll("line")
              .data(yScale.ticks())
              .join("line")
              .attr("y1", d => 0.5 + yScale(d))
              .attr("y2", d => 0.5 + yScale(d))
              .attr("x1", margin.left)
              .attr("x2", width - margin.right));
  }



  // define legend
  const leg = legend({color: color, title: "Bat species"});
  
  // add svg to the specified div-element
  const svg = chartDiv
                .html(leg.outerHTML)
                .append('svg')
                .attr('viewBox', [0, 0, width, height]);

  const gx = svg.append("g");
  const gy = svg.append("g");
  
  let clippath = svg.append('defs').append("clipPath")
  .attr("id", "clip")
  .append("rect")
  .attr("x",margin.left)
  .attr("y",margin.top)
  .attr("width",width - margin.left - margin.right)
  .attr("height",height - margin.top - margin.bottom);

  let rect = svg.append('g')
      .attr("clip-path", "url(#clip)")
      .selectAll('g')
      .data(series, d => d.key)    
    .join('g')
      .attr('fill', d => color(d.key))
      .classed('bars', true)
      .classed('stacked', true)
    .selectAll('rect')    
      .data(d => d, d => d.data.date)
    .join('rect')
      .attr('x', (d, i) => x(d.data.date))
      // .attr('x', (d, i) => x(d.data.date) - xBand.bandwidth()/2)
      .attr('y', d => y(d[1]))
      .attr('height', d => y(d[0]) - y(d[1]))
      .attr('width', xBand.bandwidth())
      //.attr('width', (width-margin.left-margin.right)/x.ticks().length)
      .classed('rects', true)
        .on("mouseover", mouseover)
        .on("mousemove", mousemove)
        .on("mouseleave", mouseleave);

  // z holds a copy of the previous transform, so we can track its changes
  let z = d3.zoomIdentity;
  const extent = [[margin.left,0], [width - margin.right, height - margin.bottom]];

  // set up the ancillary zooms and an accessor for their transforms
  const zoomX = d3.zoom().scaleExtent([1, daterange.length]).translateExtent(extent).extent(extent);
  const zoomY = d3.zoom().scaleExtent([1, daterange.length]).translateExtent(extent).extent(extent);
  const tx = () => d3.zoomTransform(gx.node());
  const ty = () => d3.zoomTransform(gy.node());
  gx.call(zoomX).attr("pointer-events", "none");
  gy.call(zoomY).attr("pointer-events", "none");

  // active zooming
  const zoom = d3.zoom().on("zoom", function(e) {
    const t = e.transform;
    const k = t.k / z.k;
    const point = center(e, this);

    // is it on an axis? is the shift key pressed?
    const doX = point[0] > x.range()[0];
    const doY = point[1] < y.range()[0];
    const shift = e.sourceEvent && e.sourceEvent.shiftKey;

    if (k === 1) {
      // pure translation?
      doX && gx.call(zoomX.translateBy, (t.x - z.x) / tx().k, 0);
      doY && gy.call(zoomY.translateBy, 0, (t.y - z.y) / ty().k);
    } else {
      // if not, we're zooming on a fixed point
      doX && gx.call(zoomX.scaleBy, shift ? 1 / k : k, point);
      doY && gy.call(zoomY.scaleBy, k, point);
  }
  
    z = t;

    redraw();
  });


  // define the div for the tooltip
  const tooltip = chartDiv
    .append("div")
    .style("opacity", 0)
    .attr("class", "tooltip")
    .style("background-color", "white")
    .style("border", "solid")
    .style("border-width", "2px")
    .style("border-radius", "5px")
    .style("padding", "5px");

    // Three function that change the tooltip when user hover / move / leave a cell
    // adapted from https://www.d3-graph-gallery.com/graph/interactivity_tooltip.html#template
  function mouseover(event) {
    tooltip
      .style("opacity", 1)
    d3.select(this)
      .style("stroke", "black")
      .style("opacity", 1)
  }
  function mousemove(event) {      
    let date = this.__data__.data.date;
    let value = this.__data__[1] - this.__data__[0];
    let key = this.__data__['key'];
    tooltip
      .html(`${formatDate(date, mode)}: ${value}x ${key}`)
      .style("left", (d3.pointer(event, this)[0]+70) + "px")
      .style("top", (d3.pointer(event, chartDiv)[1]) + "px")
      .style("font-weight", "bold")
  }
  function mouseleave(event) {
    tooltip
      .style("opacity", 0)
    d3.select(this)
      .style("stroke", "none")
      // .style("opacity", 0.8)
  }
  
  // add the grid to the svg   
  svg.append('g')
    .classed('grid', true)
    .call(grid, y);

  function adjustTextLabels(g){
    if (mode == "month") {
    g.selectAll('.x-axis .tick text')
      .attr('transform', `translate(${daysToPixels(1) / 2})`);
    }
  }

  function daysToPixels(days){
    var d1 = new Date();
    return x(d3.timeMonth.offset(d1, days)) - x(d1);
  }


  // function to transform from stacked to grouped
  function transitionGrouped() {
    const xr = tx().rescaleX(x);
    const yr = ty().rescaleY(y);
    // adjust y-axis
    // y.domain([0, d3.max(_.flatMapDeep(series, d => _.map(d, d=> d[1] - d[0])))*1.1]);
    // change class of bars
    svg.selectAll('.bars').classed('grouped', true);
    svg.selectAll('.bars').classed('stacked', false);
    let n = series.length;
    // change position of the rects through transition
    rect.transition()
        .duration(500)
        .delay((d, i) => i * 20)
        .attr("x", (d, i) => xr(d.data.date) + xBand.bandwidth() / n * d.index)
        // .attr("x", (d, i) => x(d.data.date) - xBand.bandwidth()/2 + xBand.bandwidth() / n * d.index)
        .attr("width", xBand.bandwidth() / n)
      .transition()
        .attr("y", d => yr(d[1] - d[0]))
        .attr("height", d => yr(0) - yr(d[1] - d[0]));
    // update y-axis and grid
    svg.selectAll(".y-axis").call(yAxis, yr);
    svg.selectAll('.grid').selectAll('g').remove();
    svg.selectAll(".grid").call(grid, yr);
  }

  // function to transform from grouped to stacked 
  function transitionStacked() {
    const xr = tx().rescaleX(x);
    const yr = ty().rescaleY(y);
    // adjust y-axis
    // y.domain([0, d3.max(_.flatMapDeep(series, d => _.map(d, d=> d[1])))*1.1]);
    // change class of bars
    svg.selectAll('.bars').classed('stacked', true);
    svg.selectAll('.bars').classed('grouped', false);
    // change position of the rects through transition
    rect.transition()
        .duration(500)
        .delay((d, i) => i * 20)
        .attr("y", d => yr(d[1]))
        .attr("height", d => yr(d[0]) - yr(d[1]))
      .transition()
        .attr("x", (d, i) => xr(d.data.date))
        // .attr("x", (d, i) => x(d.data.date) - xBand.bandwidth()/2)
        .attr("width", xBand.bandwidth());
    // update y-axis and grid
    svg.selectAll(".y-axis").call(yAxis, yr);
    svg.selectAll('.grid').selectAll('g').remove();
    svg.selectAll('.grid').call(grid, yr);
  }

  function updateStyle(layout) {
    if (layout === "stacked") transitionStacked();
    else transitionGrouped();
  }
  
  function redraw() {
    let n = series.length;
    const xr = tx().rescaleX(x);
    const yr = ty().rescaleY(y);
    gx.call(xAxis, xr, mode).call(adjustTextLabels);
    gy.call(yAxis, yr);
    xBand.domain(getDateRange(xr, mode))
       
    svg.selectAll(".grid").call(grid, yr)
        
    svg.selectAll(".stacked rect")
      .attr("x", d => xr(d.data.date))
      .attr("width", xBand.bandwidth())
      .attr("y", d => yr(d[1]))
      .attr("height", d => yr(d[0]) - yr(d[1]));
    
    svg.selectAll(".grouped rect")
      .attr("x", d => xr(d.data.date) + xBand.bandwidth() / n * d.index)
      .attr("width", xBand.bandwidth() / n)
      .attr("y", d => yr(d[1]-d[0]))
      .attr("height", d => yr(0) - yr(d[1] - d[0]));
    
  }

  function center(event, target) {
    if (event.sourceEvent) {
      const p = d3.pointers(event, target);
      return [d3.mean(p, d => d[0]), d3.mean(p, d => d[1])];
    }
    return [width / 2, height / 2];
  }

  return Object.assign(svg.call(zoom).call(zoom.transform, d3.zoomIdentity.scale(0.8)).node(), {updateStyle});      
}


// prepare the data from the database for the use in the graphic
function prepareStackedBatData(data, mode) {    
  const parseTime = d3.timeParse('%Y-%m-%d %H:%M:%S%Z');
  // group raw data by date
  function resol(data, mode) {
    if (mode == "day") {
      return d3.timeDay(d3.timeHour.offset(data, -12));
    } else if (mode == "hour") {
      return d3.timeHour(data);
    } else if (mode == "month") {
      return d3.timeMonth(d3.timeHour.offset(data, -12));
    } 
  }
  
  let d_g_date = _.groupBy(data, d => resol(parseTime(d.datetime), mode))
  
  // transform to array of objects where each objects holds date and number of detected  bats per species
  const d_stacked = _.reduce(d_g_date, function(result, value, key) {
        (result || result[0]).push(
              Object.assign({date: resol(parseTime(value[0].datetime), mode)}, _.countBy(value, d => d.auto_batid))
            );
        
        return result;
      }, []);
  
  // add array with column names (called columns) to data object
  Object.assign(d_stacked, {colums: _.uniqBy(_.flatten(d3.map(d_stacked, d => Object.keys(d))))});
  
  // transform to stacked data format by d3
  series = d3.stack()
          .keys(d_stacked.colums.slice(1))(d_stacked)
          .map(d => (d.forEach(v => v.key = d.key), d))
          .map(d => (d.forEach(v => v.index = d.index), d));
  return series
}

// function to format the date for the tooltip
function formatDate(date, mode) {
  if (mode == "day") {
      return date.toLocaleString("en", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } else if (mode == "hour") {
      let date_offset = d3.timeHour.offset(date)
      let d1 = date.toLocaleString("en", {
        month: "short",
        day: "numeric",
        year: "numeric",
        // hour12: false,
        hour: "numeric",
        minute:"numeric",
      });
      let d2 = date_offset.toLocaleString("en", {
        // hour12: false,
        hour:"numeric",
        minute:"numeric"
      });
      return `${d1} - ${d2}`
    } else if (mode =="month") {
      return date.toLocaleString("en", {
        month: "short",
        year: "numeric",
      });
    }
    
  }
// calculate daterange
function getDateRange(x, mode) {
  let daterange;
  if (mode == "day") {
    daterange = d3.timeDays(x.domain()[0], x.domain()[1])
  } else if (mode == "hour") {
    daterange = d3.timeHours(x.domain()[0], x.domain()[1])
  } else if (mode == "month") {
    daterange = d3.timeMonths(x.domain()[0], x.domain()[1])
  }
  return daterange;
}
// x-axis(mode)-dependent time-offset
function timeOffset(data, mode, offset = 1) {
  if (mode == "day") {
    return d3.timeDay.offset(data, offset);
  } else if (mode == "hour") {
    return d3.timeHour.offset(data, offset);
  } else if (mode == "month") {
    return d3.timeMonth.offset(data, offset);
  } 
}

// define xScale depending on xAxis resolution
// always one time-unit more in both directions
function getX(series, margin, width, mode) {

  const x = d3.scaleTime()  
              .domain([timeOffset(d3.min(_.uniq(series.flatMap(d => d.map(d => d.data.date)))), mode, offset = -1),
                timeOffset(d3.max(_.uniq(series.flatMap(d => d.map(d => d.data.date)))), mode, offset = 2)])
              .range([margin.left, width - margin.right]);
  return x;
}

// according to the style options the graph is changed
function changeChartStyle(updateOption) {
  stackedChart.updateStyle(updateOption.value);
}

// if chartResolution is changed, the graphic will be redrawn
async function changeChartResolution(resOption) {
  stackedChart = await stackedBarChart(resOption.value)
  document.getElementById('design_Option').selectedIndex = 0;
}
  

// color Legend from https://observablehq.com/@d3/color-legend

  function legend({
    color,
    title,
    tickSize = 6,
    // width = d3.select('#stackedChart').node().getBoundingClientRect().width / 4,
    width = 320, 
    height = 44 + tickSize,
    marginTop = 18,
    marginRight = 0,
    marginBottom = 16 + tickSize,
    marginLeft = 0,
    ticks = width / 64,
    tickFormat,
    tickValues
  } = {}) {
  
    const svg = d3.create("svg")
        .attr("width", width)
        .attr("height", height)
        .attr("viewBox", [0, 0, width, height])
        .style("overflow", "visible")
        .style("display", "block");
  
    let tickAdjust = g => g.selectAll(".tick line").attr("y1", marginTop + marginBottom - height);
      
    let x = d3.scaleBand()
        .domain(color.domain())
        .rangeRound([marginLeft, width - marginRight]);
    
    svg.append("g")
      .selectAll("rect")
      .data(color.domain())
      .join("rect")
        .attr("x", x)
        .attr("y", marginTop)
        .attr("width", Math.max(0, x.bandwidth() - 1))
        .attr("height", height - marginTop - marginBottom)
        .attr("fill", color);
    
    tickAdjust = () => {};
  
    svg.append("g")
        .attr("transform", `translate(0,${height - marginBottom})`)
        .call(d3.axisBottom(x)
          .ticks(ticks, typeof tickFormat === "string" ? tickFormat : undefined)
          .tickFormat(typeof tickFormat === "function" ? tickFormat : undefined)
          .tickSize(tickSize)
          .tickValues(tickValues))
        .call(tickAdjust)
        .call(g => g.select(".domain").remove())
        .call(g => g.append("text")
          .attr("x", marginLeft)
          .attr("y", marginTop + marginBottom - height - 6)
          .attr("fill", "currentColor")
          .attr("text-anchor", "start")
          .attr("font-weight", "bold")
          .attr("class", "label")
          .text(title));
  
    return svg.node();
  }

  async function getAllBatData() {
    try {
      let response = await fetch('/get_all_bat_data/')
      let batData = await response.json();
      return batData
    } catch (err) {
      console.log(err)
    }
  }

