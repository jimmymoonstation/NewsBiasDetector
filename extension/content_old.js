(function () {
  'use strict';

  const server = 'http://127.0.0.1:5000/api/click';

  let isInjected = false;
  let floatingButton = null;
  let floatingPanel = null;
  let isPanelOpen = false;

  function injectStyles() {
    const style = document.createElement('style');
    style.textContent = `
      #ext-floating-button {
        position: fixed;
        top: auto;
        bottom: 20px;
        right: 20px;
        background: white;
        border: none;
        border-radius: 50%;
        width: 48px;
        height: 48px;
        padding: 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 2147483647;
        cursor: pointer;
        overflow: hidden;
      }

      #ext-floating-button .ext-button-icon {
                             width: 100%;
                             height: 100%;
                             object-fit: cover;
                             border-radius: 50%;
                             display: block;
                             pointer-events: none; /* <— key: make the image not capture mouse events */
                             user-select: none;
                           }


      #ext-floating-panel {
        position: fixed;
        top: 40px;
        bottom: 40px;
        right: 20px;
        width: 380px;
        background: white;
        box-shadow: -2px 0 10px rgba(0,0,0,0.1);
        border-left: 1px solid #e5e7eb;
        z-index: 2147483646;
        display: flex;
        flex-direction: column;
        border-radius: 8px;
      }

      .ext-panel-content {
        padding: 16px;
        overflow-y: auto;
        flex: 1;
      }

      .ext-close-btn {
        position: absolute;
        top: 10px;
        right: 16px;
        font-size: 18px;
        border: none;
        background: none;
        cursor: pointer;
      }

      .ext-model-buttons button {
        margin-right: 6px;
        margin-bottom: 10px;
        padding: 6px 12px;
        border: 1px solid #ccc;
        background: #f9fafb;
        cursor: pointer;
        border-radius: 4px;
      }

      .ext-model-display,
      .ext-result-display,
      .ext-data-display {
        margin-top: 12px;
        font-size: 14px;
        white-space: pre-wrap;
      }
    `;
    document.head.appendChild(style);
  }

  function injectFloatingUI() {
    if (document.getElementById('ext-floating-button')) return;

    floatingButton = document.createElement('button');
    floatingButton.id = 'ext-floating-button';
//    floatingButton.innerHTML =
//      '<img src="' +
//      chrome.runtime.getURL('images/bird.jpg') +
//      '" class="ext-button-icon" alt="Logo">';
  floatingButton.innerHTML =
        '<img src="' +
        chrome.runtime.getURL('images/newsbreak.svg') +
        '" class="ext-button-icon" alt="Logo">';
    floatingButton.title = 'Open AI Assistant';

    document.body.appendChild(floatingButton);
    injectStyles();
    setupDraggableButton();
    floatingButton.addEventListener('click', togglePanel);

    isInjected = true;
  }

  function injectFloatingPanel() {
    floatingPanel = document.createElement('div');
    floatingPanel.id = 'ext-floating-panel';
    floatingPanel.innerHTML = `
      <div class="ext-panel-content">
        <button class="ext-close-btn" id="ext-close-btn">×</button>
        <div class="ext-model-buttons">
          <button id="ext-fetchGPT">GPT</button>
          <button id="ext-fetchClaude">Claude</button>
          <button id="ext-fetchGemini">Gemini</button>
        </div>
        <div class="ext-model-display" id="ext-model">Select your model</div>
        <div class="ext-result-display" id="ext-result"></div>
        <div class="ext-score-display" id="ext-score"></div>
//        <div class="ext-data-display" id="ext-data">123</div>
      </div>
    `;
    document.body.appendChild(floatingPanel);
    setupPanelEvents();
  }

  function setupPanelEvents() {
    document.getElementById('ext-close-btn').addEventListener('click', closePanel);
    document.getElementById('ext-fetchGPT').addEventListener('click', () => fetchData('gpt'));
    document.getElementById('ext-fetchClaude').addEventListener('click', () => fetchData('claude'));
    document.getElementById('ext-fetchGemini').addEventListener('click', () => fetchData('gemini'));
  }

  function togglePanel() {
    if (isPanelOpen) {
      closePanel();
    } else {
      openPanel();
    }
  }

  function openPanel() {
    if (!floatingPanel) {
      injectFloatingPanel();
    }
    isPanelOpen = true;
    floatingButton.classList.add('active');
  }

  function closePanel() {
    if (floatingPanel) {
      floatingPanel.remove();
      floatingPanel = null;
    }
    isPanelOpen = false;
    floatingButton.classList.remove('active');
  }

  async function fetchData(model) {
    try {
      document.getElementById('ext-result').innerText = `loading...`;
      const url = window.location.href;

      const response = await fetch(server, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, model }),
      });

      if (!response.ok) throw new Error(`HTTP error: ${response.statusText}`);

      const data = await response.json();
      document.getElementById('ext-model').innerText = `Model: ${model}`;
      document.getElementById('ext-result').innerText = `Analysis:\n ${data.result}`;
      document.getElementById('ext-score').innerText = `Score:\n ${data.score}`;
//      document.getElementById('ext-data').innerText = JSON.stringify(data, null, 2);
    } catch (error) {
      console.error('Fetch failed:', error);
      document.getElementById('ext-data').innerText = `Failed to fetch data: ${error.message}`;
    }
  }

  function setupDraggableButton() {
    let isDragging = false;
    let offsetY = 0;

    floatingButton.addEventListener('mousedown', (e) => {
      isDragging = true;
      offsetY = e.clientY - floatingButton.getBoundingClientRect().top;
      document.body.style.userSelect = 'none';
    });

    document.addEventListener('mousemove', (e) => {
      if (isDragging) {
        const newTop = e.clientY - offsetY;
        floatingButton.style.top = `${Math.max(10, Math.min(window.innerHeight - 58, newTop))}px`;
        floatingButton.style.bottom = 'auto';
      }
    });

    document.addEventListener('mouseup', () => {
      isDragging = false;
      document.body.style.userSelect = '';
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectFloatingUI);
  } else {
    injectFloatingUI();
  }

  let lastUrl = location.href;
  new MutationObserver(() => {
    const url = location.href;
    if (url !== lastUrl) {
      lastUrl = url;
      setTimeout(injectFloatingUI, 1000);
    }
  }).observe(document, { subtree: true, childList: true });
})();
