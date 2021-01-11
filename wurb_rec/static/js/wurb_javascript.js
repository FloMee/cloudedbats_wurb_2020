
window.onload = async function () {
  // Define global variables.

  // Recording unit tile.
  const rec_start_button_id = document.getElementById("rec_start_button_id");
  const rec_stop_button_id = document.getElementById("rec_stop_button_id");
  const rec_status_id = document.getElementById("rec_status_id");
  const rec_info_id = document.getElementById("rec_info_id");
  const rec_detector_time_id = document.getElementById("rec_detector_time_id");
  const rec_log_table_id = document.getElementById("rec_log_table_id");

  // Geographic location tile.
  const geo_source_option_id = document.getElementById("geo_source_option_id");
  const latitude_dd_id = document.getElementById("latitude_dd_id");
  const longitude_dd_id = document.getElementById("longitude_dd_id");
  const geo_set_pos_button_id = document.getElementById("geo_set_pos_button_id");
  const save_location_button_text_id = document.getElementById("save_location_button_text_id");
  const geo_set_time_button_id = document.getElementById("geo_set_time_button_id");

  // Settings tile. Tab hide/show.
  const tab_settings_basic_id = document.getElementById("tab_settings_basic_id");
  const tab_settings_more_id = document.getElementById("tab_settings_more_id");
  const tab_settings_scheduler_id = document.getElementById("tab_settings_scheduler_id");
  const div_settings_basic_id = document.getElementById("div_settings_basic_id");
  const div_settings_more_id = document.getElementById("div_settings_more_id");
  const div_settings_scheduler_id = document.getElementById("div_settings_scheduler_id");
  // const div_settings_clear_sd_confirm_id = document.getElementById("div_settings_clear_sd_confirm_id");
  const div_settings_software_update_id = document.getElementById("div_settings_software_update_id");

  // Fields and buttons.
  const settings_rec_mode_id = document.getElementById("settings_rec_mode_id");
  const settings_filename_prefix_id = document.getElementById("settings_filename_prefix_id");
  const settings_detection_limit_id = document.getElementById("settings_detection_limit_id");
  const settings_detection_sensitivity_id = document.getElementById("settings_detection_sensitivity_id");
  const settings_file_directory_id = document.getElementById("settings_file_directory_id");
  const settings_detection_algorithm_id = document.getElementById("settings_detection_algorithm_id");
  const settings_rec_length_id = document.getElementById("settings_rec_length_id");
  const settings_rec_type_id = document.getElementById("settings_rec_type_id");
  const settings_scheduler_start_event_id = document.getElementById("settings_scheduler_start_event_id");
  const settings_scheduler_start_adjust_id = document.getElementById("settings_scheduler_start_adjust_id");
  const settings_scheduler_stop_event_id = document.getElementById("settings_scheduler_stop_event_id");
  const settings_scheduler_stop_adjust_id = document.getElementById("settings_scheduler_stop_adjust_id");
  const settings_scheduler_post_action_id = document.getElementById("settings_scheduler_post_action_id");
  const settings_scheduler_post_action_delay_id = document.getElementById("settings_scheduler_post_action_delay_id");
  const settings_save_button_id = document.getElementById("settings_save_button_id");
  const settings_reset_button_id = document.getElementById("settings_reset_button_id");
  const settings_default_button_id = document.getElementById("settings_default_button_id");


  
  // Update stored location and settings.
  getLocation()
  getSettings()
  // Check geolocation:
  geoLocationSourceOnChange(update_detector = false);

  // Start websocket.
  var ws_url = (window.location.protocol === "https:") ? "wss://" : "ws://"
  ws_url += window.location.host // Note: Host includes port.
  ws_url += "/ws";
  startWebsocket(ws_url);
  mychart = await drawBarChart();
  
};


//Solution with Chart.js

async function drawBarChart() {
  const batdata = await getBatData2();
  const ctx = document.getElementById('Mychart').getContext('2d');
  const myChart = new Chart(ctx, {
    type: 'bar',
    data: {
        labels: batdata.bats,
        datasets: [{
            label: 'Number of detected bats per species',
            data: batdata.amount,
            backgroundColor: 'rgba(39, 147, 218, 0.8)',
            borderColor: 'rgba(39, 147, 218, 1)',
            borderWidth: 1
        }]
    },
    options: {
      scales: {
          yAxes: [{
              ticks: {
                  beginAtZero: true,
                  precision: 0,
              }
          }]
      },
      tooltips: {
        displayColors: false,
      },
      onClick: (evt, item) => {
        if (item[0]) {
          let index = item[0]["_index"];
          let bat = item[0]["_chart"].data.labels[index];
          getPathData(bat);
          let amount = item[0]["_chart"].data.datasets[0].data[index];
        }
      }
    },
  });
return myChart;
}

