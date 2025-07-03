// Get elements from the page
const id = window.location.href.substring(
  window.location.href.lastIndexOf("/") + 1
);

const tableDiv = document.getElementById("table");
const download = {
  filename: document.getElementById("downloadFilename"),
  form: document.getElementById("downloadForm"),
  btn: document.getElementById("downloadBtn"),
  modal: document.getElementById("downloadModal"),
};
const progress = {
  element: document.getElementById("progressElement"),
  bar: document.getElementById("progressBar"),
  container: document.getElementById("progressContainer"),
  spinner: document.getElementById("progressSpinner"),
};

// Create table
const data = [];
const table = new Tabulator(tableDiv, {
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

evtSource.addEventListener("finished", (event) => {
  // @ts-ignore
  download.filename.value = event.data;
  progress.container.classList.add("visually-hidden");

  // Cleanup
  evtSource.onerror(new Event(null));
});

// When stream finished
evtSource.onerror = () => {
  evtSource.close();

  progress.spinner.hidden = true;
  progress.element.classList.add("bg-danger-subtle");
  progress.bar.classList.add("bg-danger");
  progress.bar.style.width = "100%";
  progress.bar.innerHTML = "Stream closed";

  download.btn.hidden = false;
};

// Handle download
downloadForm.onsubmit = (e) => {
  e.preventDefault();
  bootstrap.Modal.getInstance(download.modal).hide();

  // @ts-ignore
  const filename = download.filename.value;
  table.download("csv", filename);
};
