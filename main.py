import sys
import os
import multiprocessing

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
import threading
import webview
import webview.util
import json
import subprocess
import urllib.parse
import ctypes
import time
import logging
import hashlib
import mimetypes
import re
import secrets
import shutil
import tempfile
from pathlib import Path
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler

from version import APP_VERSION as CURRENT_APP_VERSION, GITHUB_REPO

WINDOWS_PORTABLE_ASSET = "SDN_Downloader_Standalone.exe"
WINDOWS_INSTALLER_ASSET = "SDN_Downloader_Setup.exe"
TRUSTED_UPDATE_HOSTS = {
    "github.com",
    "www.github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
    "github-releases.githubusercontent.com",
}


def _release_asset_details(assets, asset_name):
    """Return normalized metadata for one exact GitHub release asset."""
    for asset in assets or []:
        if asset.get("name") != asset_name:
            continue
        digest = asset.get("digest")
        return {
            "name": asset_name,
            "url": asset.get("browser_download_url"),
            "sha256": (
                digest.split(":", 1)[1]
                if isinstance(digest, str) and digest.startswith("sha256:")
                else None
            ),
            "size": asset.get("size"),
        }
    return None


SILENT_PORTABLE_UPDATER_SCRIPT = r"""
param(
    [int]$ParentPid,
    [string]$UpdatePath,
    [string]$TargetPath,
    [string]$BackupPath,
    [string]$LogPath,
    [string]$ScriptPath
)

$ErrorActionPreference = 'Stop'

function Write-UpdateLog([string]$Message) {
    try {
        $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
        Add-Content -LiteralPath $LogPath -Value "$stamp | $Message" -Encoding UTF8
    } catch {}
}

try {
    Write-UpdateLog "Waiting for SDN process $ParentPid to exit"
    Wait-Process -Id $ParentPid -ErrorAction SilentlyContinue

    $installed = $false
    $deadline = (Get-Date).AddMinutes(2)
    while ((Get-Date) -lt $deadline -and -not $installed) {
        try {
            if (Test-Path -LiteralPath $BackupPath) {
                Remove-Item -LiteralPath $BackupPath -Force
            }
            Move-Item -LiteralPath $TargetPath -Destination $BackupPath -Force
            try {
                Move-Item -LiteralPath $UpdatePath -Destination $TargetPath -Force
                $installed = $true
            } catch {
                if ((Test-Path -LiteralPath $BackupPath) -and -not (Test-Path -LiteralPath $TargetPath)) {
                    Move-Item -LiteralPath $BackupPath -Destination $TargetPath -Force
                }
                throw
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }

    if (-not $installed) {
        throw 'Timed out while replacing the running application'
    }

    $parentDir = Split-Path -Parent $TargetPath
    try {
        Get-ChildItem -LiteralPath $parentDir -File -Filter "python3*.dll" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
        Get-ChildItem -LiteralPath $parentDir -File -Filter "vcruntime140*.dll" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
        Get-ChildItem -LiteralPath $parentDir -File -Filter "msvcp140*.dll" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
        Get-ChildItem -LiteralPath $parentDir -File -Filter "WebView2Loader*.dll" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
    } catch {}

    Start-Sleep -Milliseconds 600
    Write-UpdateLog "Update installed at $TargetPath"
    Start-Process -FilePath $TargetPath -WorkingDirectory $parentDir
    Start-Sleep -Seconds 2
    if (Test-Path -LiteralPath $BackupPath) {
        Remove-Item -LiteralPath $BackupPath -Force
    }
    Write-UpdateLog 'Updated SDN restarted successfully'
} catch {
    Write-UpdateLog "Update failed: $($_.Exception.Message)"
    try {
        if ((Test-Path -LiteralPath $BackupPath) -and -not (Test-Path -LiteralPath $TargetPath)) {
            Move-Item -LiteralPath $BackupPath -Destination $TargetPath -Force
        }
        if (Test-Path -LiteralPath $TargetPath) {
            Start-Process -FilePath $TargetPath -WorkingDirectory (Split-Path -Parent $TargetPath)
        }
    } catch {
        Write-UpdateLog "Rollback failed: $($_.Exception.Message)"
    }
} finally {
    try { Remove-Item -LiteralPath $ScriptPath -Force } catch {}
}
""".strip()


def _version_key(value):
    """Return a comparable semantic-version tuple and ignore a leading v."""
    numbers = [int(part) for part in re.findall(r'\d+', str(value or '').lstrip('vV'))[:4]]
    return tuple((numbers + [0, 0, 0, 0])[:4])


class YouTubeBrowserBridge:
    def __init__(self, main_api):
        self.main_api = main_api

    def download_url(self, url, quality="best", mode="single", force=False, title=None):
        return self.main_api.quick_download_from_browser(url, quality, mode, force, title)

    def send_to_main(self, url, auto_playlist_select=False):
        return self.main_api.load_url_in_main(url, auto_playlist_select)

    def check_duplicate(self, url, title=None, target_type=None, is_playlist=False, total_count=None):
        return self.main_api.check_duplicate(url, title, target_type=target_type, is_playlist=is_playlist, total_count=total_count)

    def cancel_download(self):
        return self.main_api.cancel_download()

    def delete_history_item(self, filepath_or_url):
        return self.main_api.delete_history_item(filepath_or_url)

    def get_history_file_states(self):
        return self.main_api.get_history_file_states()

    def open_folder(self, path=None):
        return self.main_api.open_folder(path)

    def locate_file(self, filepath=None):
        return self.main_api.locate_file(filepath)


