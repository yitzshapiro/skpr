function getYoutubeVideoId() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('v');
  }
  
  chrome.runtime.sendMessage({ videoId: getYoutubeVideoId() });
  