async function drawScatterPlot() {
  const scatterData = await getScatterData();
  const ctx = document.getElementById('ScatterPlot').getContext('2d');
  const myChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: scatterData.dates,
        datasets: [{
            label: 'Number of detected bats per day',
            data: scatterData.amount,
            fill : false,
            showLine: false,
            backgroundColor: 'rgba(39, 147, 218, 0.8)',
            borderColor: 'rgba(39, 147, 218, 1)',       
        }]
    },
    options: {
      scales: {
          yAxes: [{
              ticks: {
                  beginAtZero: true,
                  precision: 0,
              }
          }]
      },
    },   
  });
return myChart;
}

async function drawStackedBarChart() {
  const scatterData = await getScatterData();
  const ctx = document.getElementById('ScatterPlot').getContext('2d');
  const myChart = new Chart(ctx, {
    type: 'bar',
    data: {
        labels: scatterData.dates,
        datasets: [{
            label: 'Number of detected bats per day',
            data: scatterData.amount,
            fill : false,
            showLine: false,
            backgroundColor: 'rgba(39, 147, 218, 0.8)',
            borderColor: 'rgba(39, 147, 218, 1)',                  
        }],
        stack: scatterData.bat,
    },
    options: {
      scales: {
          yAxes: [{
              ticks: {
                  beginAtZero: true,
                  precision: 0,
              },
              stacked: true
          }],
          xAxes: [{
              stacked: true
          }]
      },
    },   
  });
return myChart;
}

// Solution with D3
async function graph() {
  const batData = await getBatData();
  const xScale = d3.scaleBand().domain(batData.map(d => d.bat)).rangeRound([0,250]).padding(0.1);
  const yScale = d3.scaleLinear().domain([0, 15]).range([0, 200]);

  const container = d3.select('svg')
    .classed('container', true);

  const bars = container
    .selectAll('.bar')
    .data(batData)
    .enter()
    .append('rect')
    .classed('bar', true)
    .attr('width', xScale.bandwidth())
    .attr('height', (data) => 200 - yScale(data.amount))
    .attr('x', data => xScale(data.bat))
    .attr('y', data => yScale(data.amount));
  }

function updateGraph(bat_detected) {
  const bat_idx = mychart.data['labels'].indexOf(bat_detected.bat)
  if (bat_idx == -1) {
    // bat not yet in graph --> add
    mychart.data['labels'].push(bat_detected.bat)
    //console.log(amount)
    mychart.data.datasets[0].data.push(bat_detected.amount)
  } else {
    mychart.data.datasets[0].data[bat_idx] += bat_detected.amount
  }

  mychart.update()
}

async function getPathData(bat) {
  try {
    let response = await fetch("/get_path_data/"+bat)
    let pathData = await response.json();
    d3.select('#pathlist')
      .selectAll('li')
      .data(pathData, data => data.filepath)
      .enter()
      .append('li')
      .text(data => ("filepath: " + data.filepath +" Probability: " + data.prob));
    d3.select('#pathlist')
      .selectAll('li')
      .data(pathData, data => data.filepath)
      .exit()
      .remove();

  } catch (err) {
    console.log(err)
  }
}

function changeStyle() {
  d3.selectAll('p').style('font-size', Math.random()* 30 + 'px');
}

function hideDivision(div_id) {
  if (div_id != 'undefined') {
    div_id.style.visibility = "hidden";
    div_id.style.overflow = "hidden";
    div_id.style.height = "0";
    div_id.style.width = "0";
  }
};

function showDivision(div_id) {
  if (div_id != 'undefined') {
    div_id.style.visibility = null;
    div_id.style.overflow = null;
    div_id.style.height = null;
    div_id.style.width = null;
  }
};

