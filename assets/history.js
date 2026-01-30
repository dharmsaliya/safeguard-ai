// Function to load history from LocalStorage
function loadHistory() {
    const historyData = JSON.parse(localStorage.getItem('safeguard_history')) || [];
    const tableBody = document.getElementById('history-list');
    const noDataMsg = document.getElementById('no-data');

    // Update Summary Stats
    document.getElementById('total-incidents').innerText = historyData.length;
    if (historyData.length > 0) {
        document.getElementById('last-incident').innerText = historyData[0].date.split(',')[0]; // Just the date part
    }

    // Clear current list
    tableBody.innerHTML = "";

    if (historyData.length === 0) {
        noDataMsg.style.display = "block";
        return;
    } 
    
    noDataMsg.style.display = "none";

    // Loop through data and create rows
    historyData.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${item.date}</td>
            <td><span class="incident-type">${item.type}</span></td>
            <td>${item.impact} G</td>
            <td>${item.posture}</td>
            <td>${item.temp} °C</td>
        `;
        tableBody.appendChild(row);
    });
}

// Function to clear history
function clearHistory() {
    if(confirm("Are you sure you want to delete all medical records?")) {
        localStorage.removeItem('safeguard_history');
        loadHistory();
    }
}

// Load data when page opens
window.onload = loadHistory;