YOUTUBE_IDM_ADBLOCK_SCRIPT = r"""
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
    function ensureStyles() {
        if (document.getElementById('sdn-styles')) return;
        var parent = document.head || document.documentElement || document.body;
        if (!parent) return;
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
            '   position: fixed; z-index: 2147483647;',
            '   display: none; align-items: center; gap: 7px;',
            '   background: rgba(18, 18, 22, 0.88);',
            '   backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);',
            '   color: #ffffff; padding: 4px 11px; border-radius: 20px;',
            '   border: 1px solid rgba(255, 255, 255, 0.16);',
            '   box-shadow: 0 4px 20px rgba(0, 0, 0, 0.45), 0 1px 3px rgba(0, 0, 0, 0.3);',
            '   font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;',
            '   font-size: 12px; font-weight: 600; direction: rtl; user-select: none;',
            '   cursor: grab; transition: background 0.18s, border-color 0.18s, box-shadow 0.18s;',
            '}',
            '#sdn-idm-panel:hover {',
            '   background: rgba(28, 28, 34, 0.96);',
            '   border-color: rgba(255, 255, 255, 0.3);',
            '   box-shadow: 0 6px 24px rgba(0, 0, 0, 0.65);',
            '}',
            '#sdn-idm-panel.sdn-dragging {',
            '   cursor: grabbing !important;',
            '   opacity: 0.95;',
            '   transform: scale(1.02);',
            '   box-shadow: 0 12px 30px rgba(0, 0, 0, 0.8) !important;',
            '}',
            '.sdn-drag-handle {',
            '   cursor: grab; color: rgba(255, 255, 255, 0.4); font-size: 13px; padding: 0 2px;',
            '   user-select: none; display: inline-flex; align-items: center; transition: color 0.15s;',
            '}',
            '#sdn-idm-panel:hover .sdn-drag-handle { color: rgba(255, 255, 255, 0.75); }',
            '.sdn-panel-btn {',
            '   display: inline-flex; align-items: center; gap: 5px; cursor: pointer;',
            '   padding: 2px 4px; border-radius: 8px; transition: opacity 0.15s;',
            '}',
            '.sdn-panel-btn:hover { opacity: 0.85; }',
            '.sdn-panel-close {',
            '   cursor: pointer; color: rgba(255, 255, 255, 0.35); font-size: 11px; padding: 2px 4px;',
            '   border-radius: 50%; transition: all 0.15s; line-height: 1;',
            '}',
            '.sdn-panel-close:hover {',
            '   color: #ffffff; background: rgba(255, 255, 255, 0.12);',
            '}',
            '.sdn-idm-menu-item {',
            '   padding: 8px 12px; border-radius: 8px; font-size: 12.5px; font-weight: 500;',
            '   cursor: pointer; display: flex; align-items: center; justify-content: space-between;',
            '   gap: 8px; color: #f4f4f5 !important; transition: background 0.15s ease, color 0.15s ease;',
            '}',
            '.sdn-idm-menu-item:hover {',
            '   background: rgba(255, 255, 255, 0.08) !important; color: #ffffff !important;',
            '}',
            '.sdn-menu-badge {',
            '   font-size: 10.5px; font-weight: 600; padding: 2px 7px; border-radius: 6px;',
            '   background: rgba(255, 255, 255, 0.08); color: rgba(255, 255, 255, 0.7);',
            '   letter-spacing: 0.3px; direction: ltr;',
            '}',
            '.sdn-idm-menu-item:hover .sdn-menu-badge {',
            '   background: rgba(255, 255, 255, 0.15); color: #ffffff;',
            '}'
        ].join(' ');
        parent.appendChild(style);
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

    function getMenu() {
        var m = document.getElementById('sdn-idm-menu');
        if (!m) {
            var parent = document.body || document.documentElement;
            if (!parent) return null;
            m = createEl(
                'div',
                'sdn-idm-menu',
                'display:none; position:fixed; z-index:2147483647; width:295px; background:rgba(22, 22, 26, 0.95); backdrop-filter:blur(24px) saturate(180%); -webkit-backdrop-filter:blur(24px) saturate(180%); border:1px solid rgba(255, 255, 255, 0.13); border-radius:14px; padding:8px; box-shadow:0 18px 45px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.04); direction:rtl; font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; flex-direction:column; gap:2px;'
            );
            parent.appendChild(m);

            document.addEventListener('click', function(e) {
                var p = document.getElementById('sdn-idm-panel');
                if (m && !m.contains(e.target) && (!p || !p.contains(e.target))) {
                    m.style.display = 'none';
                }
            });
        }
        return m;
    }

    // Modern Toast Notification with action support
    window.showSdnToast = function(msg, type, actionData) {
        var t = document.getElementById('sdn-toast');
        if (!t) {
            t = createEl('div', 'sdn-toast', 'position:fixed; bottom:26px; left:50%; transform:translateX(-50%); z-index:2147483647; background:rgba(15, 23, 42, 0.96); backdrop-filter:blur(12px); color:#ffffff; border-radius:30px; padding:11px 22px; font-weight:bold; font-size:13px; box-shadow:0 12px 35px rgba(0,0,0,0.85); transition:all 0.3s cubic-bezier(0.4, 0, 0.2, 1); opacity:0; pointer-events:auto; font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; direction:rtl; display:flex; align-items:center; gap:12px; max-width:92vw;');
            (document.body || document.documentElement).appendChild(t);
        }
        while (t.firstChild) t.removeChild(t.firstChild);

        var borderColor = 'rgba(255, 255, 255, 0.2)';
        if (type === 'success') borderColor = 'rgba(52, 211, 153, 0.6)';
        else if (type === 'warning') borderColor = 'rgba(245, 158, 11, 0.6)';
        else if (type === 'error') borderColor = 'rgba(239, 68, 68, 0.6)';

        t.style.border = '1px solid ' + borderColor;
        t.style.boxShadow = '0 12px 35px rgba(0,0,0,0.85)';

        var textSpan = createEl('span', '', 'line-height:1.4;', msg);
        t.appendChild(textSpan);

        if (actionData && actionData.is_downloading) {
            var cancelDlBtn = createEl('button', '', 'background:#ef4444; color:#ffffff; border:none; border-radius:14px; padding:4px 12px; font-size:12px; font-weight:700; cursor:pointer; margin-right:6px; white-space:nowrap; display:inline-flex; align-items:center; gap:4px; box-shadow:0 2px 8px rgba(239,68,68,0.4);', '🛑 إيقاف التنزيل');
            cancelDlBtn.onclick = function(e) {
                e.stopPropagation();
                if (window.pywebview && window.pywebview.api && window.pywebview.api.cancel_download) {
                    window.pywebview.api.cancel_download();
                    window.showSdnToast('🛑 جاري إيقاف وإلغاء التنزيل...', 'info');
                }
            };
            t.appendChild(cancelDlBtn);
        }

        if (actionData && (actionData.url || actionData.filepath)) {
            if (actionData.url) {
                var actionBtn = createEl('button', '', 'background:#ffffff; color:#0f172a; border:none; border-radius:14px; padding:4px 12px; font-size:12px; font-weight:700; cursor:pointer; margin-right:6px; white-space:nowrap;', 'تنزيل على أي حال ↻');
                actionBtn.onclick = function(e) {
                    e.stopPropagation();
                    t.style.opacity = '0';
                    if (window.pywebview && window.pywebview.api && window.pywebview.api.download_url) {
                        window.pywebview.api.download_url(actionData.url, actionData.quality || 'best', actionData.mode || 'single', true, actionData.title || '');
                    }
                };
                t.appendChild(actionBtn);
            }

            var openFolderBtn = createEl('button', '', 'background:rgba(255,255,255,0.18); color:#ffffff; border:1px solid rgba(255,255,255,0.35); border-radius:14px; padding:4px 12px; font-size:12px; font-weight:700; cursor:pointer; margin-right:6px; white-space:nowrap; display:inline-flex; align-items:center; gap:4px;', '📁 فتح مجلد');
            openFolderBtn.onclick = function(e) {
                e.stopPropagation();
                if (window.pywebview && window.pywebview.api) {
                    if (actionData.filepath && window.pywebview.api.locate_file) {
                        window.pywebview.api.locate_file(actionData.filepath);
                    } else if (window.pywebview.api.open_folder) {
                        window.pywebview.api.open_folder(actionData.filepath || null);
                    }
                }
            };
            t.appendChild(openFolderBtn);
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
        var menu = getMenu();
        if (!menu) return;
        while (menu.firstChild) menu.removeChild(menu.firstChild);

        var curTitle = getVideoTitle();
        var header = createEl('div', '', 'display:flex; align-items:center; justify-content:space-between; padding:4px 8px 8px 8px; border-bottom:1px solid rgba(255,255,255,0.08); margin-bottom:4px;');
        var hTitle = createEl('span', '', 'font-size:12.5px; font-weight:600; color:#ffffff;', ctx.isPlaylist ? 'خيارات تحميل القائمة (SDN)' : 'خيارات تنزيل الفيديو (SDN)');
        var hClose = createEl('span', '', 'cursor:pointer; color:rgba(255,255,255,0.45); font-size:13px; padding:2px 6px; border-radius:6px; transition:all 0.15s;', '✕');
        hClose.onmouseenter = function() { hClose.style.color = '#ffffff'; hClose.style.background = 'rgba(255,255,255,0.1)'; };
        hClose.onmouseleave = function() { hClose.style.color = 'rgba(255,255,255,0.45)'; hClose.style.background = 'transparent'; };
        hClose.onclick = function(e) {
            e.stopPropagation();
            menu.style.display = 'none';
        };
        header.appendChild(hTitle);
        header.appendChild(hClose);
        menu.appendChild(header);

        function addSectionHeader(title) {
            var s = createEl('div', '', 'font-size:11px; font-weight:500; color:rgba(255,255,255,0.42); padding:6px 10px 2px 10px;');
            s.textContent = title;
            menu.appendChild(s);
        }

        function addItem(text, badgeText, callback) {
            var row = createEl('div', '', '');
            row.className = 'sdn-idm-menu-item';
            var label = createEl('span', '', 'color:#f4f4f5;', text);
            row.appendChild(label);
            if (badgeText) {
                var badge = createEl('span', '', '', badgeText);
                badge.className = 'sdn-menu-badge';
                row.appendChild(badge);
            }
            row.onclick = function(e) {
                e.stopPropagation();
                menu.style.display = 'none';
                callback();
            };
            menu.appendChild(row);
        }

        if (ctx.isPlaylist) {
            if (ctx.isWatch) {
                addSectionHeader('تحميل هذا الفيديو فقط:');
                addItem('فيديو بأعلى جودة متوفرة', 'Best', function() {
                    triggerDirectDownload(ctx.singleUrl, 'best', 'single', 'هذا الفيديو (أفضل جودة)', curTitle);
                });
                addItem('فيديو 1080p FHD لهذا المقطع', '1080p', function() {
                    triggerDirectDownload(ctx.singleUrl, '1080p', 'single', 'فيديو 1080p', curTitle);
                });
                addItem('فيديو 720p HD لهذا المقطع', '720p', function() {
                    triggerDirectDownload(ctx.singleUrl, '720p', 'single', 'فيديو 720p', curTitle);
                });
                addItem('استخراج صوت المقطع MP3', 'MP3', function() {
                    triggerDirectDownload(ctx.singleUrl, 'mp3', 'single', 'صوت MP3', curTitle);
                });
            }

            addSectionHeader('قائمة التشغيل كاملة:');
            addItem('تحميل كامل القائمة فيديو', 'All Video', function() {
                triggerDirectDownload(ctx.fullUrl, 'best', 'playlist_all', 'كامل قائمة التشغيل', curTitle);
            });
            addItem('تحميل كامل القائمة MP3', 'All MP3', function() {
                triggerDirectDownload(ctx.fullUrl, 'mp3', 'playlist_all', 'كامل القائمة MP3', curTitle);
            });
            addItem('تحديد عناصر معينة مخصصة...', 'مخصص', function() {
                showToast('📋 جاري فتح نافذة تحديد عناصر القائمة في SDN...', 'info');
                if (window.pywebview && window.pywebview.api && window.pywebview.api.send_to_main) {
                    window.pywebview.api.send_to_main(ctx.fullUrl, true);
                }
            });
        } else {
            addSectionHeader('اختر الجودة للتنزيل المباشر:');
            addItem('فيديو 1080p Full HD (MP4)', '1080p', function() {
                triggerDirectDownload(ctx.fullUrl, '1080p', 'single', '1080p Full HD', curTitle);
            });
            addItem('فيديو 720p HD (MP4)', '720p', function() {
                triggerDirectDownload(ctx.fullUrl, '720p', 'single', '720p HD', curTitle);
            });
            addItem('أفضل جودة تلقائياً (Best)', 'Best', function() {
                triggerDirectDownload(ctx.fullUrl, 'best', 'single', 'أفضل جودة', curTitle);
            });
            addItem('فيديو 480p SD (حجم خفيف)', '480p', function() {
                triggerDirectDownload(ctx.fullUrl, '480p', 'single', '480p SD', curTitle);
            });
            addItem('استخراج الصوت MP3 (عالي النقاء)', 'MP3', function() {
                triggerDirectDownload(ctx.fullUrl, 'mp3', 'single', 'صوت MP3', curTitle);
            });
        }

        var div = createEl('div', '', 'border-top:1px solid rgba(255,255,255,0.08); margin:4px 2px;');
        menu.appendChild(div);

        addItem('🛑 إيقاف التنزيل الحالي', 'إيقاف', function() {
            if (window.pywebview && window.pywebview.api && window.pywebview.api.cancel_download) {
                window.pywebview.api.cancel_download();
                showToast('🛑 تم إرسال أمر إيقاف التنزيل...', 'info');
            }
        });

        addItem('📁 فتح مجلد التنزيلات', 'مجلد', function() {
            if (window.pywebview && window.pywebview.api && window.pywebview.api.open_folder) {
                window.pywebview.api.open_folder();
            }
        });

        addItem('فتح وتعديل الرابط في محرك SDN', '↗', function() {
            if (window.pywebview && window.pywebview.api && window.pywebview.api.send_to_main) {
                window.pywebview.api.send_to_main(ctx.fullUrl, false);
                showToast('✅ تم فتح الرابط في شاشة SDN الرئيسية', 'success');
            }
        });
    }

    function openMenuAt(rect, ctx) {
        var menu = getMenu();
        if (!menu) return;
        if (menu.style.display === 'flex') {
            menu.style.display = 'none';
            return;
        }
        populateMenu(ctx);
        menu.style.display = 'flex';

        var menuW = 295;
        var menuH = menu.offsetHeight || 280;

        var top = 70;
        var left = window.innerWidth - 315;

        if (rect) {
            if (rect.bottom + menuH + 10 <= window.innerHeight) {
                top = rect.bottom + 6;
            } else if (rect.top - menuH - 6 >= 10) {
                top = rect.top - menuH - 6;
            } else {
                top = Math.max(10, window.innerHeight - menuH - 10);
            }

            left = rect.right - menuW;
            if (left < 10) left = 10;
            if (left + menuW > window.innerWidth - 10) left = window.innerWidth - menuW - 10;
        }

        menu.style.top = top + 'px';
        menu.style.left = left + 'px';
    }

    // Draggable Floating IDM Widget Controller
    function makeDraggable(el) {
        if (el.__sdn_drag_attached) return;
        el.__sdn_drag_attached = true;

        var isDragging = false;
        var startX = 0, startY = 0;
        var initialLeft = 0, initialTop = 0;
        var hasMoved = false;

        // Apply saved position or default to top-right
        try {
            var saved = localStorage.getItem('sdn_idm_pos');
            if (saved) {
                var p = JSON.parse(saved);
                var maxL = Math.max(10, window.innerWidth - 180);
                var maxT = Math.max(10, window.innerHeight - 50);
                var l = Math.min(Math.max(10, p.left), maxL);
                var t = Math.min(Math.max(10, p.top), maxT);
                el.style.left = l + 'px';
                el.style.top = t + 'px';
                el.style.right = 'auto';
            } else {
                el.style.top = '66px';
                el.style.left = Math.max(10, window.innerWidth - 180) + 'px';
                el.style.right = 'auto';
            }
        } catch (e) {
            el.style.top = '66px';
            el.style.right = '24px';
        }

        function onPointerDown(e) {
            if (e.target && e.target.classList && e.target.classList.contains('sdn-panel-close')) {
                return;
            }
            isDragging = true;
            hasMoved = false;
            startX = (e.touches && e.touches[0] ? e.touches[0].clientX : e.clientX) || 0;
            startY = (e.touches && e.touches[0] ? e.touches[0].clientY : e.clientY) || 0;

            var r = el.getBoundingClientRect();
            initialLeft = r.left;
            initialTop = r.top;

            el.style.left = initialLeft + 'px';
            el.style.top = initialTop + 'px';
            el.style.right = 'auto';

            document.addEventListener('mousemove', onPointerMove, { passive: false });
            document.addEventListener('mouseup', onPointerUp, { passive: false });
            document.addEventListener('touchmove', onPointerMove, { passive: false });
            document.addEventListener('touchend', onPointerUp, { passive: false });
        }

        function onPointerMove(e) {
            if (!isDragging) return;
            var cx = (e.touches && e.touches[0] ? e.touches[0].clientX : e.clientX) || 0;
            var cy = (e.touches && e.touches[0] ? e.touches[0].clientY : e.clientY) || 0;
            var dx = cx - startX;
            var dy = cy - startY;

            if (Math.abs(dx) > 4 || Math.abs(dy) > 4) {
                hasMoved = true;
                el.classList.add('sdn-dragging');
            }

            if (hasMoved) {
                if (e.cancelable) e.preventDefault();
                var newL = initialLeft + dx;
                var newT = initialTop + dy;

                var maxL = Math.max(10, window.innerWidth - el.offsetWidth - 10);
                var maxT = Math.max(10, window.innerHeight - el.offsetHeight - 10);

                newL = Math.max(10, Math.min(newL, maxL));
                newT = Math.max(10, Math.min(newT, maxT));

                el.style.left = newL + 'px';
                el.style.top = newT + 'px';
            }
        }

        function onPointerUp(e) {
            if (!isDragging) return;
            isDragging = false;
            el.classList.remove('sdn-dragging');

            document.removeEventListener('mousemove', onPointerMove);
            document.removeEventListener('mouseup', onPointerUp);
            document.removeEventListener('touchmove', onPointerMove);
            document.removeEventListener('touchend', onPointerUp);

            if (hasMoved) {
                try {
                    var r = el.getBoundingClientRect();
                    localStorage.setItem('sdn_idm_pos', JSON.stringify({
                        left: Math.round(r.left),
                        top: Math.round(r.top)
                    }));
                } catch (err) {}
            }
        }

        el.addEventListener('mousedown', onPointerDown);
        el.addEventListener('touchstart', onPointerDown, { passive: true });

        el.addEventListener('click', function(e) {
            if (hasMoved) {
                e.stopPropagation();
                e.preventDefault();
                hasMoved = false;
                return;
            }
            if (e.target && e.target.classList && e.target.classList.contains('sdn-panel-close')) {
                return;
            }
            e.stopPropagation();
            openMenuAt(el.getBoundingClientRect(), getMediaContext());
        });
    }

    // Single Compact Draggable Floating IDM Widget
    function ensureIdmPanel(ctx) {
        var panel = document.getElementById('sdn-idm-panel');

        if (!ctx.active) {
            if (panel) panel.style.display = 'none';
            var m = document.getElementById('sdn-idm-menu');
            if (m) m.style.display = 'none';
            return;
        }

        var parent = document.body || document.documentElement;
        if (!parent) return;

        if (!panel) {
            panel = createEl('div', 'sdn-idm-panel');
            panel.title = 'اسحب لتغيير المكان، أو انقر لاختيار الجودة والتنزيل';
            parent.appendChild(panel);
            makeDraggable(panel);
        }

        var curUrl = ctx.singleUrl || ctx.fullUrl;
        var modeKey = (ctx.isPlaylist ? 'playlist' : 'single') + '_' + curUrl;

        if (panel.dataset.modeKey !== modeKey) {
            panel.dataset.modeKey = modeKey;
            while (panel.firstChild) panel.removeChild(panel.firstChild);

            var handle = createEl('span', '', '', '⠿');
            handle.className = 'sdn-drag-handle';
            handle.title = 'اسحب لتغيير مكان الزر في أي زاوية تفضلها';
            panel.appendChild(handle);

            var mainBtn = createEl('span', '', '');
            mainBtn.className = 'sdn-panel-btn';
            mainBtn.title = 'انقر لاختيار صيغة وجودة التنزيل';

            var icon = createEl('span', '', 'color:rgba(255,255,255,0.85); font-size:12px; margin-left:2px;', '↓');
            var txt = createEl('span', 'sdnPanelText', 'color:#ffffff; font-weight:600; font-size:12px; letter-spacing:0.2px;', ctx.isPlaylist ? 'تنزيل SDN (قائمة) ▾' : 'تنزيل SDN ▾');

            mainBtn.appendChild(icon);
            mainBtn.appendChild(txt);
            panel.appendChild(mainBtn);

            var dismiss = createEl('span', '', '', '✕');
            dismiss.className = 'sdn-panel-close';
            dismiss.title = 'إخفاء مؤقت لهذا الفيديو';
            dismiss.onclick = function(e) {
                e.stopPropagation();
                panel.style.display = 'none';
                var m = document.getElementById('sdn-idm-menu');
                if (m) m.style.display = 'none';
                window.__sdn_dismissed_url = window.location.href;
            };
            panel.appendChild(dismiss);
        }

        if (window.__sdn_dismissed_url && window.__sdn_dismissed_url === window.location.href) {
            panel.style.display = 'none';
            return;
        }

        panel.style.display = 'inline-flex';
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
            ensureStyles();
            var ctx = getMediaContext();
            ensureIdmPanel(ctx);

            var old1 = document.getElementById('sdn-title-dl-bar');
            if (old1) old1.remove();
            var old2 = document.getElementById('sdn-player-badge');
            if (old2) old2.remove();
            var old3 = document.getElementById('sdn-action-pill-btn');
            if (old3) old3.remove();

            dismissAdsAndDialogs();
        } catch (e) {}
    }

    window.sdnLoopTick = loopTick;
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

        window.addEventListener('resize', function() {
            var p = document.getElementById('sdn-idm-panel');
            if (p && p.style.left && p.style.left !== 'auto') {
                var curL = parseInt(p.style.left, 10);
                var curT = parseInt(p.style.top, 10);
                var maxL = Math.max(10, window.innerWidth - (p.offsetWidth || 150) - 10);
                var maxT = Math.max(10, window.innerHeight - (p.offsetHeight || 36) - 10);
                if (curL > maxL) p.style.left = maxL + 'px';
                if (curT > maxT) p.style.top = maxT + 'px';
            }
        });

        window.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.altKey) && (e.key === 'd' || e.key === 'D' || e.key === 'ي')) {
                e.preventDefault();
                var ctx = getMediaContext();
                if (ctx.active) {
                    var p = document.getElementById('sdn-idm-panel');
                    openMenuAt(p ? p.getBoundingClientRect() : null, ctx);
                }
            }
        });
    }

    return 'FULL_RUN_OK';
})();
"""


# ============================================================
# ULTRA LOGGING & DIAGNOSTICS
# ============================================================
try:
    from app_logger import setup_logger, log_exception, get_diagnostic_info, cleanup_old_logs
except ImportError:
    # Fallback: simple logger if module not found (bare setup)
    import logging as _logging
    def setup_logger(name="SDN"): 
        _logging.basicConfig(level=_logging.DEBUG)
        return _logging.getLogger(name)
    def log_exception(logger, msg="Error"): logger.exception(msg)
    def get_diagnostic_info(): return {}
    def cleanup_old_logs(): pass

_log = setup_logger("SDN.Main")
_log.info("═" * 60)
_log.info(f"SDN v{CURRENT_APP_VERSION} - STARTING")
_log.info("═" * 60)