function hideShowSettingsTabs(tab_name) {
  tab_settings_basic_id.classList.remove("is-active");
  tab_settings_more_id.classList.remove("is-active");
  tab_settings_scheduler_id.classList.remove("is-active");
  hideDivision(div_settings_basic_id)
  hideDivision(div_settings_more_id)
  hideDivision(div_settings_scheduler_id)

  if (tab_name == "basic") {
    tab_settings_basic_id.classList.add("is-active");
    showDivision(div_settings_basic_id)
  } else if (tab_name == "more") {
    tab_settings_more_id.classList.add("is-active");
    showDivision(div_settings_more_id)
  } else if (tab_name == "scheduler") {
    tab_settings_scheduler_id.classList.add("is-active");
    showDivision(div_settings_scheduler_id)
  };
};

function geoLocationSourceOnChange(update_detector) {
  let selected_value = geo_source_option_id.options[geo_source_option_id.selectedIndex].value
  save_location_button_text_id.innerHTML = "Save"
  if (selected_value == "geo-not-used") {
    latitude_dd_id.value = "0.0";
    longitude_dd_id.value = "0.0";
    latitude_dd_id.disabled = true;
    longitude_dd_id.disabled = true;
    geo_set_pos_button_id.disabled = true;
    geo_set_time_button_id.disabled = false;
    if (update_detector) {
      saveLocationSource()
    }
  }
  else if (selected_value == "geo-manual") {
    getManualLocation();
    save_location_button_text_id.innerHTML = "Save lat/long"
    latitude_dd_id.disabled = false;
    longitude_dd_id.disabled = false;
    geo_set_pos_button_id.disabled = false;
    geo_set_time_button_id.disabled = false;
    if (update_detector) {
      saveLocationSource()
    }
  }
  else if (selected_value == "geo-client-gps") {
    activateGeoLocation()
    latitude_dd_id.disabled = true;
    longitude_dd_id.disabled = true;
    geo_set_pos_button_id.disabled = false;
    geo_set_time_button_id.disabled = false;
    if (update_detector) {
      saveLocationSource()
    }
  }
  else if (selected_value == "geo-usb-gps") {
    save_location_button_text_id.innerHTML = "Use as manual"
    latitude_dd_id.disabled = true;
    longitude_dd_id.disabled = true;
    geo_set_pos_button_id.disabled = false;
    geo_set_time_button_id.disabled = false;
    if (update_detector) {
      saveLocationSource()
    }
  }
  else {
    latitude_dd_id.disabled = true;
    longitude_dd_id.disabled = true;
    geo_set_pos_button_id.disabled = true;
    geo_set_time_button_id.disabled = false;
  }
}

function activateGeoLocation() {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(showPosition, errorCallback, { timeout: 10000 });
    // navigator.geolocation.getCurrentPosition(showLocation);
    // navigator.geolocation.watchPosition(showLocation);
    // navigator.geolocation.clearWatch(showLocation);
  } else {
    alert(`Geo location from client:\nNot supported by this browser.`);
  };
};
function showPosition(location) {
  rec_info_id.innerHTML = location.coords.latitude;
  latitude_id.value = location.coords.latitude;
  longitude_id.value = location.coords.longitude;
};
function errorCallback(error) {
  alert(`Geo location from client:\nERROR(${error.code}): ${error.message}`);
};

async function startRecording() {
  try {
    document.getElementById("rec_status_id").innerHTML = "Waiting...";
    // Save settings before recording starts.
    saveSettings()
    await fetch('/start-rec/');
  } catch (err) {
    alert(`ERROR startRecording: ${err}`);
    console.log(err);
  };
};

async function stopRecording(action) {
  try {
    document.getElementById("rec_status_id").innerHTML = "Waiting...";
    await fetch('/stop-rec/');
  } catch (err) {
    alert(`ERROR stopRecording: ${err}`);
    console.log(err);
  };
};

async function recModeOnChange() {
  try {
    let recmode = settings_rec_mode_id.value;
    let url_string = `/save-rec-mode/?recmode=${recmode}`;
    await fetch(url_string);
  } catch (err) {
    alert(`ERROR recModeOnChange: ${err}`);
    console.log(err);
  };
};

async function saveLocationSource() {
  try {
    let location = {
      geo_source_option: geo_source_option_id.value,
      latitude_dd: latitude_dd_id.value,
      longitude_dd: longitude_dd_id.value,
    }
    await fetch("/save-location/",
      {
        method: "POST",
        body: JSON.stringify(location)
      })
  } catch (err) {
    alert(`ERROR saveLocation: ${err}`);
    console.log(err);
  };
};

