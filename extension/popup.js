//const server = 'http://127.0.0.1:5000/api/scrape'
const server = "https://newsbias-detect-tool-96460072068.us-central1.run.app/api/scrape";

// Function to fetch data from the backend
async function fetchData(model) {
    try {
        // Get the current tab
        const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tabs.length === 0) {
            throw new Error("No active tab found.");
        }
        const currentTab = tabs[0];
        const url = currentTab.url;

        // Send the URL to the Flask backend
        const response = await fetch(server, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url, model: model }) // Send the URL and model as JSON
        });

        if (!response.ok) {
            throw new Error(`Network response was not ok: ${response.statusText}`);
        }

        const data = await response.json();

        // Update the DOM with the received data
        document.getElementById('model').innerText = `Model: ${model}`;
        document.getElementById('result').innerText = `Paragraphs: ${data.result}`;
    } catch (error) {
        console.error('Error fetching data:', error);
        document.getElementById('data').innerText = `Failed to fetch data: ${error.message}`;
    }
}

// Event listeners for buttons
document.getElementById('fetchGPT').addEventListener('click', () => fetchData('gpt'));
document.getElementById('fetchClaude').addEventListener('click', () => fetchData('claude'));
document.getElementById('fetchGemini').addEventListener('click', () => fetchData('gemini'));
