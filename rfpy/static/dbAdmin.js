const dbTableNames = document.querySelectorAll(".tables");
const resultsTable = document.querySelector("#resultsTable");

async function getTableData(url) {
    const response = await fetch(url)
    return response.json()
}

function generateTableHead(table, data) {
    const thead = table.createTHead();
    const row = thead.insertRow();
    for (let key in data) {
        let th = document.createElement("th");
        let text = document.createTextNode(key);
        th.appendChild(text);
        row.appendChild(th)
    }
}

function generateTable(table, data) {
    const tbody = table.createTBody();
    for (let element of data) {
        const row = tbody.insertRow();
        for (let key in element) {
            let cell = row.insertCell();
            let text = document.createTextNode(element[key]);
            cell.appendChild(text);
        }
    }
}

async function displayResults() {
    const dbtable = this.dataset.tb;
    url = `http://127.0.0.1:5000/getTables?table=${dbtable}`;
    const data = await getTableData(url);
    resultsTable.deleteTHead();
    tbody = resultsTable.getElementsByTagName('tbody')[0];
    if (tbody) {resultsTable.removeChild(tbody)};
    //resultsTable.delete();
    generateTableHead(resultsTable, data[0]);
    generateTable(resultsTable, data);
}

dbTableNames.forEach(nodeItem => {
    nodeItem.addEventListener('click', 
    displayResults);
})
