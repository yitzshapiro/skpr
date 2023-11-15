chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.videoId) {
      fetch('http://127.0.0.1:8000/process_video/', {
        method: 'POST',
        body: JSON.stringify({ videoId: request.videoId }),
        headers: { 'Content-Type': 'application/json' }
      })
      .then(response => response.json())
      .then(data => {
        chrome.scripting.executeScript({
          target: { tabId: sender.tab.id },
          func: highlightAndSkip,
          args: [data.start, data.end]
        });
      })
      .catch(error => {
        console.error('Error:', error);
      });
    }
  });
  
  function highlightAndSkip(start, end) {
    // Access the YouTube video player
    const player = document.querySelector('video');
    if (!player) return;
  
    // Function to check and skip the video
    function checkAndSkip() {
      // If current time is within the specified range, skip to the end
      if (player.currentTime >= start && player.currentTime < end) {
        player.currentTime = end;
        // Optionally, remove listener after skipping
        player.removeEventListener('timeupdate', checkAndSkip);
      }
    }
  
    // Add an event listener to the video player
    player.addEventListener('timeupdate', checkAndSkip);
  }
  