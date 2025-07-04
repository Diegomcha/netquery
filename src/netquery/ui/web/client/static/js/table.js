// Get elements from the page
const id = window.location.href.substring(
  window.location.href.lastIndexOf("/") + 1
);

const download = {
  filename: /** @type {HTMLInputElement} */ (
    document.getElementById("downloadFilename")
  ),
  form: /** @type {HTMLFormElement} */ (
    document.getElementById("downloadForm")
  ),
  btn: /** @type {HTMLButtonElement} */ (
    document.getElementById("downloadBtn")
  ),
};
const progress = {
  element: /** @type {HTMLDivElement} */ (
    document.getElementById("progressElement")
  ),
  bar: /** @type {HTMLDivElement} */ (document.getElementById("progressBar")),
  container: /** @type {HTMLDivElement} */ (
    document.getElementById("progressContainer")
  ),
  spinner: /** @type {HTMLDivElement} */ (
    document.getElementById("progressSpinner")
  ),
  stop: /** @type {HTMLButtonElement} */ (
    document.getElementById("progressStop")
  ),
};

// Create table
/** @type {object[]} */
const data = [];
const table = new Tabulator("#table", {
  height: "70vh", // set height of table (in CSS or here), this enables the Virtual DOM and improves render speed dramatically (can be any valid css height value)
  data: data, //assign data to table
  pagination: true,
  layout: "fitColumns", //fit columns to width of table (optional)
  columns: [
    //Define Table Columns
    { title: "Result", field: "result" },
    { title: "File", field: "filename" },
    { title: "Group", field: "group" },
    { title: "Label", field: "label" },
    { title: "Hostname", field: "hostname" },
    { title: "IP", field: "ip" },
    { title: "Device Type", field: "device_type" },
    { title: "Log", field: "log", visible: false, download: true },
  ],
});

const cleanup = () =>
  fetch(`/stream/${id}`, { method: "DELETE" }).catch(() => {});

// Handle download
download.form.addEventListener(
  "submit",
  (e) => {
    e.preventDefault();

    const filename = download.filename.value;
    table.download("csv", filename);
  },
  false
);

// Handle stop
window.addEventListener("beforeunload", cleanup, true);
progress.stop.addEventListener(
  "click",
  () => {
    progress.stop.disabled = true;
    progress.stop.innerText = "Stopping...";
    cleanup();
  },
  true
);

// Load event source
const evtSource = new EventSource(`/stream/${id}`);

// Receiving a new row
evtSource.addEventListener(
  "message",
  (event) => {
    // Add row
    const data = JSON.parse(event.data);
    table.addRow(data);

    // Handle progress
    data.progress *= 100;

    progress.bar.style.width = data.progress + "%";
    progress.bar.textContent = data.progress.toFixed(2) + "%";
    progress.element.setAttribute("aria-valuenow", data.progress);
  },
  true
);

evtSource.addEventListener(
  "finished",
  (event) => {
    download.filename.value = event.data;
    progress.container.classList.add("visually-hidden");

    // Cleanup
    evtSource.dispatchEvent(new Event("error"));
  },
  true
);

// When stream finished
evtSource.addEventListener(
  "error",
  () => {
    evtSource.close();

    progress.spinner.hidden = true;
    progress.stop.hidden = true;
    progress.element.classList.add("bg-danger-subtle");
    progress.bar.classList.add("bg-danger");
    progress.bar.style.width = "100%";
    progress.bar.innerHTML = "Stream closed";
    download.btn.hidden = false;
  },
  true
);