async function saveLocation() {
  try {
    let location = {
      geo_source_option: geo_source_option_id.value,
      latitude_dd: latitude_dd_id.value,
      longitude_dd: longitude_dd_id.value,
    }
    if (geo_source_option_id.value == "geo-manual") {
      location["manual_latitude_dd"] = latitude_dd_id.value
      location["manual_longitude_dd"] = longitude_dd_id.value
    }
    if (geo_source_option_id.value == "geo-usb-gps") {
      location["geo_source_option"] = "geo-manual"
      location["manual_latitude_dd"] = latitude_dd_id.value
      location["manual_longitude_dd"] = longitude_dd_id.value
    }
    await fetch("/save-location/",
      {
        method: "POST",
        body: JSON.stringify(location)
      })
  } catch (err) {
    alert(`ERROR saveLocation: ${err}`);
    console.log(err);
  };
};

async function getBatData() {
  try {
    let response = await fetch("/get_bat_data/")
    let batData = await response.json();
    console.log(batData)
    return batData
  } catch (err) {
    console.log(err)
  }
}

async function getBatData2() {
  try {
    const bats = []
    const amount = []
    let response = await fetch("/get_bat_data/")
    let batData = await response.json();
    for (var i=0; i<batData.length; i++){
      bats.push(batData[i].bat);
      amount.push(batData[i].amount);
    }
    console.log(batData)
    return {bats, amount}
  } catch (err) {
    console.log(err)
  }
}

async function getScatterData() {
  try {
    const dates = []
    const amount = []
    const bat = []
    let response = await fetch("/get_scatter_data/")
    let scatterData = await response.json();
    console.log(scatterData)
    for (var i=0; i<scatterData.length; i++){
      dates.push(scatterData[i].date);
      amount.push(scatterData[i].amount);
      bat.push(scatterData[i].bat);
    }
    console.log(scatterData)
    return {dates, amount}
  } catch (err) {
    console.log(err)
  }
}

async function getLocation() {
  try {
    let response = await fetch("/get-location/");
    let data = await response.json();
    updateLocation(data);
  } catch (err) {
    alert(`ERROR getLocation: ${err}`);
    console.log(err);
  };
};

async function getManualLocation() {
  try {
    let response = await fetch("/get-location/");
    let location = await response.json();
    latitude_dd_id.value = location.manual_latitude_dd
    longitude_dd_id.value = location.manual_longitude_dd
  } catch (err) {
    alert(`ERROR getManualLocation: ${err}`);
    console.log(err);
  };
};

async function setDetectorTime() {
  try {
    let posix_time_ms = new Date().getTime();
    // let url_string = "/set_time/?posixtime=" + posix_time_ms;    
    let url_string = `/set-time/?posixtime=${posix_time_ms}`;
    await fetch(url_string);
  } catch (err) {
    alert(`ERROR setDetectorTime: ${err}`);
    console.log(err);
  };
};

async function saveSettings() {
  try {
    let settings = {
      rec_mode: settings_rec_mode_id.value,
      filename_prefix: settings_filename_prefix_id.value,
      detection_limit: settings_detection_limit_id.value,
      detection_sensitivity: settings_detection_sensitivity_id.value,
      file_directory: settings_file_directory_id.value,
      detection_algorithm: settings_detection_algorithm_id.value,
      rec_length_s: settings_rec_length_id.value,
      rec_type: settings_rec_type_id.value,
      scheduler_start_event: settings_scheduler_start_event_id.value,
      scheduler_start_adjust: settings_scheduler_start_adjust_id.value,
      scheduler_stop_event: settings_scheduler_stop_event_id.value,
      scheduler_stop_adjust: settings_scheduler_stop_adjust_id.value,
      scheduler_post_action: settings_scheduler_post_action_id.value,
      scheduler_post_action_delay: settings_scheduler_post_action_delay_id.value,
    }
    await fetch("/save-settings/",
      {
        method: "POST",
        body: JSON.stringify(settings)
      })
  } catch (err) {
    alert(`ERROR saveSettings: ${err}`);
    console.log(err);
  };
};

async function getSettings() {
  try {
    let response = await fetch("/get-settings/?default=false");
    let data = await response.json();
    updateSettings(data);
  } catch (err) {
    alert(`ERROR getSettings: ${err}`);
    console.log(err);
  };
};