# ============================================================
# ULTRA PERFORMANCE: Windows API optimizations
# ============================================================
try:
    # Set process priority to HIGH for ultra responsiveness
    _PROCESS_HIGH_PRIORITY_CLASS = 0x00000080
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), _PROCESS_HIGH_PRIORITY_CLASS)
    _log.info("Process priority set to HIGH")
except Exception as e:
    _log.warning(f"Could not set process priority: {e}")

try:
    # Set AppUserModelID for Windows taskbar grouping
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"SDN.App.{CURRENT_APP_VERSION}")
except Exception as e:
    _log.debug(f"AppUserModelID not set: {e}")

# ============================================================
# إصلاح مشكلة البحث عن ملفات win-arm64 / WebView2
# ============================================================
try:
    _orig_interop_dll_path = webview.util.interop_dll_path
    def _safe_interop_dll_path(dll_name: str) -> str:
        try:
            return _orig_interop_dll_path(dll_name)
        except Exception:
            if hasattr(sys, '_MEIPASS'):
                base = sys._MEIPASS
                candidate = os.path.join(base, dll_name)
                if os.path.exists(candidate):
                    return candidate
                candidate_runtime = os.path.join(base, 'webview', 'lib', 'runtimes', dll_name, 'native')
                if os.path.exists(candidate_runtime):
                    return candidate_runtime
            if dll_name in ('win-arm64', 'win-x64', 'win-x86'):
                return sys._MEIPASS if hasattr(sys, '_MEIPASS') else '.'
            raise
    webview.util.interop_dll_path = _safe_interop_dll_path
    _log.debug("WebView2 DLL path hook installed")
except Exception as e:
    _log.warning(f"WebView2 DLL hook not installed: {e}")

# ============================================================
# ULTRA ADBLOCK: Native WebView2 request interception
# Blocks doubleclick, tracking, and ad beacons before any byte leaves the machine
# ============================================================
try:
    import webview.platforms.edgechromium as _ec
    _orig_web_resource_req = _ec.EdgeChrome.on_web_resource_request
    _orig_on_webview_ready = _ec.EdgeChrome.on_webview_ready

    _NATIVE_AD_DOMAINS = (
        'doubleclick.net',
        'googleads.g.doubleclick.net',
        '/api/stats/ads',
        '/pagead/',
        '/youtubei/v1/player/ad_break',
        '/pcs/view',
        '/ptracking',
    )

    def _native_adblock_on_web_resource_request(self, sender, args):
        try:
            uri = str(args.Request.Uri).lower()
            for pattern in _NATIVE_AD_DOMAINS:
                if pattern in uri:
                    args.Response = sender.Environment.CreateWebResourceResponse(None, 204, 'No Content', '')
                    return
        except Exception:
            pass
        _orig_web_resource_req(self, sender, args)

    def _custom_on_webview_ready(self, sender, args):
        if args.IsSuccess and sender.CoreWebView2:
            try:
                sender.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync(YOUTUBE_IDM_ADBLOCK_SCRIPT)
            except Exception as _ex:
                _log.debug(f"DocumentCreatedAsync injection note: {_ex}")
        _orig_on_webview_ready(self, sender, args)

    _ec.EdgeChrome.on_web_resource_request = _native_adblock_on_web_resource_request
    _ec.EdgeChrome.on_webview_ready = _custom_on_webview_ready
    _log.debug("WebView2 native adblock filter and early script injection installed successfully")
except Exception as _e_native_ad:
    _log.debug(f"WebView2 native adblock hook skipped: {_e_native_ad}")

# ============================================================
# ULTRA PERFORMANCE: Pre-cache heavy imports in background
# ============================================================
_preload_done = threading.Event()

def _preload_heavy_modules():
    """Pre-load yt-dlp and other heavy modules in background thread for instant first-use"""
    modules_to_preload = [
        ('downloader', ['MediaDownloader', 'validate_link', 'clean_error_message', 'auto_update_ytdlp']),
        ('yt_dlp', []),
        ('urllib.request', []),
        ('json', []),
    ]
    for mod_name, _ in modules_to_preload:
        try:
            __import__(mod_name)
            _log.debug(f"Pre-loaded: {mod_name}")
        except Exception as e:
            _log.debug(f"Pre-load skipped {mod_name}: {e}")
    _preload_done.set()
    _log.info("Module pre-loading complete")

threading.Thread(target=_preload_heavy_modules, daemon=True, name="Preloader").start()


def get_clipboard_text():
    """
    تسترجع النص المخزن في الحافظة بشكل آمن 100% وبدون أي انهيار للنظام
    Ultra: faster direct Win32 API call with single-try optimization
    """
    try:
        user32 = ctypes.windll.user32
        user32.GetClipboardData.restype = ctypes.c_void_p
        user32.OpenClipboard.argtypes = [ctypes.c_void_p]
        user32.CloseClipboard.argtypes = []

        for _ in range(3):
            if user32.OpenClipboard(None):
                try:
                    handle = user32.GetClipboardData(13) # CF_UNICODETEXT
                    if handle:
                        val = ctypes.c_wchar_p(handle).value
                        if val and isinstance(val, str):
                            return val.strip()
                finally:
                    user32.CloseClipboard()
                break
            time.sleep(0.02)
    except Exception as e:
        _log.debug(f"Clipboard read failed: {e}")
    return ""


# Only real browser extensions may talk to the loopback bridge. Regular web
# pages (and scripts embedded in them) must never be able to inject URLs.
EXTENSION_ORIGIN_PREFIXES = (
    "chrome-extension://",
    "moz-extension://",
    "safari-web-extension://",
    "ms-browser-extension://",
    "edge-extension://",
)


def _is_allowed_extension_origin(origin: str) -> bool:
    origin = (origin or "").strip().lower()
    return any(origin.startswith(prefix) for prefix in EXTENSION_ORIGIN_PREFIXES)


