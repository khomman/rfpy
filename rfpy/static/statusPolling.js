//const rf_bar = document.getElementById("rf-progress");


async function getStatus(url) {
    const response = await fetch(url);
    console.log(response)
    return response.json();
}

function stopPolling(dlVal, rfVal, interval) {
    if (dlVal === 100 && rfVal === 100) {
        clearInterval(interval);
    }
}

async function displayResults() {
    const data = await getStatus("http://127.0.0.1:5000/poll_status");
    const dlVal = data.filter(x => x.download).map(x => x.download)[0];
    const rfVal = data.filter(x => x.rf).map(x => x.rf)[0];

    if (dlVal != undefined){
        document.getElementById('dl-progress').style.width = `${dlVal}%`;
        document.getElementById('dl-span').innerHTML = `Download:${dlVal}%`;
    }
    if (rfVal != undefined){
        document.getElementById('rf-progress').style.width = `${rfVal}%`;
        document.getElementById('rf-span').innerHTML = `RF:${rfVal}%`
    }
        stopPolling(dlVal, rfVal, interval);
}

window.onload = function(){
    interval = setInterval(displayResults, 3000);
}
// document.addEventListener('readystatechange', () => {
// interval = setInterval(displayResults,3000);
// })