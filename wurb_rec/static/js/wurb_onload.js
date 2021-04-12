
window.onload = async function () {

  define_global_variables()

  audioFeedbackSliders()

  // Update stored location and settings.
  getLocation()
  getSettings()

  modeSelectOnChange(update_detector = false)

  // Check geolocation:
  geoLocationSourceOnChange(update_detector = false);

  // Start websocket.
  var ws_url = (window.location.protocol === "https:") ? "wss://" : "ws://"
  ws_url += window.location.host // Note: Host includes port.
  ws_url += "/ws";
  startWebsocket(ws_url);

  // alert("Onload done...")

  stackedChart = await stackedBarChart();  

  document.getElementById('design_Option').selectedIndex = 0;
  document.getElementById('xRes_Option').selectedIndex = 1;

};

