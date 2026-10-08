/* SDN Downloader Ultra - toolbar popup controller */

(function () {
  var urlBox = document.getElementById('url');
  var sendBtn = document.getElementById('send');
  var statusBox = document.getElementById('status');
  var activeUrl = '';

  function setStatus(text, kind) {
    statusBox.textContent = text || '';
    statusBox.className = 'status' + (kind ? ' ' + kind : '');
  }

  function loadCurrentTab() {
    try {
      chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
        var tab = tabs && tabs[0];
        if (!tab || !tab.url || !/^https?:\/\//i.test(tab.url)) {
          urlBox.textContent = 'لا يوجد رابط قابل للإرسال في هذه الصفحة.';
          sendBtn.disabled = true;
          return;
        }
        activeUrl = tab.url;
        urlBox.textContent = activeUrl;
        sendBtn.disabled = false;
      });
    } catch (e) {
      urlBox.textContent = 'تعذّر قراءة رابط التبويب.';
    }
  }

  function send() {
    if (!activeUrl) return;
    sendBtn.disabled = true;
    setStatus('جارٍ الإرسال…', '');
    try {
      chrome.runtime.sendMessage({ type: 'SDN_SEND_URL', url: activeUrl }, function (reply) {
        if (reply && reply.ok) {
          setStatus('✅ تم الإرسال إلى التطبيق', 'ok');
        } else {
          setStatus('⚠️ ' + ((reply && reply.error) || 'فشل الإرسال'), 'err');
        }
        sendBtn.disabled = false;
      });
    } catch (e) {
      setStatus('⚠️ تعذّر الاتصال بالتطبيق', 'err');
      sendBtn.disabled = false;
    }
  }

  sendBtn.addEventListener('click', send);
  loadCurrentTab();
})();
