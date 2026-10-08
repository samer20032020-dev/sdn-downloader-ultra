/* SDN Downloader Ultra - browser bridge
 * Forwards links to the desktop app's loopback server on 127.0.0.1:4567.
 * The packaged app only accepts requests whose Origin is a real extension
 * origin, so this file must always run inside the extension context.
 */

const SDN_ENDPOINT = 'http://127.0.0.1:4567/';

function isSendableUrl(url) {
  return typeof url === 'string' && /^https?:\/\//i.test(url);
}

async function sendToSdn(url) {
  if (!isSendableUrl(url)) {
    return { ok: false, error: 'Only http/https links are supported.' };
  }
  try {
    const res = await fetch(SDN_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    if (!res.ok) {
      return { ok: false, error: 'SDN app responded with ' + res.status + '. Is it running?' };
    }
    const data = await res.json().catch(function () { return { status: 'ok' }; });
    return { ok: data.status === 'ok', error: data.msg || null };
  } catch (e) {
    return { ok: false, error: 'Could not reach SDN Downloader. Make sure the app is open.' };
  }
}

function notify(title, message) {
  try {
    if (chrome.notifications && chrome.notifications.create) {
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icons/icon128.png',
        title: title,
        message: message
      });
    }
  } catch (e) {
    /* notifications are optional */
  }
}

function currentTabUrl() {
  return new Promise(function (resolve) {
    try {
      chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
        resolve(tabs && tabs[0] ? tabs[0].url : null);
      });
    } catch (e) {
      resolve(null);
    }
  });
}

function createMenus() {
  if (!chrome.contextMenus) return;
  try {
    chrome.contextMenus.removeAll(function () {
      chrome.contextMenus.create({
        id: 'sdn-send-link',
        title: 'Send link to SDN Downloader',
        contexts: ['link']
      });
      chrome.contextMenus.create({
        id: 'sdn-send-page',
        title: 'Send page to SDN Downloader',
        contexts: ['page']
      });
    });
  } catch (e) {
    /* ignore */
  }
}

if (chrome.runtime && chrome.runtime.onInstalled) {
  chrome.runtime.onInstalled.addListener(createMenus);
}

if (chrome.contextMenus && chrome.contextMenus.onClicked) {
  chrome.contextMenus.onClicked.addListener(function (info) {
    const url = info.menuItemId === 'sdn-send-link' ? info.linkUrl : info.pageUrl;
    sendToSdn(url).then(function (result) {
      notify('SDN Downloader', result.ok ? 'Link sent to the app.' : result.error);
    });
  });
}

if (chrome.runtime && chrome.runtime.onMessage) {
  chrome.runtime.onMessage.addListener(function (msg, sender, sendResponse) {
    if (msg && msg.type === 'SDN_SEND_URL') {
      sendToSdn(msg.url).then(sendResponse);
      return true; /* keep the message channel open for the async reply */
    }
    return false;
  });
}

if (chrome.commands && chrome.commands.onCommand) {
  chrome.commands.onCommand.addListener(function (command) {
    if (command !== 'send-current-page') return;
    currentTabUrl().then(function (url) {
      return sendToSdn(url);
    }).then(function (result) {
      notify('SDN Downloader', result.ok ? 'Link sent to the app.' : result.error);
    });
  });
}