async function getDefaultSettings() {
  try {
    let response = await fetch("/get-settings/?default=true");
    let data = await response.json();
    updateSettings(data);
  } catch (err) {
    alert(`ERROR getDefaultSettings: ${err}`);
    console.log(err);
  };
};

async function raspberryPiControl(command) {
  try {
    // if (command == "rpi_clear_sd") {
    //   showDivision(div_settings_clear_sd_confirm_id)
    // } else {
    //   hideDivision(div_settings_clear_sd_confirm_id)
    //   if (command != "rpi_clear_sd") { // 
    //     let url_string = `/rpi-control/?command=${command}`;
    //     await fetch(url_string);
    //   }
    // }
    if (command == "rpi_sw_update_dialog") {
      showDivision(div_settings_software_update_id)
    } else {
      hideDivision(div_settings_software_update_id)
      if (command != "rpi_sw_update_dialog") {
        if (command != "rpi_sw_update_cancel") {
          let url_string = `/rpi-control/?command=${command}`;
          await fetch(url_string);
        }
      }
    }
  } catch (err) {
    alert(`ERROR raspberryPiControl: ${err}`);
    console.log(err);
  };
};

function updateStatus(status) {
  rec_status_id.innerHTML = status.rec_status;
  rec_info_id.innerHTML = status.device_name;
  rec_detector_time_id.innerHTML = status.detector_time;
}

function updateLocation(location) {
  geo_source_option_id.value = location.geo_source_option
  if (location.geo_source_option == "geo-manual") {
    latitude_dd_id.value = location.manual_latitude_dd
    longitude_dd_id.value = location.manual_longitude_dd
  } else {
    latitude_dd_id.value = location.latitude_dd
    longitude_dd_id.value = location.longitude_dd
  }
  // Check geolocation:
  geoLocationSourceOnChange(update_detector = false);
}

function updateLatLong(latlong) {
  latitude_dd_id.value = latlong.latitude_dd
  longitude_dd_id.value = latlong.longitude_dd
}

function updateSettings(settings) {
  settings_rec_mode_id.value = settings.rec_mode
  settings_filename_prefix_id.value = settings.filename_prefix
  settings_detection_limit_id.value = settings.detection_limit
  settings_detection_sensitivity_id.value = settings.detection_sensitivity
  settings_file_directory_id.value = settings.file_directory
  settings_detection_algorithm_id.value = settings.detection_algorithm
  settings_rec_length_id.value = settings.rec_length_s
  settings_rec_type_id.value = settings.rec_type
  settings_scheduler_start_event_id.value = settings.scheduler_start_event
  settings_scheduler_start_adjust_id.value = settings.scheduler_start_adjust
  settings_scheduler_stop_event_id.value = settings.scheduler_stop_event
  settings_scheduler_stop_adjust_id.value = settings.scheduler_stop_adjust
  settings_scheduler_post_action_id.value = settings.scheduler_post_action
  settings_scheduler_post_action_delay_id.value = settings.scheduler_post_action_delay
}

function updateLogTable(log_rows) {
  html_table_rows = ""
  for (row_index in log_rows) {
    html_table_rows += "<tr><td>"
    html_table_rows += log_rows[row_index]
    html_table_rows += "</tr></td>"
  }
  document.getElementById("rec_log_table_id").innerHTML = html_table_rows
}

function startWebsocket(ws_url) {
  // let ws = new WebSocket("ws://localhost:8000/ws");
  let ws = new WebSocket(ws_url);
  ws.onmessage = function (event) {
    let data_json = JSON.parse(event.data);
    
    if ("status" in data_json === true) {
      updateStatus(data_json.status)
    }
    if ("location" in data_json === true) {
      updateLocation(data_json.location)
      
    }
    if ("latlong" in data_json === true) {
      updateLatLong(data_json.latlong)
    }
    if ("settings" in data_json === true) {
      updateSettings(data_json.settings)
    }
    if ("log_rows" in data_json === true) {
      updateLogTable(data_json.log_rows)
      console.log(data_json)
    }
    if ("bat_detected" in data_json === true) 
      {updateGraph(data_json.bat_detected)
    }
  }
  ws.onclose = function () {
    // Try to reconnect in 5th seconds. Will continue...
    ws = null;
    setTimeout(function () { startWebsocket(ws_url) }, 5000);
  };
};