class ExtensionHTTPHandler(BaseHTTPRequestHandler):
    """Lightweight, origin-restricted HTTP handler for browser extensions."""

    bridge_api = None
    # Optional shared secret. When set, every POST must present it via the
    # X-SDN-Token header (the packaged extension injects it automatically).
    auth_token = None

    def log_message(self, format, *args):
        pass  # Suppress HTTP access log noise

    def _cors_headers(self):
        origin = self.headers.get("Origin", "")
        if _is_allowed_extension_origin(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-SDN-Token")

    def do_OPTIONS(self):
        origin = self.headers.get("Origin", "")
        if not _is_allowed_extension_origin(origin):
            self.send_response(403)
            self.end_headers()
            return
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def _authorized(self) -> bool:
        expected = ExtensionHTTPHandler.auth_token
        if not expected:
            return True
        provided = self.headers.get("X-SDN-Token", "")
        return secrets.compare_digest(provided, expected)

    def _reject(self, code, message):
        self.send_response(code)
        self._cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        try:
            self.wfile.write(json.dumps({"status": "error", "msg": message}).encode("utf-8"))
        except Exception:
            pass

    def do_POST(self):
        origin = self.headers.get("Origin", "")
        if not _is_allowed_extension_origin(origin):
            _log.debug("Rejected extension request from origin: %s", origin[:80])
            return self._reject(403, "Origin not allowed")
        if not self._authorized():
            return self._reject(401, "Unauthorized")

        try:
            content_length = int(self.headers.get('Content-Length', 0))
        except (TypeError, ValueError):
            content_length = 0
        if content_length <= 0 or content_length > 65536:
            return self._reject(413, "Invalid payload size")

        post_data = self.rfile.read(content_length)
        try:
            payload = json.loads(post_data.decode('utf-8'))
            url = str(payload.get('url') or '').strip()
            parsed = urllib.parse.urlsplit(url)
            if parsed.scheme in ('http', 'https') and parsed.netloc and ExtensionHTTPHandler.bridge_api:
                self.send_response(200)
                self._cors_headers()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                ExtensionHTTPHandler.bridge_api.handle_extension_url(url)
                self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
            else:
                self._reject(400, "No URL provided")
        except Exception as e:
            _log.debug(f"Extension handler error: {e}")
            self._reject(400, "Bad request")


class MediaHTTPHandler(BaseHTTPRequestHandler):
    """Loopback-only, tokenized media server with HTTP range support."""

    bridge_api = None

    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Range")
        self.end_headers()

    def do_HEAD(self):
        self._serve_media(send_body=False)

    def do_GET(self):
        self._serve_media(send_body=True)

    def _serve_media(self, send_body):
        bridge = MediaHTTPHandler.bridge_api
        path = urllib.parse.urlsplit(self.path).path
        if not bridge or not path.startswith("/media/"):
            self.send_error(404)
            return

        token = urllib.parse.unquote(path[len("/media/"):])
        if not re.fullmatch(r"[A-Za-z0-9_-]{20,128}", token):
            self.send_error(404)
            return

        filepath = bridge.resolve_media_token(token)
        if not filepath:
            self.send_error(404)
            return

        try:
            file_size = os.path.getsize(filepath)
            start = 0
            end = max(0, file_size - 1)
            status = 200
            range_header = self.headers.get("Range", "").strip()
            if range_header:
                match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header)
                if not match or not any(match.groups()):
                    self._send_range_error(file_size)
                    return
                start_text, end_text = match.groups()
                if start_text:
                    start = int(start_text)
                    end = int(end_text) if end_text else file_size - 1
                else:
                    suffix_length = int(end_text)
                    if suffix_length <= 0:
                        self._send_range_error(file_size)
                        return
                    start = max(0, file_size - suffix_length)
                    end = file_size - 1
                if start >= file_size or end < start:
                    self._send_range_error(file_size)
                    return
                end = min(end, file_size - 1)
                status = 206

            content_length = max(0, end - start + 1)
            content_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(content_length))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
            self.end_headers()

            if not send_body:
                return
            with open(filepath, "rb") as media_file:
                media_file.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk = media_file.read(min(128 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except OSError as exc:
            _log.debug(f"Media streaming error: {exc}")
            try:
                self.send_error(404)
            except Exception:
                pass

    def _send_range_error(self, file_size):
        self.send_response(416)
        self.send_header("Content-Range", f"bytes */{file_size}")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()


class DownloaderBridgeAPI:
    """ULTRA Bridge API - Interface between Python backend and WebView frontend"""

    # Upper bound for cached media tokens to keep long sessions bounded.
    _MEDIA_TOKEN_LIMIT = 4096
    
    def __init__(self):
        self._window = None
        self.save_dir = self._load_save_dir()
        self.downloader = None
        self.latest_update_info = None
        self._startup_time = time.time()
        self._update_restart_started = False
        self._update_download_active = False
        self.pending_update_path = None
        self.pending_update_kind = None
        self.pending_update_sha256 = None
        self.pending_update_size = None
        self._download_thread = None
        self._media_server = None
        self._media_port = None
        self._media_lock = threading.Lock()
        self._media_tokens = {}
        self._media_path_tokens = {}
        self._media_prepare_lock = threading.Lock()
        self._media_cache_dir = None
        self._auto_update_enabled = True
        
        ExtensionHTTPHandler.bridge_api = self
        MediaHTTPHandler.bridge_api = self
        
        _log.info(f"Bridge API initialized. Save dir: {self.save_dir}")
        
        # Start all background services
        self._start_local_media_server()
        self._start_local_extension_server()
        self._trigger_bg_auto_updates()
        self._start_auto_cache_cleaner()
        self._start_history_file_watcher()
        
        # Diagnostic dump on first run
        try:
            diag = get_diagnostic_info()
            _log.info(f"System diagnostic: {json.dumps(diag, ensure_ascii=False)}")
        except Exception:
            pass

    # ================================================================
    # ULTRA: Auto Cache Cleaner with smart scheduling
    # ================================================================
    def _start_auto_cache_cleaner(self):
        def _clean_job():
            import glob
            import shutil
            import tempfile

            # First clean after 60s, then every 12h
            time.sleep(60)
            
            while True:
                try:
                    cleaned_count = 0
                    temp_dir = tempfile.gettempdir()
                    now = time.time()
                    
                    # Clean temp files older than 4 hours
                    for pattern in ('SDN_Update_*.exe', 'SDN_*.ytdl', 'SDN_*.part', 'SDN_*.tmp'):
                        for f_path in glob.glob(os.path.join(temp_dir, pattern)):
                            try:
                                if os.path.exists(f_path) and (now - os.path.getmtime(f_path)) > 14400:
                                    os.remove(f_path)
                                    cleaned_count += 1
                            except Exception:
                                pass

                    # Compatibility copies are disposable and recreated on demand.
                    media_cache = self._get_media_cache_dir()
                    for cache_file in media_cache.glob("*.mp3"):
                        try:
                            if (now - cache_file.stat().st_atime) > 30 * 86400:
                                cache_file.unlink()
                                cleaned_count += 1
                        except OSError:
                            pass

                    # Clean old logs
                    cleanup_old_logs()
                    
                    if cleaned_count > 0:
                        _log.info(f"Cache cleaner: removed {cleaned_count} items")

                except Exception as e:
                    _log.debug(f"Cache cleaner minor issue: {e}")

                time.sleep(43200)  # 12 hours

        threading.Thread(target=_clean_job, daemon=True, name="CacheCleaner").start()

    # ================================================================
    # ULTRA: Background auto-update checker with smart dedup
    # ================================================================
    def _trigger_bg_auto_updates(self):
        def _update_job():
            time.sleep(3)  # Let UI settle
            if not self._auto_update_enabled:
                _log.info("Automatic update checks are disabled by the user")
                return
            try:
                from downloader import auto_update_ytdlp
                update_result = auto_update_ytdlp()
                _log.info(f"yt-dlp update check: {update_result}")
            except Exception as e:
                _log.warning(f"yt-dlp auto-update failed: {e}")

            try:
                up_info = self.check_app_update()
                if up_info and up_info.get('has_update'):
                    self.latest_update_info = up_info
                    if self._window:
                        self._window.evaluate_js(
                            f"if (typeof showUpdateBadge === 'function') showUpdateBadge({json.dumps(up_info)});"
                        )
                    _log.info(f"Update available: v{up_info.get('latest_version')} (current: v{CURRENT_APP_VERSION})")
                else:
                    _log.debug("App is up to date")
                    if self._window:
                        self._window.evaluate_js(
                            "if (typeof showUpdateBadge === 'function') showUpdateBadge({has_update: false});"
                        )
            except Exception as e:
                _log.warning(f"App update check failed: {e}")

        threading.Thread(target=_update_job, daemon=True, name="UpdateChecker").start()

    # ================================================================
    # Local extension bridge server
    # ================================================================
    def _start_local_extension_server(self):
        def _run_server():
            try:
                HTTPServer.allow_reuse_address = True
                server = HTTPServer(('127.0.0.1', 4567), ExtensionHTTPHandler)
                _log.info("Extension bridge server started on port 4567")
                server.serve_forever()
            except OSError as e:
                _log.warning(f"Extension server port 4567 in use: {e}")
            except Exception as e:
                _log.error(f"Extension server failed: {e}")

        threading.Thread(target=_run_server, daemon=True, name="ExtServer").start()

    def handle_extension_url(self, url):
        if self._window:
            js_code = f"if (typeof handleExtensionInput === 'function') handleExtensionInput({json.dumps(url)});"
            self._window.evaluate_js(js_code)
            _log.debug(f"Extension URL forwarded to UI: {url[:80]}...")

    def _start_local_media_server(self):
        """Start a private random-port server used only for local media playback."""
        try:
            self._media_server = ThreadingHTTPServer(("127.0.0.1", 0), MediaHTTPHandler)
            self._media_server.daemon_threads = True
            self._media_port = int(self._media_server.server_port)
            threading.Thread(
                target=self._media_server.serve_forever,
                daemon=True,
                name="MediaServer",
            ).start()
            _log.info(f"Local media server started on port {self._media_port}")
        except Exception as exc:
            self._media_server = None
            self._media_port = None
            _log.warning(f"Local media server failed: {exc}")

    def _register_media_file(self, filepath):
        """Return a tokenized HTTP URL for a real local audio file."""
        try:
            path = Path(filepath).resolve(strict=True)
            if not path.is_file() or not self._media_port:
                return path.as_uri()
            normalized = os.path.normcase(str(path))
            with self._media_lock:
                token = self._media_path_tokens.get(normalized)
                if not token:
                    token = secrets.token_urlsafe(32)
                    self._media_path_tokens[normalized] = token
                    self._media_tokens[token] = str(path)
                    self._prune_media_tokens_locked()
            return f"http://127.0.0.1:{self._media_port}/media/{token}"
        except Exception as exc:
            _log.debug(f"Could not register media file {filepath}: {exc}")
            try:
                return Path(filepath).resolve().as_uri()
            except Exception:
                return str(filepath).replace("\\", "/")

    def _prune_media_tokens_locked(self):
        """Drop the oldest media tokens once the cache exceeds its limit.

        The caller must hold ``self._media_lock``. Insertion order is preserved
        by Python dicts, so the first keys are the oldest entries.
        """
        overflow = len(self._media_tokens) - self._MEDIA_TOKEN_LIMIT
        if overflow <= 0:
            return
        for token in list(self._media_tokens.keys())[:overflow]:
            stored_path = self._media_tokens.pop(token, None)
            if stored_path is not None:
                self._media_path_tokens.pop(os.path.normcase(stored_path), None)

    def resolve_media_token(self, token):
        with self._media_lock:
            filepath = self._media_tokens.get(token)
        if filepath and os.path.isfile(filepath):
            return filepath
        return None

    def get_media_url(self, filepath):
        """Bridge method for resolving a local file to a WebView-playable URL."""
        return self._register_media_file(filepath)

    def _get_media_cache_dir(self):
        """Return the private cache used for WebView-compatible audio copies."""
        if self._media_cache_dir:
            cache_dir = Path(self._media_cache_dir)
        else:
            local_app_data = os.environ.get("LOCALAPPDATA")
            cache_root = Path(local_app_data) if local_app_data else Path.home() / ".cache"
            cache_dir = cache_root / "SDN" / "media_cache"
            self._media_cache_dir = str(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def prepare_media_playback(self, filepath):
        """
        Return a WebView-safe playback URL without modifying the source file.

        WebView2 codec availability differs between Windows editions. MP3 and
        WAV can be served directly; other supported formats are converted once
        to an MP3 cache and reused while the source file is unchanged.
        """
        audio_exts = {'.mp3', '.m4a', '.aac', '.flac', '.ogg', '.wav', '.opus', '.wma'}
        try:
            source = Path(filepath).resolve(strict=True)
            if not source.is_file() or source.suffix.lower() not in audio_exts:
                return {'ok': False, 'error': 'الملف الصوتي غير موجود أو غير مدعوم'}

            source_ext = source.suffix.lower()
            if source_ext in {'.mp3', '.wav'}:
                return {
                    'ok': True,
                    'url': self._register_media_file(str(source)),
                    'filepath': str(source),
                    'transcoded': False,
                }

            stat = source.stat()
            cache_key = hashlib.sha256(
                f"{os.path.normcase(str(source))}|{stat.st_size}|{stat.st_mtime_ns}".encode("utf-8")
            ).hexdigest()
            cache_file = self._get_media_cache_dir() / f"{cache_key}.mp3"

            with self._media_prepare_lock:
                if not cache_file.is_file() or cache_file.stat().st_size == 0:
                    from downloader import get_ffmpeg_path

                    ffmpeg_path = get_ffmpeg_path()
                    partial_file = cache_file.with_suffix(".partial.mp3")
                    try:
                        partial_file.unlink(missing_ok=True)
                    except OSError:
                        pass

                    _log.info(f"Preparing WebView-compatible audio: {source.name}")
                    process = subprocess.run(
                        [
                            ffmpeg_path,
                            "-nostdin",
                            "-hide_banner",
                            "-loglevel", "error",
                            "-y",
                            "-i", str(source),
                            "-map", "0:a:0",
                            "-vn",
                            "-c:a", "libmp3lame",
                            "-b:a", "192k",
                            "-id3v2_version", "3",
                            str(partial_file),
                        ],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=900,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                    )
                    if process.returncode != 0 or not partial_file.is_file() or partial_file.stat().st_size == 0:
                        try:
                            partial_file.unlink(missing_ok=True)
                        except OSError:
                            pass
                        detail = (process.stderr or process.stdout or "FFmpeg failed").strip()
                        _log.warning(f"Audio compatibility conversion failed for {source}: {detail[:500]}")
                        return {'ok': False, 'error': 'تعذر تجهيز الملف الصوتي للتشغيل'}

                    os.replace(partial_file, cache_file)
                    _log.info(f"Audio compatibility copy ready: {cache_file.name}")

            return {
                'ok': True,
                'url': self._register_media_file(str(cache_file)),
                'filepath': str(source),
                'transcoded': True,
                'cached_filepath': str(cache_file),
            }
        except subprocess.TimeoutExpired:
            _log.warning(f"Audio compatibility conversion timed out: {filepath}")
            return {'ok': False, 'error': 'استغرق تجهيز الملف الصوتي وقتاً طويلاً'}
        except Exception as exc:
            _log.warning(f"Could not prepare audio playback for {filepath}: {exc}")
            return {'ok': False, 'error': 'تعذر تجهيز الملف الصوتي للتشغيل'}

    def _build_audio_track(self, filepath, uploader):
        """Build one player record and prefer the compatible cached URL."""
        path_obj = Path(filepath).resolve(strict=True)
        prepared = self.prepare_media_playback(str(path_obj))
        playable_url = (
            prepared.get('url')
            if prepared.get('ok')
            else self._register_media_file(str(path_obj))
        )
        return {
            'title': path_obj.stem,
            'uploader': uploader,
            'url': playable_url,
            'playable_url': playable_url,
            'filepath': str(path_obj),
            'format': path_obj.suffix.lstrip('.').upper(),
            'size': path_obj.stat().st_size,
            'thumbnail': '',
            'playback_ready': bool(prepared.get('ok')),
            'playback_transcoded': bool(prepared.get('transcoded')),
            'playback_error': prepared.get('error', ''),
        }

    def report_audio_error(self, filepath='', error=''):
        """Receive compact player diagnostics from the WebView."""
        _log.warning(f"Audio player error | file={filepath!r} | detail={str(error)[:500]}")
        return True

    # ================================================================
    # Config & History management with corruption recovery
    # ================================================================
    def _load_save_dir(self):
        config_path = os.path.join(os.path.expanduser("~"), ".sdn_config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    dir_path = data.get("save_dir")
                    if dir_path and os.path.isdir(dir_path):
                        _log.debug(f"Loaded save dir from config: {dir_path}")
                        return dir_path
        except (json.JSONDecodeError, IOError) as e:
            _log.warning(f"Config file corrupted, resetting: {e}")
            try:
                os.remove(config_path)
            except Exception:
                pass
        except Exception as e:
            _log.debug(f"Config load skipped: {e}")
        
        default = os.path.join(os.path.expanduser("~"), "Downloads")
        _log.info(f"Using default save dir: {default}")
        return default

    def _save_config(self):
        config_path = os.path.join(os.path.expanduser("~"), ".sdn_config.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump({"save_dir": self.save_dir}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            _log.warning(f"Failed to save config: {e}")

    def get_app_info(self):
        try:
            import yt_dlp
            yt_dlp_version = getattr(yt_dlp.version, '__version__', 'unknown')
        except Exception:
            yt_dlp_version = 'unknown'
        return {
            'version': CURRENT_APP_VERSION,
            'repo': GITHUB_REPO,
            'yt_dlp_version': yt_dlp_version,
            'save_dir': self.save_dir,
        }

    def get_history(self):
        config_path = os.path.join(os.path.expanduser("~"), ".sdn_history.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get('filepath'):
                                item['file_exists'] = os.path.exists(item['filepath'])
                        return data
        except (json.JSONDecodeError, IOError) as e:
            _log.warning(f"History file corrupted, resetting: {e}")
            try:
                os.remove(config_path)
            except Exception:
                pass
        except Exception as e:
            _log.debug(f"History load skipped: {e}")
        return []

    def get_history_file_states(self):
        """Return a mapping of normalized {filepath: exists} for all history items."""
        history = self.get_history()
        states = {}
        for item in history:
            fp = item.get('filepath')
            if fp:
                norm = os.path.normcase(os.path.normpath(str(fp)))
                exists = bool(item.get('file_exists', os.path.exists(fp)))
                states[norm] = exists
                states[str(fp)] = exists
        return states

    def _start_history_file_watcher(self):
        """Monitors download history file paths in real time.
        If a file is deleted from disk (e.g. desktop/downloads), notifies the UI to hide it.
        If restored (e.g. Ctrl+Z), notifies the UI to bring it back."""
        def _watcher_loop():
            last_states = {}
            while True:
                time.sleep(0.8)
                win = getattr(self, '_window', None)
                if not win:
                    continue
                history = self.get_history()
                if not history:
                    continue

                current_states = {}
                state_changed = False
                for item in history:
                    fp = item.get('filepath')
                    if fp:
                        norm = os.path.normcase(os.path.normpath(str(fp)))
                        exists = os.path.exists(fp)
                        current_states[norm] = exists
                        current_states[str(fp)] = exists
                        if norm in last_states:
                            if last_states[norm] != exists:
                                state_changed = True
                        else:
                            last_states[norm] = exists

                if state_changed:
                    last_states = current_states
                    try:
                        js = f"if (window.onHistoryFileStateChange) window.onHistoryFileStateChange({json.dumps(current_states)});"
                        win.evaluate_js(js)
                    except Exception:
                        pass
                else:
                    last_states = current_states

        threading.Thread(target=_watcher_loop, daemon=True, name="HistoryFileWatcher").start()

    def add_history(self, item):
        history = self.get_history()
        if not isinstance(item, dict):
            return False
        # A media URL may legitimately be downloaded multiple times at different
        # qualities. Deduplicate only the exact output file.
        item_path = os.path.normcase(os.path.normpath(str(item.get('filepath') or '')))
        if item_path:
            history = [
                existing for existing in history
                if os.path.normcase(os.path.normpath(str(existing.get('filepath') or ''))) != item_path
            ]
        history.insert(0, item)
        history = history[:200]
        config_path = os.path.join(os.path.expanduser("~"), ".sdn_history.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            _log.warning(f"Failed to save history: {e}")
            return False

    def clear_history(self):
        config_path = os.path.join(os.path.expanduser("~"), ".sdn_history.json")
        try:
            if os.path.exists(config_path):
                os.remove(config_path)
            _log.info("History cleared")
            return True
        except Exception as e:
            _log.warning(f"Failed to clear history: {e}")
            return False

    def delete_history_item(self, filepath_or_url):
        """Remove a single item from history by filepath, url, or title."""
        if not filepath_or_url:
            return {'success': False}
        history = self.get_history()
        norm_target = os.path.normcase(os.path.normpath(str(filepath_or_url)))
        new_history = []
        removed = False
        for item in history:
            fp = os.path.normcase(os.path.normpath(str(item.get('filepath') or '')))
            u = str(item.get('url') or '')
            t = str(item.get('title') or '')
            if fp == norm_target or u == str(filepath_or_url) or t == str(filepath_or_url):
                removed = True
                continue
            new_history.append(item)
        if removed:
            config_path = os.path.join(os.path.expanduser("~"), ".sdn_history.json")
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(new_history, f, ensure_ascii=False, indent=2)
                return {'success': True}
            except Exception as e:
                _log.warning(f"Failed to delete history item: {e}")
        return {'success': False}

    # ================================================================
    # Window & File system utilities
    # ================================================================
    def set_window(self, window):
        self._window = window

    def get_save_dir(self):
        return self.save_dir

    def open_folder(self, path=None):
        target = path or self.save_dir
        try:
            if os.path.exists(target):
                if sys.platform == 'win32':
                    os.startfile(target)
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', target])
                else:
                    subprocess.Popen(['xdg-open', target])
                _log.debug(f"Opened folder: {target}")
        except Exception as e:
            _log.warning(f"Failed to open folder: {e}")

    def locate_file(self, filepath):
        try:
            if not filepath:
                return self.open_folder()
            norm_path = os.path.normpath(filepath)
            if os.path.exists(norm_path):
                if sys.platform == 'win32':
                    subprocess.Popen(['explorer.exe', '/select,', norm_path])
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', '-R', norm_path])
                else:
                    self.open_folder(os.path.dirname(norm_path))
                _log.debug(f"Located file: {norm_path}")
            else:
                self.open_folder(os.path.dirname(norm_path) if os.path.dirname(norm_path) else None)
        except Exception as e:
            _log.warning(f"Failed to locate file: {e}")
            self.open_folder()

    def play_file(self, filepath):
        """Open or play media file using native system handler."""
        try:
            norm_path = os.path.normpath(str(filepath or ''))
            if os.path.exists(norm_path):
                if sys.platform == 'win32':
                    os.startfile(norm_path)
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', norm_path])
                else:
                    subprocess.Popen(['xdg-open', norm_path])
                return {'success': True}
        except Exception as e:
            _log.warning(f"Failed to play file: {e}")
        return {'success': False}

    def check_duplicate(self, url=None, title=None, target_type=None, is_playlist=False, total_count=None):
        """Check if URL or title has already been downloaded into save_dir or history to prevent duplicate waste.
        Respects format: downloading MP3 when video exists (or vice versa) is allowed!
        Only flags duplicate if the SAME format (video vs video, or audio vs audio) already exists.
        Supports full playlist duplicate detection as well."""
        history = self.get_history() or []
        import re

        AUDIO_EXTS = {'.mp3', '.m4a', '.flac', '.wav', '.opus', '.ogg', '.wma', '.aac'}
        VIDEO_EXTS = {'.mp4', '.mkv', '.webm', '.avi', '.mov', '.flv', '.wmv', '.m4v'}
        VALID_MEDIA_EXTS = AUDIO_EXTS | VIDEO_EXTS

        # Normalize target_type: 'audio', 'video', or None (check both)
        norm_target = None
        if target_type:
            tt_str = str(target_type).strip().lower()
            if tt_str in ('audio', 'mp3', 'm4a', 'flac', 'opus', 'wav', 'aac') or 'audio' in tt_str or 'صوت' in tt_str:
                norm_target = 'audio'
            elif tt_str in ('video', 'mp4', 'mkv', 'webm', 'avi', 'mov', 'فيديو') or 'video' in tt_str:
                norm_target = 'video'

        def _get_entry_type(entry_name_or_ext, hist_item=None):
            if hist_item:
                h_type = str(hist_item.get('type') or '').lower()
                if h_type == 'audio':
                    return 'audio'
                if h_type == 'video':
                    return 'video'
                h_quality = str(hist_item.get('quality') or '').lower()
                if 'mp3' in h_quality or 'صوت' in h_quality:
                    return 'audio'
                if 'video' in h_quality or 'فيديو' in h_quality:
                    return 'video'
            if entry_name_or_ext:
                s = str(entry_name_or_ext).strip().lower()
                if not s.startswith('.'):
                    s = Path(s).suffix.lower()
                if s in AUDIO_EXTS:
                    return 'audio'
                if s in VIDEO_EXTS:
                    return 'video'
            return None

        # Check for playlist duplicate
        is_pl = bool(is_playlist or ('list=' in str(url or '')) or ('/playlist' in str(url or '')))
        if is_pl:
            target_exts = AUDIO_EXTS if norm_target == 'audio' else VIDEO_EXTS
            # 1. Check if playlist folder exists in save_dir and contains files of the target format
            if os.path.exists(self.save_dir):
                norm_p_title = title.strip().lower() if title else ""
                try:
                    with os.scandir(self.save_dir) as entries:
                        for entry in entries:
                            if entry.is_dir():
                                e_name_lower = entry.name.strip().lower()
                                is_match = False
                                if norm_p_title and (norm_p_title in e_name_lower or e_name_lower in norm_p_title):
                                    is_match = True
                                elif 'watch later' in e_name_lower or 'مشاهدة لاحقاً' in e_name_lower or 'مشاهده لاحقا' in e_name_lower:
                                    if 'WL' in (url or '').upper() or 'watch later' in norm_p_title or 'مشاهدة' in norm_p_title or 'مشاهده' in norm_p_title:
                                        is_match = True
                                
                                if is_match:
                                    matching_files = []
                                    for sub_entry in os.scandir(entry.path):
                                        if sub_entry.is_file():
                                            fext = Path(sub_entry.name).suffix.lower()
                                            if fext in target_exts and os.path.getsize(sub_entry.path) > 1024:
                                                matching_files.append(sub_entry.path)
                                    if len(matching_files) >= 1:
                                        tot = int(total_count) if (total_count and int(total_count) > 0) else None
                                        if tot and len(matching_files) < tot:
                                            _log.info(f"Playlist folder partial match: {entry.name} ({len(matching_files)}/{tot} items in {norm_target})")
                                            return {
                                                'is_duplicate': False,
                                                'is_partial': True,
                                                'is_playlist': True,
                                                'matched_title': entry.name,
                                                'filepath': entry.path,
                                                'reason': 'playlist_partial',
                                                'format': norm_target or 'media',
                                                'existing_count': len(matching_files),
                                                'total_count': tot,
                                                'remaining_count': tot - len(matching_files),
                                                'count': len(matching_files)
                                            }
                                        _log.info(f"Playlist folder duplicate found: {entry.name} ({len(matching_files)} items in {norm_target})")
                                        return {
                                            'is_duplicate': True,
                                            'is_playlist': True,
                                            'matched_title': entry.name,
                                            'filepath': entry.path,
                                            'reason': 'playlist_folder_exists',
                                            'format': norm_target or 'media',
                                            'count': len(matching_files),
                                            'total_count': tot or len(matching_files)
                                        }
                except Exception as ex:
                    _log.debug(f"Playlist folder scan exception: {ex}")

            # 2. Check history for playlist items with target format
            if url and 'list=' in url:
                m_list = re.search(r'list=([a-zA-Z0-9_-]+)', url)
                if m_list:
                    list_id = m_list.group(1)
                    hist_matches = 0
                    first_fp = ''
                    for h in history:
                        h_url = h.get('url', '')
                        if list_id in h_url:
                            fp = h.get('filepath', '')
                            if fp and os.path.exists(fp):
                                if _get_entry_type(fp, hist_item=h) == norm_target:
                                    hist_matches += 1
                                    if not first_fp:
                                        first_fp = fp
                    if hist_matches >= 3:
                        tot = int(total_count) if (total_count and int(total_count) > 0) else None
                        if tot and hist_matches < tot:
                            return {
                                'is_duplicate': False,
                                'is_partial': True,
                                'is_playlist': True,
                                'matched_title': title or 'قائمة تشغيل سابقة',
                                'filepath': first_fp,
                                'reason': 'playlist_partial_history',
                                'format': norm_target or 'media',
                                'existing_count': hist_matches,
                                'total_count': tot,
                                'remaining_count': tot - hist_matches,
                                'count': hist_matches
                            }
                        return {
                            'is_duplicate': True,
                            'is_playlist': True,
                            'matched_title': title or 'قائمة تشغيل سابقة',
                            'filepath': first_fp,
                            'reason': 'playlist_history',
                            'format': norm_target or 'media',
                            'count': hist_matches,
                            'total_count': tot or hist_matches
                        }

        def _norm_title(t):
            if not t:
                return ""
            t = re.sub(r'\.(?:mp4|mkv|webm|avi|mov|flv|wmv|m4v|mp3|m4a|flac|wav|opus|ogg|wma|aac)$', '', t, flags=re.IGNORECASE)
            t = re.sub(r'[\(\[\{].*?[\)\]\}]', '', t)
            t = re.sub(r'(?:official\s*(?:music\s*)?video|official\s*audio|lyrics?|full\s*album|4k|hd|1080p|720p|480p|360p)', '', t, flags=re.IGNORECASE)
            return "".join(c for c in t if c.isalnum()).lower()

        def _is_match(t1, t2):
            if not t1 or not t2:
                return False
            r1 = "".join(c for c in t1 if c.isalnum()).lower()
            r2 = "".join(c for c in t2 if c.isalnum()).lower()
            if r1 and r2 and r1 == r2:
                return True
            c1 = _norm_title(t1)
            c2 = _norm_title(t2)
            if c1 and c2 and c1 == c2:
                return True
            for a, b in ((c1, c2), (r1, r2)):
                if a and b:
                    shorter, longer = min(len(a), len(b)), max(len(a), len(b))
                    if shorter >= 8 and (a in b or b in a) and (shorter / longer >= 0.80):
                        return True
            return False

        # 1. Check history by URL
        if url:
            from downloader import clean_url
            try:
                cleaned = clean_url(url)
            except Exception:
                cleaned = url.split('&')[0]

            v_id = None
            m = re.search(r'(?:v=|\/shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})', url)
            if m:
                v_id = m.group(1)

            for h in history:
                h_url = h.get('url', '')
                if not h_url:
                    continue
                is_url_match = False
                if v_id:
                    hm = re.search(r'(?:v=|\/shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})', h_url)
                    if hm and hm.group(1) == v_id:
                        is_url_match = True
                if not is_url_match:
                    try:
                        clean_h = clean_url(h_url)
                    except Exception:
                        clean_h = h_url.split('&')[0]
                    if h_url == url or (cleaned and clean_h and cleaned == clean_h):
                        is_url_match = True

                if is_url_match:
                    fp = h.get('filepath', '')
                    if not fp or os.path.exists(fp):
                        h_entry_type = _get_entry_type(fp, hist_item=h)
                        if norm_target and h_entry_type and h_entry_type != norm_target:
                            # Different format: e.g. existing is audio, user wants video -> ALLOWED!
                            continue
                        return {
                            'is_duplicate': True,
                            'matched_title': h.get('title') or 'مقطع سابق',
                            'filepath': fp,
                            'reason': 'url',
                            'format': h_entry_type or norm_target or 'media'
                        }

        # 2. Check history and save_dir by title
        if title:
            # Check history
            for h in history:
                h_title = h.get('title', '')
                if h_title and _is_match(title, h_title):
                    fp = h.get('filepath', '')
                    if not fp or os.path.exists(fp):
                        h_entry_type = _get_entry_type(fp, hist_item=h)
                        if norm_target and h_entry_type and h_entry_type != norm_target:
                            # Different format: e.g. existing is audio, user wants video -> ALLOWED!
                            continue
                        return {
                            'is_duplicate': True,
                            'matched_title': h_title,
                            'filepath': fp,
                            'reason': 'title',
                            'format': h_entry_type or norm_target or 'media'
                        }

            # Check save_dir files (and subfolders for playlists)
            if os.path.exists(self.save_dir):
                def _scan_folder(folder_path, depth=0):
                    if depth > 1:
                        return None
                    try:
                        with os.scandir(folder_path) as entries:
                            for entry in entries:
                                if entry.is_file():
                                    ext = Path(entry.name).suffix.lower()
                                    if ext not in VALID_MEDIA_EXTS:
                                        continue
                                    stem = Path(entry.name).stem
                                    if _is_match(title, stem):
                                        entry_type = _get_entry_type(ext)
                                        if norm_target and entry_type and entry_type != norm_target:
                                            continue
                                        return {
                                            'is_duplicate': True,
                                            'matched_title': entry.name,
                                            'filepath': entry.path,
                                            'reason': 'file_exists',
                                            'format': entry_type or norm_target or 'media'
                                        }
                                elif entry.is_dir() and depth == 0:
                                    res_sub = _scan_folder(entry.path, depth=depth + 1)
                                    if res_sub:
                                        return res_sub
                    except Exception:
                        pass
                    return None

                disk_match = _scan_folder(self.save_dir)
                if disk_match:
                    return disk_match

        return {'is_duplicate': False, 'matched_title': '', 'filepath': ''}

    def choose_folder(self):
        if self._window:
            result = self._window.create_file_dialog(webview.FOLDER_DIALOG, directory=self.save_dir)
            if result and len(result) > 0:
                self.save_dir = result[0]
                self._save_config()
                _log.info(f"Save directory changed to: {self.save_dir}")
                return self.save_dir
        return self.save_dir

    def choose_cookie_file(self):
        if self._window:
            file_types = ('Cookie Files (*.txt)', 'All files (*.*)')
            result = self._window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
            if result and len(result) > 0:
                _log.debug(f"Cookie file selected: {result[0]}")
                return result[0]
        return ""

    # ================================================================
    # Music Player APIs
    # ================================================================
    def scan_music_folder(self, folder_path=None):
        """Recursively scan the download folder and return playable local tracks."""
        scan_dir = folder_path or self.save_dir
        if not os.path.isdir(scan_dir):
            return {'tracks': [], 'folder': scan_dir}
        audio_exts = {'.mp3', '.m4a', '.aac', '.flac', '.ogg', '.wav', '.opus', '.wma'}
        tracks = []
        try:
            for entry in Path(scan_dir).rglob('*'):
                if not entry.is_file() or entry.suffix.lower() not in audio_exts:
                    continue
                uploader = entry.parent.name if entry.parent != Path(scan_dir) else 'مجلد التنزيلات'
                tracks.append(self._build_audio_track(entry, uploader))
        except Exception as e:
            _log.warning(f"Music scan error: {e}")

        # Sort by modification time without hitting the filesystem inside the
        # comparison; files can be deleted while a large library is scanned.
        def _track_mtime(track):
            try:
                return os.path.getmtime(track['filepath'])
            except OSError:
                return 0.0

        tracks.sort(key=_track_mtime, reverse=True)
        _log.info(f"Scanned {len(tracks)} audio files in {scan_dir}")
        return {'tracks': tracks, 'folder': scan_dir}

    def add_music_files(self):
        """Open file dialog to pick audio files to add to the player"""
        if self._window:
            file_types = (
                'Audio Files (*.mp3;*.m4a;*.aac;*.flac;*.ogg;*.wav;*.opus;*.wma)',
                'All files (*.*)'
            )
            result = self._window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=True,
                file_types=file_types
            )
            if result:
                tracks = []
                for fpath in result:
                    path_obj = Path(fpath).resolve()
                    tracks.append(self._build_audio_track(path_obj, 'مضافة يدوياً'))
                return {'tracks': tracks}
        return {'tracks': []}

    def delete_music_track(self, filepath):
        """Delete an audio file from disk"""
        try:
            if filepath and os.path.isfile(filepath):
                os.remove(filepath)
                _log.info(f"Deleted music file: {filepath}")
                return {'ok': True}
            return {'ok': False, 'error': 'الملف غير موجود'}
        except Exception as e:
            _log.warning(f"Delete music error: {e}")
            return {'ok': False, 'error': str(e)}

    # ================================================================
    # Download & Media methods with Ultra error handling
    # ================================================================
    def get_clipboard(self):
        return get_clipboard_text()

    def validate_link(self, url, proxy=None):
        try:
            from downloader import validate_link
            result = validate_link(url, proxy=proxy)
            _log.debug(f"Link validation: {result.get('valid')} - {url[:60]}...")
            return result
        except Exception as e:
            from downloader import clean_error_message
            _log.warning(f"Link validation exception: {e}")
            return {'valid': False, 'reason': clean_error_message(e, url=url)}

    def fetch_info(self, url, browser_cookies='none', proxy=None):
        try:
            if not self.downloader:
                from downloader import MediaDownloader
                self.downloader = MediaDownloader()
                _log.info("MediaDownloader initialized")
            
            clean_proxy = (proxy or '').strip() or None
            info = self.downloader.fetch_info(url, browser_cookies=browser_cookies, proxy=clean_proxy)
            title = info.get('title', 'Unknown') if isinstance(info, dict) else 'Unknown'
            _log.debug(f"Fetched info for: {title[:50]}...")
            return {'data': info, 'error': None}
        except Exception as e:
            from downloader import clean_error_message
            err_msg = clean_error_message(e, url=url)
            _log.error(f"Fetch info failed for {url[:60]}: {err_msg}")
            return {'data': None, 'error': err_msg}

    def start_download(self, url, option, browser_cookies='none'):
        if self._download_thread and self._download_thread.is_alive():
            return {'started': False, 'error': 'يوجد تنزيل آخر قيد التنفيذ.'}
        if not isinstance(option, dict):
            return {'started': False, 'error': 'خيار التنزيل غير صالح.'}

        # Format-aware duplicate check for single item & playlist downloads
        if not option.get('allow_duplicate'):
            target_type = option.get('type', 'video')
            if target_type not in ('audio', 'video'):
                target_type = 'audio' if 'mp3' in str(option.get('ext', '')).lower() else 'video'
            title = option.get('media_title') or option.get('title')
            is_playlist = bool(option.get('is_playlist'))
            total_items_count = int(option.get('playlist_count') or len(option.get('playlist_items') or []) or 0) if is_playlist else 1
            dup = self.check_duplicate(url, title, target_type=target_type, is_playlist=is_playlist, total_count=total_items_count)
            if dup and dup.get('is_duplicate'):
                type_name = "صوت (Audio)" if target_type == 'audio' else "فيديو (Video)"
                if dup.get('is_playlist'):
                    return {
                        'started': False,
                        'error': f"⚠️ جميع مقاطع هذه القائمة ({dup.get('count', 0)} مقطع) موجودة مسبقاً بنفس الصيغة ({type_name}) في مجلد التنزيلات!"
                    }
                return {
                    'started': False,
                    'error': f"⚠️ هذا المقطع موجود بالفعل بنفس الصيغة ({type_name}) في مجلد التنزيلات!"
                }

        _log.info(f"Download queued: {url[:80]}... (type: {option.get('type', 'video')})")
        self._download_thread = threading.Thread(
            target=self._async_download,
            args=(url, option, browser_cookies),
            daemon=True,
            name=f"DL-{url[:20]}"
        )
        self._download_thread.start()
        return {'started': True}

    def cancel_download(self):
        if self.downloader:
            self.downloader.cancel()
            _log.info("Download cancellation requested")
            return {'cancelled': True}
        return {'cancelled': False}

    # ================================================================
    # Playlist Session Persistence & Automatic Resumption System
    # ================================================================
    @staticmethod
    def _get_playlist_session_file():
        return os.path.join(os.path.expanduser("~"), ".sdn_playlist_session.json")

    def _save_playlist_session(self, session_data):
        session_file = self._get_playlist_session_file()
        try:
            temp_file = session_file + f".tmp.{os.getpid()}"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            if os.path.exists(session_file):
                try:
                    os.remove(session_file)
                except Exception:
                    pass
            os.replace(temp_file, session_file)
            _log.debug(f"Saved playlist session: {session_data.get('completed_count')}/{session_data.get('total_count')}")
        except Exception as e:
            _log.warning(f"Failed to save playlist session: {e}")

    def _load_playlist_session(self):
        session_file = self._get_playlist_session_file()
        if not os.path.exists(session_file):
            return None
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            _log.warning(f"Failed to load playlist session: {e}")
        return None

    def get_unfinished_playlist_session(self):
        """Returns any active/interrupted playlist session so the user can resume remaining videos."""
        session = self._load_playlist_session()
        if session:
            rem = session.get('remaining_indices') or []
            status = session.get('status', 'in_progress')
            if len(rem) > 0 and status in ('in_progress', 'paused', 'interrupted'):
                total = session.get('total_count') or session.get('playlist_count') or (session.get('completed_count', 0) + len(rem))
                session['total_count'] = total
                session['remaining_count'] = len(rem)
                session['playlist_title'] = session.get('playlist_title') or session.get('title') or 'قائمة تشغيل'
                return {
                    'has_session': True,
                    'session': session
                }
        return {'has_session': False}

    def discard_unfinished_playlist_session(self):
        """Discards any saved playlist session when user cancels or when completed."""
        session_file = self._get_playlist_session_file()
        try:
            if os.path.exists(session_file):
                os.remove(session_file)
            _log.info("Discarded active playlist session")
            return {'success': True, 'discarded': True}
        except Exception as e:
            _log.warning(f"Error removing playlist session: {e}")
            return {'success': False, 'discarded': False, 'error': str(e)}

    def resume_playlist_download(self):
        """Resumes downloading the remaining items from an interrupted playlist session."""
        session_info = self.get_unfinished_playlist_session()
        if not session_info.get('has_session'):
            return {'success': False, 'error': 'لا توجد جلسة قائمة تشغيل محفوظة للاستئناف.'}

        session = session_info['session']
        url = session.get('url')
        option = session.get('option') or {}
        remaining = session.get('remaining_indices') or []

        if not url or not remaining:
            self.discard_unfinished_playlist_session()
            return {'success': False, 'error': 'بيانات الجلسة غير مكتملة.'}

        # Configure download option to target ONLY remaining indices
        resume_opt = dict(option)
        resume_opt['is_playlist'] = True
        resume_opt['playlist_items'] = remaining
        resume_opt['playlist_count'] = len(remaining)
        resume_opt['is_resumed_session'] = True
        resume_opt['resumed_from_total'] = session.get('total_count', len(remaining))
        resume_opt['previously_completed'] = session.get('completed_count', 0)

        _log.info(f"Resuming playlist '{session.get('title')}' with {len(remaining)} remaining items: {remaining}")
        res = self.start_download(url, resume_opt, browser_cookies=resume_opt.get('cookies', 'none'))
        return {
            'success': bool(res.get('started')),
            'remaining_count': len(remaining),
            'total_count': session.get('total_count'),
            'completed_count': session.get('completed_count'),
            'title': session.get('title'),
            'error': res.get('error')
        }

    def set_auto_update_enabled(self, enabled=True):
        """Respect the user's auto-update preference from the settings screen."""
        self._auto_update_enabled = bool(enabled)
        _log.info(f"Automatic updates {'enabled' if self._auto_update_enabled else 'disabled'} by user")
        return {'ok': True, 'enabled': self._auto_update_enabled}

    def update_ytdlp_engine(self, force=True):
        """Update the yt-dlp extraction engine (verified PyPI wheel when packaged)."""
        try:
            from downloader import auto_update_ytdlp
            result = auto_update_ytdlp(force=bool(force))
            _log.info(f"Manual yt-dlp engine update: {result}")
            return result
        except Exception as e:
            _log.error(f"Manual yt-dlp engine update failed: {e}")
            return {'updated': False, 'reason': str(e), 'version': 'unknown'}

    def restart_app(self):
        """Relaunch the application so a staged engine update takes effect."""
        try:
            if getattr(sys, 'frozen', False):
                subprocess.Popen([sys.executable], close_fds=True)
            else:
                subprocess.Popen([sys.executable, os.path.abspath(__file__)], close_fds=True)
            _log.info("Restarting application for engine update")
            time.sleep(0.2)
            os._exit(0)
            return {'success': True}
        except Exception as e:
            _log.error(f"Restart failed: {e}")
            return {'success': False, 'error': str(e)}

    # ================================================================
    # YouTube In-App Login & Session Management
    # ================================================================
    @staticmethod
    def _check_cookie_auth(cookies):
        if not cookies:
            return False
        from http.cookies import BaseCookie
        keys = set()
        for c in cookies:
            if isinstance(c, BaseCookie):
                for morsel in c.values():
                    k = getattr(morsel, "key", "")
                    if k:
                        keys.add(k)
            elif isinstance(c, dict):
                k = c.get("name") or c.get("key") or ""
                if k:
                    keys.add(k)
            elif hasattr(c, "key"):
                k = getattr(c, "key", "")
                if k:
                    keys.add(k)
        return "LOGIN_INFO" in keys or ("SID" in keys and "SAPISID" in keys)

    def get_youtube_login_status(self):
        try:
            from downloader import is_youtube_logged_in
            logged_in = is_youtube_logged_in()
            return {'logged_in': logged_in}
        except Exception as e:
            _log.warning(f"Error checking YouTube login status: {e}")
            return {'logged_in': False, 'error': str(e)}

    def logout_youtube(self):
        try:
            from downloader import logout_youtube
            res = logout_youtube()
            _log.info("Logged out from YouTube session")
            return {'success': res}
        except Exception as e:
            _log.error(f"Error logging out from YouTube: {e}")
            return {'success': False, 'error': str(e)}

    def start_youtube_login(self):
        """Open a dedicated window for YouTube login and extract session cookies automatically."""
        threading.Thread(target=self._run_youtube_login_flow, daemon=True).start()
        return {'started': True}

    def _run_youtube_login_flow(self):
        try:
            import webview
            from downloader import save_cookies_to_netscape_file, get_youtube_session_cookie_path

            login_url = "https://accounts.google.com/ServiceLogin?service=youtube&continue=https%3A%2F%2Fwww.youtube.com%2F"
            login_win = webview.create_window(
                title='تسجيل الدخول إلى YouTube - SDN Downloader',
                url=login_url,
                width=620,
                height=740,
                resizable=True,
                background_color='#0f0f0f'
            )

            def monitor_cookies():
                cookie_path = get_youtube_session_cookie_path()
                max_checks = 180
                for _ in range(max_checks):
                    time.sleep(1.5)
                    try:
                        cookies = login_win.get_cookies()
                        if not cookies:
                            continue
                        if self._check_cookie_auth(cookies):
                            if save_cookies_to_netscape_file(cookies, cookie_path):
                                _log.info("YouTube session cookies saved successfully")
                                try:
                                    login_win.destroy()
                                except Exception:
                                    pass
                                if self._window:
                                    self._window.evaluate_js("if (window.onYouTubeLoginComplete) window.onYouTubeLoginComplete(true);")
                                return
                    except Exception:
                        break

            threading.Thread(target=monitor_cookies, daemon=True).start()

        except Exception as e:
            _log.error(f"Failed to start YouTube login flow: {e}")
            if self._window:
                self._window.evaluate_js(f"if (window.onYouTubeLoginComplete) window.onYouTubeLoginComplete(false, '{str(e)}');")

    # ================================================================
    # In-App YouTube Smart Browser with AdBlocker & IDM Download Sniffer
    # ================================================================
    def open_youtube_browser(self, start_url=None):
        """Open the integrated Ad-Free YouTube Browser with IDM-style Floating Download Widget."""
        threading.Thread(target=self._run_youtube_browser, args=(start_url,), daemon=True).start()
        return {'success': True}

    def _run_youtube_browser(self, start_url=None):
        try:
            import webview
            target_url = start_url or "https://www.youtube.com"
            bridge = YouTubeBrowserBridge(self)

            browser_win = webview.create_window(
                title='متصفح YouTube الذكي - SDN Downloader (بدون إعلانات + تحميل فوري)',
                url=target_url,
                width=1180,
                height=780,
                resizable=True,
                background_color='#0f0f0f',
                js_api=bridge
            )
            self._youtube_browser_win = browser_win

            is_closed = [False]

            def on_closed():
                is_closed[0] = True
                self._youtube_browser_win = None

            def on_loaded():
                try:
                    browser_win.evaluate_js(YOUTUBE_IDM_ADBLOCK_SCRIPT)
                except Exception as ex:
                    _log.debug(f"on_loaded injection note: {ex}")

            try:
                browser_win.events.loaded += on_loaded
                browser_win.events.closed += on_closed
            except Exception as e_ev:
                _log.debug(f"Events hook note: {e_ev}")

            def inject_loop():
                # Keep running as long as the browser window is open
                last_cookie_sync = 0
                while not is_closed[0]:
                    try:
                        browser_win.evaluate_js(
                            "if (!window.__sdn_ublock_installed) { " + YOUTUBE_IDM_ADBLOCK_SCRIPT + " } else { if (window.sdnLoopTick) { window.sdnLoopTick(); } else if (window.dismissAdsAndDialogs) { window.dismissAdsAndDialogs(); } }"
                        )
                    except Exception as e:
                        err = str(e).lower()
                        if 'destroyed' in err or 'closed' in err or 'disposed' in err:
                            break

                    now = time.time()
                    if now - last_cookie_sync > 5.0:
                        last_cookie_sync = now
                        try:
                            cookies = browser_win.get_cookies()
                            if self._check_cookie_auth(cookies):
                                from downloader import save_cookies_to_netscape_file, get_youtube_session_cookie_path
                                save_cookies_to_netscape_file(cookies, get_youtube_session_cookie_path())
                                if self._window:
                                    self._window.evaluate_js("if (window.onYouTubeLoginComplete) window.onYouTubeLoginComplete(true);")
                        except Exception:
                            pass

                    time.sleep(1.0)

            threading.Thread(target=inject_loop, daemon=True).start()

        except Exception as e:
            _log.error(f"Failed to open YouTube browser: {e}")

    def _notify_browser_toast(self, msg, toast_type='info', is_dup=False, dup_url=None, quality='best', mode='single', title=None, filepath=None, is_downloading=False):
        if getattr(self, '_youtube_browser_win', None):
            try:
                action_data = None
                if is_dup and dup_url:
                    action_data = {'url': dup_url, 'quality': quality, 'mode': mode, 'title': title or '', 'filepath': filepath or ''}
                elif filepath:
                    action_data = {'filepath': filepath or ''}
                if is_downloading:
                    if not action_data:
                        action_data = {}
                    action_data['is_downloading'] = True
                js_call = f"if (window.showSdnToast) window.showSdnToast({json.dumps(msg)}, {json.dumps(toast_type)}, {json.dumps(action_data)});"
                self._youtube_browser_win.evaluate_js(js_call)
            except Exception as e:
                _log.debug(f"Could not notify browser toast: {e}")

    def quick_download_from_browser(self, url, quality="best", mode="single", force=False, title=None):
        """Called from the in-app YouTube Browser to download directly in background without switching windows."""
        _log.info(f"Direct browser quick download: {url} (quality: {quality}, mode: {mode}, force: {force})")

        if mode == "playlist_select":
            self.load_url_in_main(url, auto_playlist_select=True)
            return {'success': True, 'mode': 'playlist_select'}

        is_audio = (str(quality).lower() == 'mp3' or 'audio' in str(quality).lower())
        target_type = 'audio' if is_audio else 'video'

        # Duplicate check before downloading:
        if not force:
            is_pl = (mode == 'playlist_all') or ('list=' in url)
            dup_info = self.check_duplicate(url=url, title=title, target_type=target_type, is_playlist=is_pl)
            if dup_info.get('is_duplicate'):
                format_name = 'صوت MP3' if is_audio else 'فيديو'
                if dup_info.get('is_playlist'):
                    msg = f"⚠️ هذه القائمة تم تنزيلها مسبقاً بصيغة ({format_name}) وهي موجودة بالفعل في جهازك!"
                else:
                    msg = f"⚠️ هذا المقطع تم تنزيله مسبقاً بصيغة ({format_name}) وهو موجود بالفعل في جهازك!"
                self._notify_browser_toast(msg, 'warning', is_dup=True, dup_url=url, quality=quality, mode=mode, title=title, filepath=dup_info.get('filepath'))
                return {'success': False, 'duplicate': True, 'msg': msg}

        if is_audio:
            option = {
                'type': 'audio',
                'quality_tag': 'MP3',
                'label': 'صوت MP3 (320kbps)',
                'ext': 'mp3',
                'format_id': 'bestaudio/best',
                'media_title': title or 'مقطع صوتي',
                'turbo': True
            }
        else:
            height = None
            if '1080' in str(quality):
                height = 1080
            elif '720' in str(quality):
                height = 720
            elif '480' in str(quality):
                height = 480

            from downloader import _video_selector
            option = {
                'type': 'video',
                'quality_tag': quality if quality != 'best' else 'Best',
                'label': f'فيديو ({quality})',
                'ext': 'mp4',
                'format_id': _video_selector(height),
                'media_title': title or 'مقطع فيديو',
                'turbo': True
            }

        if mode == 'playlist_all':
            option['is_playlist'] = True
            option['playlist_mode'] = 'all'

        folder_name = Path(self.save_dir).name or self.save_dir
        q_label = option.get('label') or str(quality)
        if mode == 'playlist_all':
            self._notify_browser_toast(f"🚀 بدأ تنزيل كامل قائمة التشغيل ({q_label}) إلى مجلد: {folder_name}...", 'info')
        else:
            self._notify_browser_toast(f"🚀 بدأ التنزيل المباشر ({q_label}) إلى: {folder_name}...", 'info')

        start_t = time.time()
        last_item_idx = [0]

        def run_direct_dl():
            def progress_cb(p_data):
                if self._window:
                    try:
                        self._window.evaluate_js(f'updateProgress({json.dumps(p_data)})')
                    except Exception:
                        pass
                if mode == 'playlist_all':
                    p_idx = p_data.get('playlist_index')
                    p_cnt = p_data.get('playlist_count')
                    if p_idx and p_cnt and p_idx != last_item_idx[0]:
                        last_item_idx[0] = p_idx
                        it_title = p_data.get('item_title') or f"مقطع {p_idx}"
                        self._notify_browser_toast(f"📥 جاري تنزيل ({p_idx}/{p_cnt}): {it_title[:32]}...", 'info')

            def status_cb(msg):
                if self._window:
                    try:
                        self._window.evaluate_js(f'updateProgress({json.dumps({"status": "processing", "msg": msg})})')
                    except Exception:
                        pass

            try:
                if not self.downloader:
                    from downloader import MediaDownloader
                    self.downloader = MediaDownloader()

                browser_cookies = getattr(self, 'last_browser_cookies', 'none') or 'none'

                result = self.downloader.download(
                    url, option, self.save_dir,
                    progress_callback=progress_cb,
                    status_callback=status_cb,
                    browser_cookies=browser_cookies
                )

                downloaded_files = result.get('files') or []
                media_type = option.get('type') or 'video'
                media_title = option.get('media_title') or (downloaded_files[0].get('title') if downloaded_files else 'وسائط محملة')

                if media_type == 'audio':
                    for file_item in downloaded_files:
                        file_item['is_audio'] = True
                        filepath = file_item.get('filepath') or ''
                        if filepath:
                            prepared = self.prepare_media_playback(filepath)
                            file_item['playable_url'] = (
                                prepared.get('url')
                                if prepared.get('ok')
                                else self._register_media_file(filepath)
                            )
                            file_item['playback_ready'] = bool(prepared.get('ok'))
                            file_item['playback_transcoded'] = bool(prepared.get('transcoded'))
                            file_item['playback_error'] = prepared.get('error', '')

                for file_item in downloaded_files:
                    h_item = {
                        'title': file_item.get('title') or media_title,
                        'quality': option.get('label') or quality,
                        'type': media_type,
                        'filepath': file_item.get('filepath') or '',
                        'url': url,
                        'date': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                    }
                    self.add_history(h_item)

                if len(downloaded_files) > 1 or option.get('is_playlist'):
                    first_fp = downloaded_files[0].get('filepath') if downloaded_files else self.save_dir
                    self._notify_browser_toast(f"✅ تم اكتمال تنزيل كامل القائمة ({len(downloaded_files)} عنصر) بنجاح!", 'success', filepath=first_fp)
                else:
                    first_fp = downloaded_files[0].get('filepath') if downloaded_files else ''
                    first_name = Path(first_fp).name if first_fp else media_title
                    self._notify_browser_toast(f"✅ تم اكتمال تنزيل: {first_name} بنجاح!", 'success', filepath=first_fp)

                if self._window:
                    try:
                        payload = {
                            'status': 'complete',
                            'title': media_title,
                            'quality': option.get('label') or quality,
                            'filepath': result.get('filepath') or (downloaded_files[0]['filepath'] if downloaded_files else ''),
                            'files': downloaded_files,
                            'count': result.get('count', len(downloaded_files)),
                            'directory': result.get('directory') or self.save_dir,
                            'media_type': media_type,
                            'is_playlist': bool(result.get('is_playlist')),
                            'elapsed': round(time.time() - start_t, 1),
                        }
                        self._window.evaluate_js(f'updateProgress({json.dumps(payload)})')
                    except Exception as ex:
                        _log.debug(f"Complete evaluate_js: {ex}")

            except Exception as e:
                _log.error(f"Direct browser download failed: {e}")
                self._notify_browser_toast(f"❌ خطأ أثناء التنزيل: {str(e)[:70]}", 'error')

        threading.Thread(target=run_direct_dl, daemon=True).start()
        return {'success': True}

    def load_url_in_main(self, url, auto_playlist_select=False):
        """Send URL to main window input bar and fetch info."""
        if self._window:
            try:
                self._window.restore()
                self._window.show()
            except Exception:
                pass
            safe_url = json.dumps(str(url))
            safe_auto = json.dumps(bool(auto_playlist_select))
            self._window.evaluate_js(f"if (window.onBrowserSendUrl) window.onBrowserSendUrl({safe_url}, {safe_auto});")
        return {'success': True}

    def _async_download(self, url, option, browser_cookies):
        start_t = time.time()
        is_playlist = bool(option.get('is_playlist') or option.get('mixed_playlist'))
        playlist_session = None

        if is_playlist:
            existing_sess = self._load_playlist_session()
            if option.get('is_resumed_session') and existing_sess and existing_sess.get('url') == url:
                playlist_session = existing_sess
                playlist_session['status'] = 'in_progress'
                playlist_session['timestamp'] = time.time()
                self._save_playlist_session(playlist_session)
            else:
                p_items = list(option.get('playlist_items') or [])
                total_cnt = int(option.get('playlist_count') or len(p_items) or 1)
                if not p_items and total_cnt > 0:
                    p_items = list(range(1, total_cnt + 1))
                playlist_session = {
                    'url': url,
                    'title': option.get('media_title') or 'قائمة تشغيل',
                    'total_count': total_cnt,
                    'completed_count': 0,
                    'completed_indices': [],
                    'remaining_indices': p_items,
                    'option': option,
                    'status': 'in_progress',
                    'save_dir': self.save_dir,
                    'timestamp': time.time()
                }
                self._save_playlist_session(playlist_session)

        def on_playlist_item_complete(p_idx, item_title, file_path):
            if playlist_session and p_idx is not None:
                try:
                    idx = int(p_idx)
                    if idx not in playlist_session['completed_indices']:
                        playlist_session['completed_indices'].append(idx)
                    if idx in playlist_session['remaining_indices']:
                        playlist_session['remaining_indices'].remove(idx)
                    playlist_session['completed_count'] = len(playlist_session['completed_indices'])
                    playlist_session['remaining_count'] = len(playlist_session['remaining_indices'])
                    playlist_session['timestamp'] = time.time()
                    self._save_playlist_session(playlist_session)
                except Exception as ex:
                    _log.debug(f"Session item update exception: {ex}")

        def progress_callback(p_data):
            if playlist_session and p_data.get('playlist_count'):
                p_count = int(p_data['playlist_count'])
                if p_count > playlist_session.get('total_count', 0):
                    playlist_session['total_count'] = p_count
                    if not playlist_session.get('remaining_indices'):
                        playlist_session['remaining_indices'] = [
                            i for i in range(1, p_count + 1)
                            if i not in playlist_session.get('completed_indices', [])
                        ]
                    self._save_playlist_session(playlist_session)
            if self._window:
                try:
                    self._window.evaluate_js(f'updateProgress({json.dumps(p_data)})')
                except Exception as ex:
                    _log.debug(f"Progress evaluate_js error: {ex}")

        def status_callback(msg):
            if self._window:
                try:
                    payload = {'status': 'processing', 'msg': msg}
                    self._window.evaluate_js(f'updateProgress({json.dumps(payload)})')
                except Exception as ex:
                    _log.debug(f"Status evaluate_js error: {ex}")

        try:
            if not self.downloader:
                from downloader import MediaDownloader
                self.downloader = MediaDownloader()

            if option.get('mixed_playlist'):
                video_indices = option.get('playlist_video_items') or []
                audio_indices = option.get('playlist_audio_items') or []
                downloaded_files = []
                last_result = {}

                if video_indices:
                    v_opt = dict(option)
                    v_opt['type'] = 'video'
                    v_opt['playlist_items'] = video_indices
                    v_opt['playlist_count'] = len(video_indices)
                    v_opt['mixed_playlist'] = False
                    status_callback(f"🎬 جاري تنزيل {len(video_indices)} مقطع فيديو محدد من القائمة...")
                    res_v = self.downloader.download(
                        url, v_opt, self.save_dir,
                        progress_callback=progress_callback,
                        status_callback=status_callback,
                        browser_cookies=browser_cookies,
                        item_complete_callback=on_playlist_item_complete
                    )
                    downloaded_files.extend(res_v.get('files') or [])
                    last_result = res_v

                if audio_indices:
                    a_opt = dict(option)
                    a_opt['type'] = 'audio'
                    a_opt['ext'] = 'mp3'
                    a_opt['quality_tag'] = 'MP3'
                    a_opt['format_id'] = 'bestaudio/best'
                    a_opt['label'] = 'صوت MP3'
                    a_opt['playlist_items'] = audio_indices
                    a_opt['playlist_count'] = len(audio_indices)
                    a_opt['mixed_playlist'] = False
                    status_callback(f"🎵 جاري تنزيل {len(audio_indices)} مقطع صوتي MP3 محدد من القائمة...")
                    res_a = self.downloader.download(
                        url, a_opt, self.save_dir,
                        progress_callback=progress_callback,
                        status_callback=status_callback,
                        browser_cookies=browser_cookies,
                        item_complete_callback=on_playlist_item_complete
                    )
                    a_files = res_a.get('files') or []
                    for f in a_files:
                        f['is_audio'] = True
                    downloaded_files.extend(a_files)
                    last_result = res_a

                result = {
                    'files': downloaded_files,
                    'count': len(downloaded_files),
                    'directory': last_result.get('directory') or self.save_dir,
                    'filepath': downloaded_files[0].get('filepath') if downloaded_files else '',
                    'is_playlist': True,
                    'media_type': 'mixed'
                }
            else:
                result = self.downloader.download(
                    url, option, self.save_dir,
                    progress_callback=progress_callback,
                    status_callback=status_callback,
                    browser_cookies=browser_cookies,
                    item_complete_callback=on_playlist_item_complete
                )
            
            if is_playlist:
                self.discard_unfinished_playlist_session()
            
            elapsed = time.time() - start_t
            _log.info(f"Download complete: {result.get('count', 0)} file(s) ({elapsed:.1f}s)")

            media_title = option.get('media_title') or 'وسائط محمّلة'
            quality_label = option.get('label') or option.get('quality_tag') or 'جودة افتراضية'
            media_type = option.get('type') or 'video'
            downloaded_files = result.get('files') or []

            for file_item in downloaded_files:
                filepath = file_item.get('filepath') or ''
                is_audio_file = bool(file_item.get('is_audio')) or media_type == 'audio' or filepath.lower().endswith(('.mp3', '.m4a', '.wav', '.flac', '.opus'))
                if is_audio_file and filepath:
                    prepared = self.prepare_media_playback(filepath)
                    file_item['playable_url'] = (
                        prepared.get('url')
                        if prepared.get('ok')
                        else self._register_media_file(filepath)
                    )
                    file_item['playback_ready'] = bool(prepared.get('ok'))
                    file_item['playback_transcoded'] = bool(prepared.get('transcoded'))
                    file_item['playback_error'] = prepared.get('error', '')
                    file_item['is_audio'] = True

            for file_item in downloaded_files:
                filepath = file_item.get('filepath') or ''
                is_audio_file = bool(file_item.get('is_audio')) or media_type == 'audio' or filepath.lower().endswith(('.mp3', '.m4a', '.wav', '.flac', '.opus'))
                self.add_history({
                    'title': file_item.get('title') or media_title,
                    'quality': 'صوت MP3' if is_audio_file else quality_label,
                    'type': 'audio' if is_audio_file else 'video',
                    'filepath': filepath,
                    'url': url,
                    'date': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                })
            
            if self._window:
                try:
                    payload = {
                        'status': 'complete',
                        'filepath': result.get('filepath') or '',
                        'files': downloaded_files,
                        'count': result.get('count', len(downloaded_files)),
                        'directory': result.get('directory') or self.save_dir,
                        'media_type': result.get('media_type') or media_type,
                        'is_playlist': bool(result.get('is_playlist')),
                        'elapsed': round(elapsed, 1),
                    }
                    self._window.evaluate_js(f'updateProgress({json.dumps(payload)})')
                except Exception as ex:
                    _log.warning(f"Complete evaluate_js error: {ex}")
        except Exception as e:
            elapsed = time.time() - start_t
            try:
                from downloader import clean_error_message
                error_message = clean_error_message(e)
            except Exception:
                error_message = str(e)
            _log.error(f"Download failed after {elapsed:.1f}s: {error_message}")
            if self._window:
                try:
                    payload = {
                        'status': 'cancelled' if 'إلغاء' in error_message else 'error',
                        'error': error_message,
                    }
                    self._window.evaluate_js(f'updateProgress({json.dumps(payload)})')
                except Exception as ex:
                    _log.warning(f"Error evaluate_js error: {ex}")
        finally:
            self._download_thread = None

    def resize_window(self, width, height):
        if self._window:
            try:
                self._window.resize(int(width), int(height))
            except Exception as e:
                _log.debug(f"Window resize failed: {e}")

    # ================================================================
    # Ultra: App Update & Installer Launch
    # ================================================================
    def check_app_update(self):
        try:
            import urllib.request
            req = urllib.request.Request(
                f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                headers={
                    'User-Agent': f'SDN-Downloader-App/{CURRENT_APP_VERSION}',
                    'Accept': 'application/vnd.github+json',
                }
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                tag_name = data.get('tag_name', '').lstrip('v')
                body = data.get('body', '')
                assets = data.get('assets', [])
                release_html_url = data.get('html_url', f"https://github.com/{GITHUB_REPO}/releases/latest")
                portable = _release_asset_details(assets, WINDOWS_PORTABLE_ASSET)
                installer = _release_asset_details(assets, WINDOWS_INSTALLER_ASSET)

                if tag_name and _version_key(tag_name) > _version_key(CURRENT_APP_VERSION):
                    preferred = portable or installer or {}
                    return {
                        'has_update': True,
                        'latest_version': tag_name,
                        'current_version': CURRENT_APP_VERSION,
                        'download_url': preferred.get('url') or release_html_url,
                        'html_url': release_html_url,
                        'sha256': preferred.get('sha256'),
                        'size': preferred.get('size'),
                        'update_kind': 'portable' if portable else 'installer',
                        'portable_url': portable.get('url') if portable else None,
                        'portable_sha256': portable.get('sha256') if portable else None,
                        'portable_size': portable.get('size') if portable else None,
                        'installer_url': installer.get('url') if installer else None,
                        'installer_sha256': installer.get('sha256') if installer else None,
                        'installer_size': installer.get('size') if installer else None,
                        'notes': body or 'تحديث جديد لتحسين الأداء وحل المشاكل.'
                    }
        except Exception as e:
            _log.debug(f"Update check failed (offline?): {e}")
        return {'has_update': False, 'current_version': CURRENT_APP_VERSION}

    def _current_application_path(self):
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).resolve()
        return Path(__file__).resolve()

    def _can_replace_current_executable(self):
        """Check whether the packaged app can safely replace itself in place."""
        if not getattr(sys, 'frozen', False):
            return False
        target = self._current_application_path()
        if target.suffix.lower() != '.exe' or not target.is_file():
            return False
        try:
            with tempfile.NamedTemporaryFile(
                mode='wb',
                prefix='.sdn-update-probe-',
                suffix='.tmp',
                dir=str(target.parent),
                delete=True,
            ) as probe:
                probe.write(b'SDN')
                probe.flush()
            return True
        except OSError as exc:
            _log.info(f"Direct in-place update unavailable for {target.parent}: {exc}")
            return False

    def _is_installed_instance(self):
        """Check whether the running app was installed via installer or is a standalone portable binary."""
        if not getattr(sys, 'frozen', False):
            return False
        target = self._current_application_path()
        parent = target.parent
        if (
            (parent / 'Uninstall.exe').is_file()
            or (parent / 'unins000.exe').is_file()
            or (parent / '_internal').is_dir()
            or (parent / 'version.json').is_file()
            or target.name.lower() == 'sdn_downloader.exe'
        ):
            return True
        return False

    def _select_update_package(self, update_info):
        """Prefer silent installer for installed app directories, and zero-window portable replacement for standalone exes."""
        is_installed = self._is_installed_instance()
        if is_installed and update_info.get('installer_url'):
            return {
                'kind': 'installer',
                'url': update_info.get('installer_url'),
                'sha256': update_info.get('installer_sha256'),
                'size': update_info.get('installer_size'),
            }
        if self._can_replace_current_executable() and update_info.get('portable_url'):
            return {
                'kind': 'portable',
                'url': update_info.get('portable_url'),
                'sha256': update_info.get('portable_sha256'),
                'size': update_info.get('portable_size'),
            }
        if update_info.get('installer_url'):
            return {
                'kind': 'installer',
                'url': update_info.get('installer_url'),
                'sha256': update_info.get('installer_sha256'),
                'size': update_info.get('installer_size'),
            }
        return None

    def apply_app_update(self, download_url=None):
        _log.info(f"apply_app_update requested with url: {download_url}")
        if getattr(self, '_update_download_active', False):
            return {'success': True, 'status': 'already_downloading'}

        update_info = self.latest_update_info
        if not update_info or not update_info.get('has_update'):
            update_info = self.check_app_update()
            if update_info.get('has_update'):
                self.latest_update_info = update_info

        if not update_info or not update_info.get('has_update'):
            return {'success': False, 'error': 'لا يوجد تحديث جديد متاح'}

        package = self._select_update_package(update_info)
        if not package or not package.get('url'):
            return {'success': False, 'error': 'لا توجد حزمة تحديث مناسبة لـ Windows'}

        target_url = str(package['url'])
        expected_sha256 = package.get('sha256')
        expected_size = int(package.get('size') or 0)
        package_kind = package['kind']

        try:
            parsed = urllib.parse.urlsplit(target_url)
            if (
                parsed.scheme != 'https'
                or parsed.hostname not in {'github.com', 'www.github.com'}
                or not target_url.lower().endswith('.exe')
            ):
                return {'success': False, 'error': 'تم رفض رابط تحديث غير موثوق'}
        except Exception:
            return {'success': False, 'error': 'رابط التحديث غير صالح'}

        if not expected_sha256:
            return {'success': False, 'error': 'تعذر التحقق من بصمة التحديث الآمنة'}

        self._update_download_active = True
        self.pending_update_path = None
        self.pending_update_kind = None
        self.pending_update_sha256 = None
        self.pending_update_size = None

        def _do_update():
            try:
                import urllib.request

                temp_dir = tempfile.gettempdir()
                package_label = 'Portable' if package_kind == 'portable' else 'Setup'
                update_filename = f"SDN_Update_{package_label}_{int(time.time())}.exe"
                update_path = os.path.join(temp_dir, update_filename)

                _log.info(f"Downloading update from: {target_url}")
                req = urllib.request.Request(
                    target_url,
                    headers={'User-Agent': f'SDN-Downloader-App/{CURRENT_APP_VERSION}'},
                )
                digest = hashlib.sha256()
                with urllib.request.urlopen(req, timeout=180) as resp, open(update_path, 'wb') as out_f:
                    final_host = (urllib.parse.urlsplit(resp.geturl()).hostname or '').lower()
                    if (
                        final_host not in TRUSTED_UPDATE_HOSTS
                        and not final_host.endswith('.githubusercontent.com')
                        and not (final_host.endswith('.amazonaws.com') and 'github' in final_host)
                    ):
                        raise RuntimeError('تم رفض مصدر تحديث غير موثوق.')

                    total_size = int(resp.headers.get('content-length', 0) or 0)
                    downloaded = 0
                    chunk_size = 512 * 1024
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        out_f.write(chunk)
                        digest.update(chunk)
                        downloaded += len(chunk)
                        pct = min(int((downloaded / total_size) * 100), 99) if total_size > 0 else 50
                        if self._window:
                            payload = {
                                'status': 'downloading',
                                'pct': pct,
                                'downloaded': downloaded,
                                'total': total_size,
                            }
                            self._window.evaluate_js(
                                f'if (typeof onUpdateProgress === "function") '
                                f'onUpdateProgress({json.dumps(payload)});'
                            )

                if os.path.getsize(update_path) < 1024 * 1024:
                    raise RuntimeError('ملف التحديث أصغر من الحجم المتوقع.')
                if expected_size and downloaded != expected_size:
                    raise RuntimeError('حجم ملف التحديث لا يطابق الإصدار المنشور.')
                with open(update_path, 'rb') as update_file:
                    if update_file.read(2) != b'MZ':
                        raise RuntimeError('ملف التحديث ليس ملف Windows صالحًا.')
                if digest.hexdigest().lower() != str(expected_sha256).lower():
                    raise RuntimeError('فشل التحقق من بصمة ملف التحديث.')

                self.pending_update_path = update_path
                self.pending_update_kind = package_kind
                self.pending_update_sha256 = expected_sha256.lower()
                self.pending_update_size = downloaded
                _log.info(f"Verified {package_kind} update ready: {update_path}")
                clean_path = update_path.replace('\\', '/')
                if self._window:
                    payload = {
                        'status': 'complete',
                        'update_path': clean_path,
                        'setup_path': clean_path,
                        'update_kind': package_kind,
                    }
                    self._window.evaluate_js(f'if (typeof onUpdateProgress === "function") onUpdateProgress({json.dumps(payload)});')

            except Exception as e:
                _log.error(f"Update download failed: {e}")
                try:
                    if 'update_path' in locals() and os.path.exists(update_path):
                        os.remove(update_path)
                except Exception:
                    pass
                if self._window:
                    payload = {'status': 'error', 'error': f'فشل التنزيل التلقائي: {str(e)}'}
                    self._window.evaluate_js(f'if (typeof onUpdateProgress === "function") onUpdateProgress({json.dumps(payload)});')
            finally:
                self._update_download_active = False

        threading.Thread(target=_do_update, daemon=True, name="UpdateDownloader").start()
        return {'success': True, 'update_kind': package_kind}

    def _resolve_pending_update(self, update_path=None):
        pending = getattr(self, 'pending_update_path', None)
        if not pending:
            raise RuntimeError('ملف التحديث غير موجود')

        pending_path = Path(pending).resolve(strict=True)
        requested = str(update_path or '').strip()
        if requested and requested != 'undefined':
            requested_path = Path(requested).resolve(strict=True)
            if os.path.normcase(str(requested_path)) != os.path.normcase(str(pending_path)):
                raise RuntimeError('تم رفض مسار تحديث غير متوقع')

        if pending_path.stat().st_size < 1024 * 1024:
            raise RuntimeError('ملف التحديث غير مكتمل')
        expected_size = int(getattr(self, 'pending_update_size', 0) or 0)
        if expected_size and pending_path.stat().st_size != expected_size:
            raise RuntimeError('تغيّر حجم ملف التحديث بعد تنزيله')

        digest = hashlib.sha256()
        with pending_path.open('rb') as update_file:
            first_chunk = update_file.read(1024 * 1024)
            if not first_chunk.startswith(b'MZ'):
                raise RuntimeError('ملف التحديث غير صالح')
            digest.update(first_chunk)
            while True:
                chunk = update_file.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)

        expected_sha256 = str(getattr(self, 'pending_update_sha256', '') or '').lower()
        if not expected_sha256 or digest.hexdigest().lower() != expected_sha256:
            raise RuntimeError('تغيّرت بصمة ملف التحديث بعد تنزيله')
        return pending_path

    def _launch_portable_updater(self, update_path):
        if not getattr(sys, 'frozen', False):
            raise RuntimeError('التحديث الصامت يعمل من النسخة المبنية فقط')

        target_path = self._current_application_path()
        if not self._can_replace_current_executable():
            raise RuntimeError('مجلد البرنامج لا يسمح بالتحديث المباشر')

        log_dir = Path.home() / '.sdn_logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / 'sdn_update.log'
        backup_path = target_path.with_name(target_path.name + '.old')
        script_path = Path(tempfile.gettempdir()) / f"SDN_SilentUpdater_{os.getpid()}_{int(time.time())}.ps1"
        script_path.write_text(SILENT_PORTABLE_UPDATER_SCRIPT, encoding='utf-8-sig')

        powershell = (
            shutil.which('powershell.exe')
            or os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe')
        )
        if not os.path.isfile(powershell):
            script_path.unlink(missing_ok=True)
            raise RuntimeError('تعذر العثور على أداة التحديث الصامت في Windows')

        command = [
            powershell,
            '-NoLogo',
            '-NoProfile',
            '-NonInteractive',
            '-ExecutionPolicy', 'Bypass',
            '-WindowStyle', 'Hidden',
            '-File', str(script_path),
            '-ParentPid', str(os.getpid()),
            '-UpdatePath', str(update_path),
            '-TargetPath', str(target_path),
            '-BackupPath', str(backup_path),
            '-LogPath', str(log_path),
            '-ScriptPath', str(script_path),
        ]
        subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
        )
        _log.info(f"Silent portable updater launched for: {target_path}")

    def _launch_silent_installer(self, update_path):
        target_dir = self._current_application_path().parent
        installer_log = Path(tempfile.gettempdir()) / 'SDN_Silent_Installer.log'
        command = [
            str(update_path),
            '/VERYSILENT',
            '/SUPPRESSMSGBOXES',
            '/NORESTART',
            '/SP-',
            '/CLOSEAPPLICATIONS',
            '/RESTARTAPPLICATIONS',
            '/LANG=arabic',
            f'/DIR={target_dir}',
            f'/LOG={installer_log}',
        ]
        subprocess.Popen(
            command,
            cwd=str(target_dir),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
        )
        _log.info(f"Silent installer launched for directory: {target_dir}")

    def restart_and_apply_update(self, update_path=None):
        if getattr(self, '_update_restart_started', False):
            return {'success': True, 'status': 'already_started'}

        try:
            verified_path = self._resolve_pending_update(update_path)
            update_kind = getattr(self, 'pending_update_kind', None)
            if update_kind == 'portable':
                self._launch_portable_updater(verified_path)
            elif update_kind == 'installer':
                self._launch_silent_installer(verified_path)
            else:
                raise RuntimeError('نوع حزمة التحديث غير معروف')

            self._update_restart_started = True
            _log.info(f"Closing SDN to apply {update_kind} update in the background")
            time.sleep(0.35)
            os._exit(0)
            return {'success': True}
        except Exception as e:
            self._update_restart_started = False
            _log.error(f"Silent update launch failed: {e}")
            return {'success': False, 'error': str(e)}

    def launch_installer(self, setup_path=None):
        """Compatibility alias for older bundled UI code."""
        return self.restart_and_apply_update(setup_path)


# ================================================================
# ULTRA MAIN - Optimized startup sequence
# ================================================================
_single_instance_mutex = None


def _ensure_single_instance() -> bool:
    """Allow only one running copy; focus the existing window instead."""
    global _single_instance_mutex
    if sys.platform != 'win32':
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        handle = kernel32.CreateMutexW(None, False, "SDN_Downloader_Ultra_SingleInstance")
        if not handle:
            return True
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            user32 = ctypes.windll.user32
            hwnd = user32.FindWindowW(None, "SDN")
            if hwnd:
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
            _log.info("Another SDN instance is already running; focusing it and exiting")
            return False
        _single_instance_mutex = handle
        return True
    except Exception as e:
        _log.debug(f"Single instance check skipped: {e}")
        return True


def main():
    _log.info(f"🚀 SDN v{CURRENT_APP_VERSION} starting...")

    if not _ensure_single_instance():
        return

    api = DownloaderBridgeAPI()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_file = os.path.join(base_dir, 'ui', 'index.html')
    
    if not os.path.exists(html_file):
        # Fallback: look in www/ for Capacitor
        html_file = os.path.join(base_dir, 'www', 'index.html')
        _log.warning(f"ui/index.html not found, falling back to: {html_file}")

    _log.info(f"Creating window with UI: {html_file}")
    
    # Wait briefly for preloader to finish (non-blocking with timeout)
    _preload_done.wait(timeout=2.0)
    
    window = webview.create_window(
        title='SDN',
        url=html_file,
        width=820,
        height=640,
        resizable=True,
        background_color='#07090e',
        js_api=api
    )
    api.set_window(window)
    
    user_data_dir = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'SDN', 'WebView2_Data')
    os.makedirs(user_data_dir, exist_ok=True)
    os.environ['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = '--enable-gpu-rasterization --enable-zero-copy --ignore-gpu-blocklist'
    _log.info(f"App ready in {time.time() - api._startup_time:.2f}s - starting WebView with persistent storage: {user_data_dir}")
    webview.start(debug=False, private_mode=False, storage_path=user_data_dir)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
