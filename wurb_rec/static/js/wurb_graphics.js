

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
  const x = getX(series, margin, width, mode)
  
  //define daterange
  const daterange = getDateRange(x, mode)
  
  // d3.timeDays(x.domain()[0], x.domain()[1])
  
  const xBand = d3.scaleBand().domain(daterange)
                  .range([margin.left, width - margin.right])
                  .padding(0.1)
  // define yScale
  const y = d3.scaleLinear()
              .domain([0, d3.max(series, d => d3.max(d, d => d[1])) * 1.1])
              .range([height - margin.bottom, margin.top]);

  // define xAxis
  function xAxis(g, xScale) {
      return g.attr("transform", `translate(0,${height - margin.bottom})`)
          .call(d3.axisBottom(xScale).tickSizeOuter(0).ticks(10))//.tickFormat(d3.timeFormat('%d.%m.%Y')))
          .call(g => g.selectAll(".domain").remove());
  }
  

  // define yAxis
  function yAxis(g) {
      return g.attr("transform", `translate(${margin.left},0)`)
          .call(d3.axisLeft(y).ticks(null, "s"))
          .call(g => g.selectAll(".domain").remove())
          .attr('stroke-opacity', 0.2);
  }

  // define grid
  function grid(g) {
      return g.attr("stroke", "currentColor")
          .attr("stroke-opacity", 0.1)
          .call(g => g.append("g")
              .selectAll("line")
              .data(y.ticks())
              .join("line")
              .attr("y1", d => 0.5 + y(d))
              .attr("y2", d => 0.5 + y(d))
              .attr("x1", margin.left)
              .attr("x2", width - margin.right));
  }



  // define legend
  const leg = legend({color: color, title: "Bat species"});
  
  const svg = chartDiv
                .html(leg.outerHTML)
                .append('svg')
                .attr('viewBox', [0, 0, width, height])
                .call(zoom);
                
  let rect = svg.append('g')
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
      .attr('y', d => y(d[1]))
      .attr('height', d => y(d[0]) - y(d[1]))
      .attr('width', xBand.bandwidth())
      //.attr('width', (width-margin.left-margin.right)/x.ticks().length)
      .classed('rects', true)
      .on('mouseenter', (event, d) => {
        const key = d.key;
        d3.selectAll('.rects').filter((d,i) => d.key === key).attr('opacity', '0.4');
      })
      .on("mouseleave", () => {rect.attr('opacity', '1')});
    
  
  svg.append('g')
    .classed('x-axis', true)
    .call(xAxis, x);
  
  svg.append('g')
    .call(yAxis);
  
  svg.append('g')
    .call(grid);

  function transitionGrouped() {
    //y.domain([0, yMax]);
    svg.selectAll('.bars').classed('grouped', true);
    svg.selectAll('.bars').classed('stacked', false);
    let n = series.length;
    rect.transition()
        .duration(500)
        .delay((d, i) => i * 20)
        .attr("x", (d, i) => x(d.data.date) + xBand.bandwidth() / n * d.index)
        .attr("width", xBand.bandwidth() / n)
      .transition()
        .attr("y", d => y(d[1] - d[0]))
        .attr("height", d => y(0) - y(d[1] - d[0]));
  }

  function transitionStacked() {
    //y.domain([0, d3.max(series, d => d3.max(d, d => d[1]))]);
    svg.selectAll('.bars').classed('stacked', true);
    svg.selectAll('.bars').classed('grouped', false);
    rect.transition()
        .duration(500)
        .delay((d, i) => i * 20)
        .attr("y", d => y(d[1]))
        .attr("height", d => y(d[0]) - y(d[1]))
      .transition()
        .attr("x", (d, i) => x(d.data.date))
        .attr("width", xBand.bandwidth());
  }

  function zoom(svg) {
    const extent = [[margin.left, margin.top], [width - margin.right, height - margin.top]];
  
    svg.call(d3.zoom()
        .scaleExtent([1, daterange.length])
        .translateExtent(extent)
        .extent(extent)
        .on("zoom", zoomed));
  
    function zoomed(event) {
      let n = series.length;
      let xz = event.transform.rescaleX(x);
      x.range([margin.left, width - margin.right].map(d => event.transform.applyX(d)));
      xBand.range([margin.left, width - margin.right].map(d => event.transform.applyX(d)));
      //svg.selectAll(".bars rect").attr("x", d => x(d.data.date)).attr("width", x.bandwidth());
      svg.selectAll(".grouped rect").attr("x", (d, i) => x(d.data.date) + xBand.bandwidth() / n * d.index).attr("width", xBand.bandwidth() / n);    
      svg.selectAll(".stacked rect").attr("x", d => x(d.data.date)).attr("width", xBand.bandwidth());
      svg.selectAll(".x-axis").call(xAxis, xz);
    }
  }

  function updateStyle(layout) {
    if (layout === "stacked") transitionStacked();
    else transitionGrouped();
  }

  return Object.assign(svg.node(), {updateStyle});      
}


