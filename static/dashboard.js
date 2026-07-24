let sortDir = {};

function sortTable(col) {
  const table = document.getElementById("station-table");
  const tbody = table.querySelector("tbody");
  const rows = Array.from(tbody.querySelectorAll("tr"));
  const dir = sortDir[col] = !sortDir[col];
  rows.sort((a, b) => {
    const av = a.children[col].dataset.sort;
    const bv = b.children[col].dataset.sort;
    const an = parseFloat(av), bn = parseFloat(bv);
    const isNum = !isNaN(an) && !isNaN(bn);
    const cmp = isNum ? an - bn : av.localeCompare(bv);
    return dir ? cmp : -cmp;
  });
  rows.forEach(r => tbody.appendChild(r));
}

function filterStations() {
  const q = document.getElementById("station-search").value.toLowerCase();
  document.querySelectorAll("#station-table tbody tr").forEach(row => {
    const name = row.children[1].textContent.toLowerCase();
    row.style.display = name.includes(q) ? "" : "none";
  });
}