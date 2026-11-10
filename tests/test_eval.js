const window = {}; const document = { createElement: () => ({ style: {} }), head: {}, documentElement: {} };
if (!window.__sdn_ublock_installed) { 
(function() {
    if (window.__sdn_ublock_installed) return 'ALREADY_INSTALLED';
    window.__sdn_ublock_installed = true;

    // ================================================================
    // 1. uBlock Origin Engine: JSON Player Response Pruning / Defusing
    // Strips adPlacements, playerAds, and adSlots directly at the API level
    // This stops YouTube from ever queueing or attempting to play ads!
    // ================================================================
    function pruneAdData(data) {
        if (!data || typeof data !== 'object') return data;
        try {
            delete data.adPlacements;
            delete data.adSlots;
            delete data.playerAds;
            delete data.adBreakHeartbeatParams;
            delete data.adPlacementRenderer;

            if (data.playerResponse && typeof data.playerResponse === 'object') {
                delete data.playerResponse.adPlacements;
                delete data.playerResponse.adSlots;
                delete data.playerResponse.playerAds;
                delete data.playerResponse.adBreakHeartbeatParams;
            }

            if (data.streamingData && data.streamingData.adFormat) {
                delete data.streamingData.adFormat;
            }

            if (Array.isArray(data.items)) {
                data.items = data.items.filter(function(item) {
                    return !item.adSlotRenderer && !item.adLayoutRenderer;
                });
            }
        } catch (e) {}
        return data;
    }

    // ================================================================
    // uBlock Origin Core: Hook JSON.parse globally
    // ================================================================
    var origJSONParse = JSON.parse;
    JSON.parse = function(text, reviver) {
        var data = origJSONParse.apply(this, arguments);
        if (data && typeof data === 'object') {
            pruneAdData(data);
        }
        return data;
    };

    // ================================================================
    // uBlock Origin Core: Hook Response.prototype.json
    // ================================================================
    if (typeof Response !== 'undefined' && Response.prototype && Response.prototype.json) {
        var origResponseJson = Response.prototype.json;
        Response.prototype.json = async function() {
            var data = await origResponseJson.apply(this, arguments);
            if (data && typeof data === 'object') {
                pruneAdData(data);
            }
            return data;
        };
    }

    // Intercept window.fetch (uBlock json-prune-fetch-response)
    if (typeof window.fetch === 'function') {
        var origFetch = window.fetch;
        window.fetch = async function(...args) {
            var url = '';
            try {
                url = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url ? args[0].url : '');
            } catch (e) {}

            // Instantly block ad beacons, trackers & doubleclick requests with zero delay (204 No Content)
            if (url && (
                url.indexOf('/api/stats/ads') !== -1 ||
                url.indexOf('/pagead/') !== -1 ||
                url.indexOf('doubleclick.net') !== -1 ||
                url.indexOf('/youtubei/v1/player/ad_break') !== -1 ||
                url.indexOf('/pcs/view') !== -1 ||
                url.indexOf('/ptracking') !== -1
            )) {
                return new Response(null, { status: 204, statusText: 'No Content' });
            }

            var response = await origFetch.apply(this, args);

            // Prune ads from player API responses seamlessly
            if (url && (
                url.indexOf('/youtubei/v1/player') !== -1 ||
                url.indexOf('/reel/reel_item_watch') !== -1 ||
                url.indexOf('/youtubei/v1/next') !== -1
            )) {
                try {
                    var clone = response.clone();
                    var json = await clone.json();
                    pruneAdData(json);
                    return new Response(JSON.stringify(json), {
                        status: response.status,
                        statusText: response.statusText,
                        headers: response.headers
                    });
                } catch (e) {
                    return response;
                }
            }

            return response;
        };
    }

    // Intercept XMLHttpRequest
    if (window.XMLHttpRequest) {
        var origOpen = XMLHttpRequest.prototype.open;
        var origSend = XMLHttpRequest.prototype.send;

        XMLHttpRequest.prototype.open = function(method, url) {
            this._sdn_url = url || '';
            return origOpen.apply(this, arguments);
        };

        XMLHttpRequest.prototype.send = function(body) {
            var xhr = this;
            var url = xhr._sdn_url || '';

            if (url && (
                url.indexOf('/api/stats/ads') !== -1 ||
                url.indexOf('/pagead/') !== -1 ||
                url.indexOf('doubleclick.net') !== -1 ||
                url.indexOf('/youtubei/v1/player/ad_break') !== -1
            )) {
                Object.defineProperty(xhr, 'status', { value: 204 });
                Object.defineProperty(xhr, 'responseText', { value: '' });
                return;
            }

            if (url && url.indexOf('/youtubei/v1/player') !== -1) {
                var origOnReady = xhr.onreadystatechange;
                xhr.onreadystatechange = function() {
                    if (xhr.readyState === 4) {
                        try {
                            var data = JSON.parse(xhr.responseText);
                            pruneAdData(data);
                            var cleaned = JSON.stringify(data);
                            Object.defineProperty(xhr, 'responseText', { value: cleaned });
                            Object.defineProperty(xhr, 'response', { value: data });
                        } catch (e) {}
                    }
                    if (origOnReady) origOnReady.apply(xhr, arguments);
                };
            }

            return origSend.apply(this, arguments);
        };
    }

    // Intercept ytInitialPlayerResponse
    try {
        var _initialResp = window.ytInitialPlayerResponse;
        Object.defineProperty(window, 'ytInitialPlayerResponse', {
            get: function() { return _initialResp; },
            set: function(val) { _initialResp = pruneAdData(val); },
            configurable: true
        });
        if (window.ytInitialPlayerResponse) {
            window.ytInitialPlayerResponse = pruneAdData(window.ytInitialPlayerResponse);
        }
    } catch (e) {}

    // ================================================================
    // 2. Cosmetic CSS & In-Page Buttons Styling
    // ================================================================
    if (!document.getElementById('sdn-styles')) {
        var style = document.createElement('style');
        style.id = 'sdn-styles';
        style.textContent = [
            '.video-ads, .ytp-ad-module, .ytp-ad-overlay-container, .ytp-ad-overlay-slot,',
            '.ytp-ad-player-overlay, .ytp-ad-player-overlay-layout, .ytp-ad-progress-list,',
            '.ytp-ad-message-container, .ytp-ad-text, .ytp-paid-content-overlay,',
            'ytd-ad-slot-renderer, ytd-in-feed-ad-layout-renderer, #masthead-ad,',
            'ytd-banner-promo-renderer, ytd-promoted-sparkles-web-renderer,',
            'ytd-promoted-sparkles-text-search-renderer, .ytd-display-ad-renderer,',
            'ytd-statement-banner-renderer, #player-ads, ytd-merch-shelf-renderer,',
            'ytd-action-companion-ad-renderer, #premium-ytd-banner, ytd-mealbar-promo-renderer,',
            'ytd-engagement-panel-section-list-renderer[target-id="engagement-panel-ads"],',
            'tp-yt-paper-dialog:has(ytd-enforcement-message-view-model),',
            'ytd-enforcement-message-view-model {',
            '   display: none !important; visibility: hidden !important; height: 0 !important;',
            '   max-height: 0 !important; opacity: 0 !important; pointer-events: none !important;',
            '}',
            '#sdn-idm-panel {',
            '   position: fixed; top: 68px; left: 16px; z-index: 2147483646;',
            '   display: none; align-items: center; gap: 8px;',
            '   background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);',
            '   color: #ffffff; padding: 7px 14px; border-radius: 9px;',
            '   border: 1px solid #38bdf8; box-shadow: 0 8px 25px rgba(0,0,0,0.85), 0 0 12px rgba(56, 189, 248, 0.3);',
            '   font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;',
            '   font-size: 13px; font-weight: 700; direction: rtl; cursor: pointer; user-select: none;',
            '   transition: transform 0.18s, box-shadow 0.18s;',
            '}',
            '#sdn-idm-panel:hover {',
            '   transform: translateY(-1px);',
            '   box-shadow: 0 10px 28px rgba(0,0,0,0.9), 0 0 16px rgba(56, 189, 248, 0.45);',
            '}',
            '#sdn-title-dl-bar {',
            '   display: flex; align-items: center; flex-wrap: wrap; gap: 8px;',
            '   background: linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(30, 41, 59, 0.98) 100%);',
            '   border: 1.5px solid rgba(56, 189, 248, 0.55); border-radius: 12px; padding: 8px 14px;',
            '   margin: 10px 0 14px 0; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.7), 0 0 14px rgba(56, 189, 248, 0.2);',
            '   direction: rtl; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;',
            '   z-index: 1000;',
            '}',
            '.sdn-bar-label {',
            '   display: inline-flex; align-items: center; gap: 5px; font-size: 13px; font-weight: 800;',
            '   color: #38bdf8; margin-left: 6px; user-select: none;',
            '}',
            '.sdn-chip-btn {',
            '   display: inline-flex; align-items: center; gap: 6px; height: 34px; border-radius: 17px;',
            '   padding: 0 13px; font-size: 12.5px; font-weight: 700; cursor: pointer; user-select: none;',
            '   border: 1px solid transparent; transition: all 0.18s ease; white-space: nowrap;',
            '}',
            '.sdn-btn-fhd {',
            '   background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); color: #ffffff;',
            '   border-color: rgba(56, 189, 248, 0.6); box-shadow: 0 2px 8px rgba(2, 132, 199, 0.35);',
            '}',
            '.sdn-btn-fhd:hover {',
            '   background: linear-gradient(135deg, #0369a1 0%, #0284c7 100%); transform: translateY(-1px);',
            '   box-shadow: 0 4px 14px rgba(56, 189, 248, 0.55);',
            '}',
            '.sdn-btn-hd {',
            '   background: rgba(255, 255, 255, 0.08); color: #f1f5f9; border-color: rgba(255, 255, 255, 0.2);',
            '}',
            '.sdn-btn-hd:hover {',
            '   background: rgba(56, 189, 248, 0.22); border-color: #38bdf8; color: #38bdf8; transform: translateY(-1px);',
            '}',
            '.sdn-btn-audio {',
            '   background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(5, 150, 105, 0.3) 100%);',
            '   color: #34d399; border-color: rgba(52, 211, 153, 0.5); box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2);',
            '}',
            '.sdn-btn-audio:hover {',
            '   background: linear-gradient(135deg, #059669 0%, #10b981 100%); color: #ffffff; transform: translateY(-1px);',
            '   box-shadow: 0 4px 14px rgba(52, 211, 153, 0.45);',
            '}',
            '.sdn-btn-playlist-video {',
            '   background: linear-gradient(135deg, #d97706 0%, #b45309 100%); color: #ffffff;',
            '   border-color: rgba(251, 191, 36, 0.6); box-shadow: 0 2px 8px rgba(217, 119, 6, 0.35);',
            '}',
            '.sdn-btn-playlist-video:hover {',
            '   background: linear-gradient(135deg, #b45309 0%, #d97706 100%); transform: translateY(-1px);',
            '   box-shadow: 0 4px 14px rgba(251, 191, 36, 0.5);',
            '}',
            '.sdn-btn-playlist-select {',
            '   background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%); color: #ffffff;',
            '   border-color: rgba(167, 139, 250, 0.6); box-shadow: 0 2px 8px rgba(124, 58, 237, 0.35);',
            '}',
            '.sdn-btn-playlist-select:hover {',
            '   background: linear-gradient(135deg, #6d28d9 0%, #7c3aed 100%); transform: translateY(-1px);',
            '   box-shadow: 0 4px 14px rgba(167, 139, 250, 0.5);',
            '}',
            '#sdn-player-badge {',
            '   position: absolute; top: 14px; left: 14px; z-index: 2147483640;',
            '   display: inline-flex; align-items: center; gap: 6px;',
            '   background: rgba(15, 23, 42, 0.9); backdrop-filter: blur(10px);',
            '   border: 1.5px solid rgba(56, 189, 248, 0.55); border-radius: 20px;',
            '   padding: 4px 10px; box-shadow: 0 6px 22px rgba(0,0,0,0.85); direction: rtl;',
            '   font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;',
            '   user-select: none; transition: all 0.2s ease;',
            '}',
            '#sdn-player-badge:hover {',
            '   border-color: #38bdf8; box-shadow: 0 8px 26px rgba(56, 189, 248, 0.45);',
            '}',
            '.sdn-player-btn {',
            '   display: inline-flex; align-items: center; gap: 4px; height: 28px; border-radius: 14px;',
            '   padding: 0 9px; font-size: 11.5px; font-weight: 700; cursor: pointer; user-select: none;',
            '   border: 1px solid rgba(255, 255, 255, 0.16); background: rgba(255, 255, 255, 0.08);',
            '   color: #f1f5f9; transition: all 0.18s ease;',
            '}',
            '.sdn-player-btn:hover {',
            '   background: rgba(56, 189, 248, 0.25); border-color: #38bdf8; color: #38bdf8; transform: translateY(-1px);',
            '}',
            '.sdn-player-btn.btn-audio:hover {',
            '   background: rgba(52, 211, 153, 0.25); border-color: #34d399; color: #34d399;',
            '}',
            '.sdn-idm-menu-item:hover {',
            '   background: rgba(56, 189, 248, 0.18) !important; color: #38bdf8 !important;',
            '}'
        ].join(' ');
        (document.head || document.documentElement).appendChild(style);
    }

    function createEl(tag, id, css, text) {
        var el = document.createElement(tag);
        if (id) el.id = id;
        if (css) el.style.cssText = css;
        if (text) el.textContent = text;
        return el;
    }

    function getMediaContext() {
        var href = window.location.href || '';
        var path = window.location.pathname || '';
        var search = window.location.search || '';

        var isWatch = path.indexOf('/watch') !== -1 || search.indexOf('v=') !== -1;
        var isShorts = path.indexOf('/shorts/') !== -1;
        var isPlaylistPage = path.indexOf('/playlist') !== -1;
        var hasListParam = search.indexOf('list=') !== -1;
        var isPlaylist = isPlaylistPage || (isWatch && hasListParam);

        var video = document.querySelector('video');
        var hasActiveVideo = Boolean(video && (video.src || video.currentSrc || video.readyState > 0));

        var isMediaActive = isWatch || isShorts || isPlaylistPage || hasActiveVideo;

        var singleUrl = href;
        if (isWatch && hasListParam) {
            try {
                var u = new URL(href);
                var vId = u.searchParams.get('v');
                if (vId) singleUrl = 'https://www.youtube.com/watch?v=' + vId;
            } catch (e) {}
        }

        return {
            active: isMediaActive,
            isWatch: isWatch,
            isShorts: isShorts,
            isPlaylist: isPlaylist,
            singleUrl: singleUrl,
            fullUrl: href
        };
    }

    // Dropdown Menu
    var menu = document.getElementById('sdn-idm-menu');
    if (!menu) {
        menu = createEl(
            'div',
            'sdn-idm-menu',
            'display:none; position:fixed; z-index:2147483647; width:310px; background:#0f172a; border:1px solid #38bdf8; border-radius:12px; padding:10px; box-shadow:0 24px 50px rgba(0,0,0,0.95); direction:rtl; font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; flex-direction:column; gap:4px;'
        );
        (document.body || document.documentElement).appendChild(menu);

        document.addEventListener('click', function(e) {
            if (menu && !menu.contains(e.target)) {
                menu.style.display = 'none';
            }
        });
    }

    // Modern Toast Notification with action support
    window.showSdnToast = function(msg, type, actionData) {
        var t = document.getElementById('sdn-toast');
        if (!t) {
            t = createEl('div', 'sdn-toast', 'position:fixed; bottom:26px; left:50%; transform:translateX(-50%); z-index:2147483647; background:rgba(15, 23, 42, 0.96); backdrop-filter:blur(12px); color:#ffffff; border-radius:30px; padding:11px 22px; font-weight:bold; font-size:13px; box-shadow:0 12px 35px rgba(0,0,0,0.85); transition:all 0.3s cubic-bezier(0.4, 0, 0.2, 1); opacity:0; pointer-events:auto; font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; direction:rtl; display:flex; align-items:center; gap:12px; max-width:92vw;');
            (document.body || document.documentElement).appendChild(t);
        }
        while (t.firstChild) t.removeChild(t.firstChild);

        var borderColor = '#38bdf8';
        if (type === 'success') borderColor = '#22c55e';
        else if (type === 'warning') borderColor = '#f59e0b';
        else if (type === 'error') borderColor = '#ef4444';
        else if (type === 'info') borderColor = '#38bdf8';

        t.style.border = '1.5px solid ' + borderColor;
        t.style.boxShadow = '0 12px 35px rgba(0,0,0,0.85), 0 0 16px ' + borderColor + '40';

        var textSpan = createEl('span', '', 'line-height:1.4;', msg);
        t.appendChild(textSpan);

        if (actionData && actionData.url) {
            var actionBtn = createEl('button', '', 'background:' + borderColor + '; color:#000; border:none; border-radius:14px; padding:4px 12px; font-size:12px; font-weight:800; cursor:pointer; margin-right:6px; white-space:nowrap;', 'تنزيل على أي حال ↻');
            actionBtn.onclick = function(e) {
                e.stopPropagation();
                t.style.opacity = '0';
                if (window.pywebview && window.pywebview.api && window.pywebview.api.download_url) {
                    window.pywebview.api.download_url(actionData.url, actionData.quality || 'best', actionData.mode || 'single', true, actionData.title || '');
                }
            };
            t.appendChild(actionBtn);
        }

        t.style.opacity = '1';
        t.style.transform = 'translateX(-50%) translateY(0)';

        clearTimeout(window.__sdn_toast_timer);
        window.__sdn_toast_timer = setTimeout(function() {
            if (t) {
                t.style.opacity = '0';
                t.style.transform = 'translateX(-50%) translateY(10px)';
            }
        }, actionData ? 8000 : 4500);
    };

    function showToast(msg, type) {
        window.showSdnToast(msg, type || 'info');
    }

    function getVideoTitle() {
        var titleEl = document.querySelector('ytd-watch-metadata #title h1, h1.style-scope.ytd-watch-metadata, #title.ytd-watch-metadata, h1.title');
        return titleEl ? titleEl.textContent.trim() : (document.title ? document.title.replace(/ - YouTube$/, '').trim() : '');
    }

    function triggerDirectDownload(url, quality, mode, label, title) {
        var effectiveTitle = title || getVideoTitle();
        showToast('⏳ جاري التحقق من التنزيل المباشر (' + label + ')...', 'info');
        if (window.pywebview && window.pywebview.api && window.pywebview.api.download_url) {
            window.pywebview.api.download_url(url, quality, mode, false, effectiveTitle);
        }
    }

    function populateMenu(ctx) {
        if (!menu) return;
        while (menu.firstChild) menu.removeChild(menu.firstChild);

        var curTitle = getVideoTitle();
        var header = createEl('div', '', 'display:flex; align-items:center; justify-content:space-between; padding:4px 8px; border-bottom:1px solid rgba(255,255,255,0.12); margin-bottom:6px;');
        var hTitle = createEl('span', '', 'font-size:12.5px; font-weight:bold; color:#38bdf8;', ctx.isPlaylist ? '📚 خيارات تحميل القائمة / الفيديو (SDN)' : '⚡ خيارات تنزيل المقطع (SDN)');
        var hClose = createEl('span', '', 'cursor:pointer; color:#94a3b8; font-size:14px; font-weight:bold; padding:0 4px;', '✕');
        hClose.onclick = function(e) {
            e.stopPropagation();
            menu.style.display = 'none';
        };
        header.appendChild(hTitle);
        header.appendChild(hClose);
        menu.appendChild(header);

        function addSectionHeader(title) {
            var s = createEl('div', '', 'font-size:11px; font-weight:bold; color:#94a3b8; padding:5px 8px 2px 8px;');
            s.textContent = title;
            menu.appendChild(s);
        }

        function addItem(text, color, isBold, callback) {
            var row = createEl('div', '', 'padding:8px 12px; border-radius:7px; font-size:12.5px; cursor:pointer; display:flex; align-items:center; gap:8px;');
            row.className = 'sdn-idm-menu-item';
            row.textContent = text;
            row.style.color = color || '#f8fafc';
            if (isBold) row.style.fontWeight = 'bold';
            row.onclick = function(e) {
                e.stopPropagation();
                menu.style.display = 'none';
                callback();
            };
            menu.appendChild(row);
        }

        if (ctx.isPlaylist) {
            addSectionHeader('🎬 تحميل هذا الفيديو فقط:');
            addItem('🚀 تنزيل هذا الفيديو بأعلى جودة', '#38bdf8', true, function() {
                triggerDirectDownload(ctx.singleUrl, 'best', 'single', 'هذا الفيديو (أفضل جودة)', curTitle);
            });
            addItem('📺 فيديو 1080p FHD لهذا المقطع', '#f8fafc', false, function() {
                triggerDirectDownload(ctx.singleUrl, '1080p', 'single', 'فيديو 1080p', curTitle);
            });
            addItem('📺 فيديو 720p HD لهذا المقطع', '#f8fafc', false, function() {
                triggerDirectDownload(ctx.singleUrl, '720p', 'single', 'فيديو 720p', curTitle);
            });
            addItem('🎵 استخراج صوت هذا المقطع MP3', '#34d399', true, function() {
                triggerDirectDownload(ctx.singleUrl, 'mp3', 'single', 'صوت MP3', curTitle);
            });

            addSectionHeader('📚 خيارات قائمة التشغيل:');
            addItem('⚡ تحميل قائمة التشغيل كاملة فيديو', '#fbbf24', true, function() {
                triggerDirectDownload(ctx.fullUrl, 'best', 'playlist_all', 'كامل قائمة التشغيل', curTitle);
            });
            addItem('📋 اختيار فيديوهات معينة... (تحديد مخصص)', '#a78bfa', true, function() {
                showToast('📋 جاري فتح نافذة تحديد عناصر القائمة في SDN...', 'info');
                if (window.pywebview && window.pywebview.api && window.pywebview.api.send_to_main) {
                    window.pywebview.api.send_to_main(ctx.fullUrl, true);
                }
            });
            addItem('🎵 تحميل كامل القائمة بصيغة MP3', '#34d399', true, function() {
                triggerDirectDownload(ctx.fullUrl, 'mp3', 'playlist_all', 'كامل القائمة MP3', curTitle);
            });
        } else {
            addSectionHeader('🎬 اختر جودة الفيديو للتنزيل المباشر:');
            addItem('🎬 فيديو 1080p Full HD (MP4)', '#38bdf8', true, function() {
                triggerDirectDownload(ctx.fullUrl, '1080p', 'single', '1080p Full HD', curTitle);
            });
            addItem('📺 فيديو 720p HD (MP4)', '#f8fafc', false, function() {
                triggerDirectDownload(ctx.fullUrl, '720p', 'single', '720p HD', curTitle);
            });
            addItem('🚀 أفضل جودة تلقائياً (Best)', '#f8fafc', false, function() {
                triggerDirectDownload(ctx.fullUrl, 'best', 'single', 'أفضل جودة', curTitle);
            });
            addItem('📱 فيديو 480p / SD (حجم خفيف)', '#f8fafc', false, function() {
                triggerDirectDownload(ctx.fullUrl, '480p', 'single', '480p SD', curTitle);
            });
            addItem('🎵 استخراج الصوت MP3 (عالي النقاء + إضافة للموسيقى)', '#34d399', true, function() {
                triggerDirectDownload(ctx.fullUrl, 'mp3', 'single', 'صوت MP3', curTitle);
            });
        }

        var div = createEl('div', '', 'border-top:1px solid rgba(255,255,255,0.1); margin:4px 0;');
        menu.appendChild(div);

        addItem('🖥️ فتح وتعديل الرابط في محرك SDN الرئيسي', '#94a3b8', false, function() {
            if (window.pywebview && window.pywebview.api && window.pywebview.api.send_to_main) {
                window.pywebview.api.send_to_main(ctx.fullUrl, false);
                showToast('✅ تم فتح الرابط في شاشة SDN الرئيسية', 'success');
            }
        });
    }

    function openMenuAt(rect, ctx) {
        if (!menu) return;
        populateMenu(ctx);
        var top = (rect ? rect.bottom : 70) + 6;
        var left = rect ? (rect.right - 310) : (window.innerWidth - 330);
        if (left < 10) left = 10;
        if (left + 310 > window.innerWidth) left = window.innerWidth - 320;
        menu.style.top = top + 'px';
        menu.style.left = left + 'px';
        menu.style.display = 'flex';
    }

    // 1. Direct Download Bar Under the Video Title
    function ensureUnderTitleBar(ctx) {
        if (!ctx.active) {
            var old = document.getElementById('sdn-title-dl-bar');
            if (old) old.remove();
            return;
        }

        var titleEl = document.querySelector('ytd-watch-metadata #title')
                   || document.querySelector('#above-the-fold #title')
                   || document.querySelector('h1.style-scope.ytd-watch-metadata')
                   || document.querySelector('#title.ytd-watch-metadata');

        if (!titleEl) return;

        var bar = document.getElementById('sdn-title-dl-bar');
        var curUrl = ctx.singleUrl || ctx.fullUrl;
        var modeKey = (ctx.isPlaylist ? 'playlist' : 'single') + '_' + curUrl;

        if (!bar) {
            bar = createEl('div', 'sdn-title-dl-bar');
        }

        if (bar.dataset.modeKey !== modeKey) {
            bar.dataset.modeKey = modeKey;
            while (bar.firstChild) bar.removeChild(bar.firstChild);

            var curTitle = getVideoTitle();

            var lbl = createEl('span', '', '', '⚡ تنزيل SDN:');
            lbl.className = 'sdn-bar-label';
            bar.appendChild(lbl);

            if (ctx.isPlaylist) {
                var bAllVid = createEl('div', '', '', '⚡ تحميل القائمة كاملة فيديو');
                bAllVid.className = 'sdn-chip-btn sdn-btn-playlist-video';
                bAllVid.title = 'تنزيل جميع فيديوهات القائمة فوراً بأفضل جودة إلى مجلد التنزيلات المختار';
                bAllVid.onclick = function(e) {
                    e.stopPropagation();
                    triggerDirectDownload(ctx.fullUrl, 'best', 'playlist_all', 'كامل القائمة فيديو', curTitle);
                };
                bar.appendChild(bAllVid);

                var bAllAud = createEl('div', '', '', '🎵 تحميل كامل القائمة MP3');
                bAllAud.className = 'sdn-chip-btn sdn-btn-audio';
                bAllAud.title = 'تنزيل جميع مقاطع القائمة بصوت MP3 وإضافتها مباشرة لمشغل الموسيقى';
                bAllAud.onclick = function(e) {
                    e.stopPropagation();
                    triggerDirectDownload(ctx.fullUrl, 'mp3', 'playlist_all', 'كامل القائمة MP3', curTitle);
                };
                bar.appendChild(bAllAud);

                var bSelect = createEl('div', '', '', '📋 اختيار فيديوهات معينة... (مخصص)');
                bSelect.className = 'sdn-chip-btn sdn-btn-playlist-select';
                bSelect.title = 'فتح محرك SDN تلقائياً لتحديد فيديوهات معينة واختيار صيغة كل فيديو';
                bSelect.onclick = function(e) {
                    e.stopPropagation();
                    showToast('📋 جاري فتح نافذة تحديد عناصر القائمة في SDN...', 'info');
                    if (window.pywebview && window.pywebview.api && window.pywebview.api.send_to_main) {
                        window.pywebview.api.send_to_main(ctx.fullUrl, true);
                    }
                };
                bar.appendChild(bSelect);

                var bThisVid = createEl('div', '', '', '🎬 هذا الفيديو (1080p)');
                bThisVid.className = 'sdn-chip-btn sdn-btn-fhd';
                bThisVid.title = 'تنزيل هذا الفيديو فقط بجودة 1080p FHD';
                bThisVid.onclick = function(e) {
                    e.stopPropagation();
                    triggerDirectDownload(ctx.singleUrl, '1080p', 'single', 'فيديو 1080p', curTitle);
                };
                bar.appendChild(bThisVid);

                var bThisAud = createEl('div', '', '', '🎵 هذا المقطع (MP3)');
                bThisAud.className = 'sdn-chip-btn sdn-btn-hd';
                bThisAud.title = 'استخراج صوت هذا المقطع فقط MP3';
                bThisAud.onclick = function(e) {
                    e.stopPropagation();
                    triggerDirectDownload(ctx.singleUrl, 'mp3', 'single', 'صوت MP3', curTitle);
                };
                bar.appendChild(bThisAud);
            } else {
                var b1080 = createEl('div', '', '', '🎬 1080p FHD (MP4)');
                b1080.className = 'sdn-chip-btn sdn-btn-fhd';
                b1080.title = 'تنزيل مباشر فيديو 1080p Full HD إلى مجلد التنزيلات بدون تحويل';
                b1080.onclick = function(e) {
                    e.stopPropagation();
                    triggerDirectDownload(ctx.singleUrl, '1080p', 'single', '1080p Full HD', curTitle);
                };
                bar.appendChild(b1080);

                var b720 = createEl('div', '', '', '📺 720p HD (MP4)');
                b720.className = 'sdn-chip-btn sdn-btn-hd';
                b720.title = 'تنزيل مباشر فيديو 720p HD إلى مجلد التنزيلات بدون تحويل';
                b720.onclick = function(e) {
                    e.stopPropagation();
                    triggerDirectDownload(ctx.singleUrl, '720p', 'single', '720p HD', curTitle);
                };
                bar.appendChild(b720);

                var bBest = createEl('div', '', '', '🚀 أفضل جودة (Best)');
                bBest.className = 'sdn-chip-btn sdn-btn-hd';
                bBest.title = 'تنزيل بأعلى جودة متوفرة تلقائياً MP4';
                bBest.onclick = function(e) {
                    e.stopPropagation();
                    triggerDirectDownload(ctx.singleUrl, 'best', 'single', 'أفضل جودة', curTitle);
                };
                bar.appendChild(bBest);

                var bMp3 = createEl('div', '', '', '🎵 صوت MP3 عالي النقاء');
                bMp3.className = 'sdn-chip-btn sdn-btn-audio';
                bMp3.title = 'استخراج صوت MP3 عالي النقاء وإضافته تلقائياً لمكتبة الموسيقى بالسايد بار';
                bMp3.onclick = function(e) {
                    e.stopPropagation();
                    triggerDirectDownload(ctx.singleUrl, 'mp3', 'single', 'صوت MP3', curTitle);
                };
                bar.appendChild(bMp3);

                var bMore = createEl('div', '', '', '⚙️ خيارات أخرى ▼');
                bMore.className = 'sdn-chip-btn sdn-btn-hd';
                bMore.title = 'خيارات وتنسيقات التنزيل الأخرى';
                bMore.onclick = function(e) {
                    e.stopPropagation();
                    openMenuAt(bMore.getBoundingClientRect(), getMediaContext());
                };
                bar.appendChild(bMore);
            }
        }

        if (bar.previousElementSibling !== titleEl) {
            titleEl.parentNode.insertBefore(bar, titleEl.nextSibling);
        }
    }

    // 2. Direct Download Badge on the Video Player ("علامة هو")
    function ensurePlayerBadge(ctx) {
        if (!ctx.active) {
            var existing = document.getElementById('sdn-player-badge');
            if (existing) existing.remove();
            return;
        }

        var player = document.getElementById('movie_player')
                  || document.querySelector('.html5-video-player')
                  || document.querySelector('#player-container');

        if (!player) return;

        var badge = document.getElementById('sdn-player-badge');
        var curUrl = ctx.singleUrl || ctx.fullUrl;
        var modeKey = (ctx.isPlaylist ? 'playlist' : 'single') + '_' + curUrl;

        if (!badge) {
            badge = createEl('div', 'sdn-player-badge');
        }

        if (badge.dataset.modeKey !== modeKey) {
            badge.dataset.modeKey = modeKey;
            while (badge.firstChild) badge.removeChild(badge.firstChild);

            var curTitle = getVideoTitle();

            var mainBadge = createEl('span', '', 'color:#38bdf8; font-weight:800; font-size:12px; cursor:pointer;', '⚡ تنزيل SDN ▼');
            mainBadge.onclick = function(e) {
                e.stopPropagation();
                openMenuAt(badge.getBoundingClientRect(), getMediaContext());
            };
            badge.appendChild(mainBadge);

            if (ctx.isPlaylist) {
                var pVid = createEl('button', '', '', '🎬 القائمة فيديو');
                pVid.className = 'sdn-player-btn';
                pVid.onclick = function(e) {
                    e.stopPropagation();
                    triggerDirectDownload(ctx.fullUrl, 'best', 'playlist_all', 'كامل القائمة فيديو', curTitle);
                };
                badge.appendChild(pVid);

                var pAud = createEl('button', '', '', '🎵 القائمة MP3');
                pAud.className = 'sdn-player-btn btn-audio';
                pAud.onclick = function(e) {
                    e.stopPropagation();
                    triggerDirectDownload(ctx.fullUrl, 'mp3', 'playlist_all', 'كامل القائمة MP3', curTitle);
                };
                badge.appendChild(pAud);

                var pSel = createEl('button', '', '', '📋 اختيار...');
                pSel.className = 'sdn-player-btn';
                pSel.onclick = function(e) {
                    e.stopPropagation();
                    showToast('📋 جاري فتح نافذة تحديد عناصر القائمة في SDN...', 'info');
                    if (window.pywebview && window.pywebview.api && window.pywebview.api.send_to_main) {
                        window.pywebview.api.send_to_main(ctx.fullUrl, true);
                    }
                };
                badge.appendChild(pSel);
            } else {
                var b1080 = createEl('button', '', '', '🎬 1080p');
                b1080.className = 'sdn-player-btn';
                b1080.onclick = function(e) {
                    e.stopPropagation();
                    triggerDirectDownload(ctx.singleUrl, '1080p', 'single', '1080p Full HD', curTitle);
                };
                badge.appendChild(b1080);

                var b720 = createEl('button', '', '', '📺 720p');
                b720.className = 'sdn-player-btn';
                b720.onclick = function(e) {
                    e.stopPropagation();
                    triggerDirectDownload(ctx.singleUrl, '720p', 'single', '720p HD', curTitle);
                };
                badge.appendChild(b720);

                var bMp3 = createEl('button', '', '', '🎵 MP3');
                bMp3.className = 'sdn-player-btn btn-audio';
                bMp3.onclick = function(e) {
                    e.stopPropagation();
                    triggerDirectDownload(ctx.singleUrl, 'mp3', 'single', 'صوت MP3', curTitle);
                };
                badge.appendChild(bMp3);
            }
        }

        if (badge.parentNode !== player) {
            player.appendChild(badge);
        }
    }

    // 3. Secondary Floating IDM Panel
    function ensureIdmPanel(ctx) {
        var panel = document.getElementById('sdn-idm-panel');

        if (!ctx.active) {
            if (panel) panel.style.display = 'none';
            if (menu) menu.style.display = 'none';
            return;
        }

        if (!panel) {
            panel = createEl('div', 'sdn-idm-panel');
            var icon = createEl('span', '', 'color:#22c55e; font-size:13px; margin-left:4px;', '▶');
            var txt = createEl('span', 'sdnPanelText', '', ctx.isPlaylist ? 'تنزيل SDN (فيديو / قائمة)' : 'تنزيل SDN لهذا الفيديو');
            var arrow = createEl('span', '', 'color:#94a3b8; font-size:10px; margin-right:4px;', '▼');
            var sep = createEl('span', '', 'color:rgba(255,255,255,0.25); margin:0 4px;', '|');
            var dismiss = createEl('span', '', 'color:#94a3b8; font-size:12px; cursor:pointer; padding:0 2px;', '✕');
            dismiss.title = 'إخفاء مؤقت لهذا الفيديو';
            dismiss.onclick = function(e) {
                e.stopPropagation();
                panel.style.display = 'none';
                if (menu) menu.style.display = 'none';
                window.__sdn_dismissed_url = window.location.href;
            };

            panel.appendChild(icon);
            panel.appendChild(txt);
            panel.appendChild(arrow);
            panel.appendChild(sep);
            panel.appendChild(dismiss);

            panel.onclick = function(e) {
                e.stopPropagation();
                var currentCtx = getMediaContext();
                openMenuAt(panel.getBoundingClientRect(), currentCtx);
            };

            (document.body || document.documentElement).appendChild(panel);
        }

        if (window.__sdn_dismissed_url && window.__sdn_dismissed_url === window.location.href) {
            panel.style.display = 'none';
            return;
        }

        var txtEl = document.getElementById('sdnPanelText');
        if (txtEl && !txtEl.textContent.includes('جاري') && !txtEl.textContent.includes('بدأ')) {
            txtEl.textContent = ctx.isPlaylist ? 'تنزيل SDN (فيديو / قائمة)' : 'تنزيل SDN لهذا الفيديو';
        }

        panel.style.display = 'flex';
    }

    // ================================================================
    // Ultra-Fast Zero-Delay Ad Defuser & Skipper
    // ================================================================
    function dismissAdsAndDialogs() {
        try {
            var player = document.getElementById('movie_player') || document.querySelector('.html5-video-player');
            var isAdActive = false;

            if (player) {
                if (typeof player.getAdState === 'function') {
                    isAdActive = player.getAdState() > 0;
                }
                if (!isAdActive && player.classList && (player.classList.contains('ad-showing') || player.classList.contains('ad-interrupting'))) {
                    isAdActive = true;
                }
            }

            if (!isAdActive && document.querySelector('.video-ads.ytp-ad-module:not(:empty), .ytp-ad-player-overlay, .ytp-ad-text, .ytp-ad-preview-text')) {
                isAdActive = true;
            }

            var video = (player && player.querySelector('video')) || document.querySelector('video.html5-main-video') || document.querySelector('video');

            if (isAdActive && video) {
                if (!video.muted) {
                    video.muted = true;
                    video.__sdn_ad_muted = true;
                }

                var skipSelectors = [
                    '.ytp-ad-skip-button',
                    '.ytp-ad-skip-button-modern',
                    '.ytp-skip-ad-button',
                    '.ytp-ad-skip-button-slot',
                    'button.ytp-ad-skip-button-modern',
                    '.ytp-ad-overlay-close-button',
                    '#dismiss-button'
                ];
                for (var s = 0; s < skipSelectors.length; s++) {
                    var btn = document.querySelector(skipSelectors[s]);
                    if (btn) {
                        try { btn.click(); } catch (e) {}
                    }
                }

                if (player && typeof player.skipAd === 'function') {
                    try { player.skipAd(); } catch (e) {}
                }

                video.playbackRate = 16.0;

                if (video.duration && !isNaN(video.duration) && isFinite(video.duration) && video.duration < 180) {
                    var adKey = (video.currentSrc || '') + '_' + Math.floor(video.duration);
                    if (video.__sdn_last_skipped_ad !== adKey) {
                        video.__sdn_last_skipped_ad = adKey;
                        try {
                            video.currentTime = video.duration;
                        } catch (e) {}
                    }
                }

                if (video.paused) {
                    try { video.play(); } catch (e) {}
                }
            } else if (!isAdActive && video) {
                if (video.playbackRate > 2.0) {
                    video.playbackRate = 1.0;
                }
                if (video.__sdn_ad_muted) {
                    video.muted = false;
                    video.__sdn_ad_muted = false;
                }
            }

            var enforcement = document.querySelector('ytd-enforcement-message-view-model, tp-yt-paper-dialog:has(ytd-enforcement-message-view-model), tp-yt-iron-overlay-backdrop');
            if (enforcement) {
                try { enforcement.remove(); } catch (e) {}
                var playBtn = document.querySelector('.ytp-play-button');
                if (playBtn && playBtn.getAttribute('data-title-no-tooltip') === 'Play') {
                    try { playBtn.click(); } catch (e) {}
                }
                if (video && video.paused) {
                    try { video.play(); } catch (e) {}
                }
            }

            var overlayClose = document.querySelector('.ytp-ad-overlay-close-button');
            if (overlayClose) {
                try { overlayClose.click(); } catch (e) {}
            }
        } catch (e) {}
    }

    window.dismissAdsAndDialogs = dismissAdsAndDialogs;

    function loopTick() {
        try {
            var ctx = getMediaContext();
            ensureUnderTitleBar(ctx);
            ensurePlayerBadge(ctx);
            ensureIdmPanel(ctx);
            dismissAdsAndDialogs();
        } catch (e) {}
    }

    loopTick();

    if (!window.__sdn_events_hooked) {
        window.__sdn_events_hooked = true;
        setInterval(loopTick, 200);

        try {
            var observer = new MutationObserver(function() {
                loopTick();
            });
            observer.observe(document.documentElement || document.body, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['class', 'src']
            });
        } catch (e) {}

        ['yt-navigate-start', 'yt-navigate-finish', 'yt-page-data-updated', 'spfdone', 'popstate'].forEach(function(ev) {
            window.addEventListener(ev, function() {
                if (window.__sdn_dismissed_url && window.__sdn_dismissed_url !== window.location.href) {
                    window.__sdn_dismissed_url = null;
                }
                loopTick();
            });
        });

        window.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.altKey) && (e.key === 'd' || e.key === 'D' || e.key === 'ي')) {
                e.preventDefault();
                var ctx = getMediaContext();
                if (ctx.active) {
                    var mainBtn = document.getElementById('sdn-title-dl-bar') || document.getElementById('sdn-player-badge') || document.getElementById('sdn-idm-panel');
                    openMenuAt(mainBtn ? mainBtn.getBoundingClientRect() : null, ctx);
                }
            }
        });
    }

    return 'FULL_RUN_OK';
})();
 } else if (window.dismissAdsAndDialogs) { window.dismissAdsAndDialogs(); }