function prepareStackedBatData(data, mode) {    
  const parseTime = d3.timeParse('%Y-%m-%d %H:%M:%S%Z');
  // group raw data to by date
  function resol(data, mode) {
    if (mode == "day") {
      return d3.timeDay(data);
    } else if (mode == "hour") {
      return d3.timeHour(data);
    } else if (mode == "month") {
      return d3.timeMonth(data);
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

function getX(series, margin, width, mode) {

  function timeOffset(data, mode) {
    if (mode == "day") {
      return d3.timeDay.offset(data, 1);
    } else if (mode == "hour") {
      return d3.timeHour.offset(data, 1);
    } else if (mode == "month") {
      return d3.timeMonth.offset(data, 1);
    } 
  }
 
  const x = d3.scaleUtc()  
              .domain([d3.min(_.uniq(series.flatMap(d => d.map(d => d.data.date)))),
                timeOffset(d3.max(_.uniq(series.flatMap(d => d.map(d => d.data.date)))), mode)])
              .range([margin.left, width - margin.right]);
  return x;
}
function changeChartStyle(updateRadio) {
  stackedChart.updateStyle(updateRadio.value);
}

async function changeChartResolution(resRadio) {
  stackedChart = await stackedBarChart(resRadio.value)
  radio_stack.checked = true;  
}
  // color Legend from https://observablehq.com/@d3/color-legend

  function legend({
    color,
    title,
    tickSize = 6,
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
    let x;
  
    // Continuous
    if (color.interpolate) {
      const n = Math.min(color.domain().length, color.range().length);
  
      x = color.copy().rangeRound(d3.quantize(d3.interpolate(marginLeft, width - marginRight), n));
  
      svg.append("image")
          .attr("x", marginLeft)
          .attr("y", marginTop)
          .attr("width", width - marginLeft - marginRight)
          .attr("height", height - marginTop - marginBottom)
          .attr("preserveAspectRatio", "none")
          .attr("xlink:href", ramp(color.copy().domain(d3.quantize(d3.interpolate(0, 1), n))).toDataURL());
    }
  
    // Sequential
    else if (color.interpolator) {
      x = Object.assign(color.copy()
          .interpolator(d3.interpolateRound(marginLeft, width - marginRight)),
          {range() { return [marginLeft, width - marginRight]; }});
  
      svg.append("image")
          .attr("x", marginLeft)
          .attr("y", marginTop)
          .attr("width", width - marginLeft - marginRight)
          .attr("height", height - marginTop - marginBottom)
          .attr("preserveAspectRatio", "none")
          .attr("xlink:href", ramp(color.interpolator()).toDataURL());
  
      // scaleSequentialQuantile doesn’t implement ticks or tickFormat.
      if (!x.ticks) {
        if (tickValues === undefined) {
          const n = Math.round(ticks + 1);
          tickValues = d3.range(n).map(i => d3.quantile(color.domain(), i / (n - 1)));
        }
        if (typeof tickFormat !== "function") {
          tickFormat = d3.format(tickFormat === undefined ? ",f" : tickFormat);
        }
      }
    }
  
    // Threshold
    else if (color.invertExtent) {
      const thresholds
          = color.thresholds ? color.thresholds() // scaleQuantize
          : color.quantiles ? color.quantiles() // scaleQuantile
          : color.domain(); // scaleThreshold
  
      const thresholdFormat
          = tickFormat === undefined ? d => d
          : typeof tickFormat === "string" ? d3.format(tickFormat)
          : tickFormat;
  
      x = d3.scaleLinear()
          .domain([-1, color.range().length - 1])
          .rangeRound([marginLeft, width - marginRight]);
  
      svg.append("g")
        .selectAll("rect")
        .data(color.range())
        .join("rect")
          .attr("x", (d, i) => x(i - 1))
          .attr("y", marginTop)
          .attr("width", (d, i) => x(i) - x(i - 1))
          .attr("height", height - marginTop - marginBottom)
          .attr("fill", d => d);
  
      tickValues = d3.range(thresholds.length);
      tickFormat = i => thresholdFormat(thresholds[i], i);
    }
  
    // Ordinal
    else {
      x = d3.scaleBand()
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
    }
  
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


