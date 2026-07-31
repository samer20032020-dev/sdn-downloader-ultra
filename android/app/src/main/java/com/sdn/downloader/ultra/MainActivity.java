package com.sdn.downloader.ultra;

import android.app.Activity;
import android.app.DownloadManager;
import android.content.Context;
import android.content.Intent;
import android.media.MediaScannerConnection;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.util.Log;
import android.webkit.JavascriptInterface;
import android.widget.Toast;

import com.getcapacitor.BridgeActivity;
import com.yausername.ffmpeg.FFmpeg;
import com.yausername.youtubedl_android.YoutubeDL;
import com.yausername.youtubedl_android.YoutubeDLException;
import com.yausername.youtubedl_android.YoutubeDLRequest;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import kotlin.Unit;
import kotlin.jvm.functions.Function3;

public class MainActivity extends BridgeActivity {
    private static final String TAG = "SDN";
    private static final int REQUEST_CODE_PICK_FOLDER = 9999;
    private static final long YTDLP_UPDATE_INTERVAL_MS = 24L * 60L * 60L * 1000L;
    private static final Pattern URL_PATTERN = Pattern.compile("https?://\\S+");

    private final ExecutorService mediaExecutor = Executors.newSingleThreadExecutor();
    private final AtomicBoolean mediaBusy = new AtomicBoolean(false);
    private final AtomicBoolean cancellationRequested = new AtomicBoolean(false);
    private volatile boolean mediaEngineReady = false;
    private volatile String activeProcessId = "";
    private String pendingSharedUrl = null;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        handleIntent(getIntent());
        setupAndroidBridge();
        mediaExecutor.execute(this::initializeMediaEngine);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleIntent(intent);
    }

    @Override
    public void onResume() {
        super.onResume();
        setupAndroidBridge();
    }

    @Override
    public void onDestroy() {
        try {
            if (!activeProcessId.isEmpty()) {
                YoutubeDL.getInstance().destroyProcessById(activeProcessId);
            }
        } catch (Exception ignored) {
        }
        mediaExecutor.shutdownNow();
        super.onDestroy();
    }

    private synchronized boolean initializeMediaEngine() {
        if (mediaEngineReady) return true;
        try {
            YoutubeDL.getInstance().init(this);
            FFmpeg.getInstance().init(this);
            mediaEngineReady = true;
            maybeUpdateYoutubeDL();
            Log.i(TAG, "yt-dlp and FFmpeg initialized");
            return true;
        } catch (YoutubeDLException exception) {
            Log.e(TAG, "Failed to initialize Android media engine", exception);
            return false;
        }
    }

    private void maybeUpdateYoutubeDL() {
        try {
            long lastUpdate = getPreferences(Context.MODE_PRIVATE).getLong("yt_dlp_checked_at", 0);
            long now = System.currentTimeMillis();
            if (now - lastUpdate < YTDLP_UPDATE_INTERVAL_MS) return;
            getPreferences(Context.MODE_PRIVATE).edit().putLong("yt_dlp_checked_at", now).apply();
            YoutubeDL.getInstance().updateYoutubeDL(this, YoutubeDL.UpdateChannel._STABLE);
            Log.i(TAG, "yt-dlp update check completed");
        } catch (Exception exception) {
            Log.w(TAG, "yt-dlp update check skipped", exception);
        }
    }

    private void setupAndroidBridge() {
        runOnUiThread(() -> {
            if (bridge != null && bridge.getWebView() != null) {
                bridge.getWebView().getSettings().setAllowFileAccess(true);
                bridge.getWebView().getSettings().setAllowContentAccess(true);
                bridge.getWebView().addJavascriptInterface(new AndroidBridge(), "androidInterface");
            }
        });
    }

    public class AndroidBridge {
        @JavascriptInterface
        public void pickFolder() {
            try {
                Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
                intent.addFlags(
                    Intent.FLAG_GRANT_READ_URI_PERMISSION
                        | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                        | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION
                );
                startActivityForResult(intent, REQUEST_CODE_PICK_FOLDER);
            } catch (Exception exception) {
                Log.w(TAG, "Folder picker failed", exception);
            }
        }

        @JavascriptInterface
        public String getSharedUrl() {
            String url = pendingSharedUrl;
            pendingSharedUrl = null;
            return url != null ? url : "";
        }

        @JavascriptInterface
        public boolean fetchMediaInfo(String url) {
            if (!isValidWebUrl(url) || mediaBusy.get()) return false;
            mediaExecutor.execute(() -> fetchMediaInfoInternal(url.trim()));
            return true;
        }

        @JavascriptInterface
        public boolean downloadMedia(String url, String optionJson) {
            if (!isValidWebUrl(url) || !mediaBusy.compareAndSet(false, true)) return false;
            cancellationRequested.set(false);
            mediaExecutor.execute(() -> {
                try {
                    downloadMediaInternal(url.trim(), optionJson);
                } finally {
                    mediaBusy.set(false);
                    activeProcessId = "";
                }
            });
            return true;
        }

        @JavascriptInterface
        public boolean cancelDownload() {
            try {
                if (!activeProcessId.isEmpty()) {
                    cancellationRequested.set(true);
                    YoutubeDL.getInstance().destroyProcessById(activeProcessId);
                    return true;
                }
            } catch (Exception exception) {
                Log.w(TAG, "Cancel failed", exception);
            }
            return false;
        }

        @JavascriptInterface
        public String listAudioFiles() {
            return buildAudioLibraryJson().toString();
        }

        @JavascriptInterface
        public boolean deleteFile(String path) {
            try {
                if (path == null || path.trim().isEmpty()) return false;
                File file = new File(path);
                boolean deleted = file.isFile() && file.delete();
                if (deleted) {
                    MediaScannerConnection.scanFile(
                        MainActivity.this,
                        new String[]{file.getAbsolutePath()},
                        null,
                        null
                    );
                }
                return deleted;
            } catch (Exception exception) {
                return false;
            }
        }

        @JavascriptInterface
        public void openDownloads() {
            try {
                Intent intent = new Intent(Intent.ACTION_VIEW);
                intent.setDataAndType(
                    Uri.parse("content://com.android.externalstorage.documents/root/primary"),
                    "resource/folder"
                );
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(intent);
            } catch (Exception exception) {
                Intent fallback = new Intent(DownloadManager.ACTION_VIEW_DOWNLOADS);
                startActivity(fallback);
            }
        }

        @JavascriptInterface
        public boolean downloadUpdate(String url) {
            return downloadWithSystemManager(
                url,
                "SDN_Downloader_Ultra_Update_" + System.currentTimeMillis() + ".apk",
                "application/vnd.android.package-archive",
                Environment.DIRECTORY_DOWNLOADS
            );
        }

        @JavascriptInterface
        public boolean downloadFile(String url, String fileName, String mimeType, String subDir) {
            String destination = Environment.DIRECTORY_DOWNLOADS;
            if ("Movies".equalsIgnoreCase(subDir)) destination = Environment.DIRECTORY_MOVIES;
            else if ("Music".equalsIgnoreCase(subDir)) destination = Environment.DIRECTORY_MUSIC;
            else if ("DCIM".equalsIgnoreCase(subDir)) destination = Environment.DIRECTORY_DCIM;
            return downloadWithSystemManager(url, fileName, mimeType, destination);
        }
    }

    private boolean downloadWithSystemManager(String url, String fileName, String mimeType, String destination) {
        try {
            if (!isValidWebUrl(url)) return false;
            String safeName = sanitizeFileName(
                fileName == null || fileName.trim().isEmpty() ? "SDN_Media" : fileName
            );
            DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
            request.setTitle(safeName);
            request.setDescription("تحميل عبر SDN Downloader Ultra");
            request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            request.setDestinationInExternalPublicDir(destination, safeName);
            if (mimeType != null && !mimeType.isEmpty()) request.setMimeType(mimeType);

            DownloadManager manager = (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);
            if (manager == null) return false;
            manager.enqueue(request);
            runOnUiThread(
                () -> Toast.makeText(
                    MainActivity.this,
                    "⚡ بدأ التحميل في الخلفية: " + safeName,
                    Toast.LENGTH_SHORT
                ).show()
            );
            return true;
        } catch (Exception exception) {
            Log.e(TAG, "System download failed", exception);
            return false;
        }
    }

    private void fetchMediaInfoInternal(String url) {
        JSONObject response = new JSONObject();
        try {
            if (!initializeMediaEngine()) throw new Exception("تعذر تهيئة محرك الوسائط.");
            YoutubeDLRequest request = new YoutubeDLRequest(url);
            request.addOption("--dump-single-json");
            request.addOption("--flat-playlist");
            request.addOption("--skip-download");
            request.addOption("--no-warnings");

            String output = YoutubeDL.getInstance().execute(request).getOut();
            String jsonText = extractJsonObject(output);
            if (jsonText.isEmpty()) throw new Exception("لم تُرجع المنصة معلومات قابلة للقراءة.");
            response.put("data", new JSONObject(jsonText));
            response.put("source_url", url);
        } catch (Exception exception) {
            Log.e(TAG, "Android media info failed", exception);
            try {
                response.put("error", cleanAndroidError(exception));
                response.put("source_url", url);
            } catch (Exception ignored) {
            }
        }
        dispatchJsonStringCallback("onAndroidMediaInfo", response);
    }

    private void downloadMediaInternal(String url, String optionJson) {
        long startedAt = System.currentTimeMillis();
        try {
            if (!initializeMediaEngine()) throw new Exception("تعذر تهيئة محرك الوسائط.");
            JSONObject option = new JSONObject(optionJson == null ? "{}" : optionJson);
            boolean isAudio = "audio".equals(option.optString("type"));
            boolean isPlaylist = option.optBoolean("is_playlist", false);
            String extension = option.optString("ext", isAudio ? "mp3" : "mp4").toLowerCase(Locale.ROOT);
            String qualityTag = sanitizeFileName(
                option.optString("quality_tag", option.optString("quality", isAudio ? "Audio" : "Video"))
            );
            String runToken = String.valueOf(startedAt);

            File downloadRoot = new File(
                Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS),
                "SDN Downloader"
            );
            if (!downloadRoot.exists() && !downloadRoot.mkdirs()) {
                throw new Exception("تعذر إنشاء مجلد التنزيل.");
            }

            YoutubeDLRequest request = new YoutubeDLRequest(url);
            request.addOption("--no-mtime");
            request.addOption("--continue");
            request.addOption("--retries", 10);
            request.addOption("--fragment-retries", 10);
            request.addOption("--concurrent-fragments", 4);
            request.addOption("--no-overwrites");
            request.addOption("--windows-filenames");

            String format = option.optString("format_id");
            if (format.isEmpty()) format = fallbackFormat(option, isAudio);
            request.addOption("-f", format);

            if (isAudio) {
                request.addOption("--extract-audio");
                request.addOption("--audio-format", extension);
                if ("mp3".equals(extension)) {
                    request.addOption("--audio-quality", option.optString("quality", "320") + "K");
                }
                request.addOption("--add-metadata");
            } else {
                request.addOption("--merge-output-format", "mp4");
                request.addOption("--add-metadata");
            }

            JSONArray selectedItems = option.optJSONArray("playlist_items");
            if (isPlaylist) {
                request.addOption("--ignore-errors");
                if (selectedItems != null && selectedItems.length() > 0) {
                    List<String> indices = new ArrayList<>();
                    for (int i = 0; i < selectedItems.length(); i++) {
                        int index = selectedItems.optInt(i, 0);
                        if (index > 0) indices.add(String.valueOf(index));
                    }
                    if (!indices.isEmpty()) request.addOption("--playlist-items", String.join(",", indices));
                }
            } else {
                request.addOption("--no-playlist");
            }

            String outputTemplate;
            if (isPlaylist) {
                outputTemplate = new File(
                    downloadRoot,
                    "%(playlist_title|Playlist).120B/%(playlist_index)03d - %(title).150B [%(id)s] ["
                        + qualityTag + "] [" + runToken + "].%(ext)s"
                ).getAbsolutePath();
            } else {
                outputTemplate = new File(
                    downloadRoot,
                    "%(title).170B [%(id)s] [" + qualityTag + "] [" + runToken + "].%(ext)s"
                ).getAbsolutePath();
            }
            request.addOption("-o", outputTemplate);

            activeProcessId = "sdn-" + runToken;
            Function3<Float, Long, String, Unit> callback = (progress, eta, line) -> {
                JSONObject extra = new JSONObject();
                try {
                    extra.put("eta_str", eta != null ? eta + " ثانية" : "");
                    extra.put("speed_str", line == null ? "" : line);
                } catch (Exception ignored) {
                }
                sendProgress("downloading", progress == null ? 0 : progress, "جاري التنزيل", extra, 0);
                return Unit.INSTANCE;
            };

            YoutubeDL.getInstance().execute(request, activeProcessId, callback);
            List<File> outputFiles = findRunFiles(downloadRoot, runToken, startedAt);
            if (outputFiles.isEmpty()) throw new Exception("اكتمل الأمر لكن لم يتم العثور على الملف النهائي.");

            JSONObject completed = new JSONObject();
            completed.put("status", "complete");
            completed.put("count", outputFiles.size());
            completed.put("is_playlist", isPlaylist);
            completed.put("media_type", isAudio ? "audio" : "video");
            completed.put("directory", outputFiles.get(0).getParent());
            completed.put("filepath", outputFiles.get(0).getAbsolutePath());
            completed.put("elapsed", Math.round((System.currentTimeMillis() - startedAt) / 100.0) / 10.0);
            JSONArray filesJson = new JSONArray();
            for (File file : outputFiles) {
                JSONObject fileJson = new JSONObject();
                fileJson.put("filepath", file.getAbsolutePath());
                fileJson.put("title", stripExtension(file.getName()));
                if (isAudio) fileJson.put("playable_url", "");
                filesJson.put(fileJson);
            }
            completed.put("files", filesJson);
            dispatchJsonObjectCallback("updateProgress", completed);

            MediaScannerConnection.scanFile(
                this,
                outputFiles.stream().map(File::getAbsolutePath).toArray(String[]::new),
                null,
                null
            );
        } catch (Exception exception) {
            Log.e(TAG, "Android yt-dlp download failed", exception);
            if (cancellationRequested.get()) {
                sendProgress("cancelled", 0, "تم إلغاء التنزيل", null, 0);
            } else {
                sendProgress("error", 0, cleanAndroidError(exception), null, 0);
            }
        }
    }

    private String fallbackFormat(JSONObject option, boolean isAudio) {
        if (isAudio) return "bestaudio/best";
        int height = option.optInt("quality", 0);
        String filter = height > 0 ? "[height<=" + height + "]" : "";
        return "bestvideo" + filter + "[ext=mp4]+bestaudio[ext=m4a]/bestvideo"
            + filter + "+bestaudio/best" + filter + "/best";
    }

    private List<File> findRunFiles(File root, String runToken, long startedAt) {
        List<File> result = new ArrayList<>();
        collectRunFiles(root, runToken, startedAt, result);
        result.sort(Comparator.comparing(File::getAbsolutePath));
        return result;
    }

    private void collectRunFiles(File directory, String runToken, long startedAt, List<File> result) {
        File[] children = directory.listFiles();
        if (children == null) return;
        for (File child : children) {
            if (child.isDirectory()) {
                collectRunFiles(child, runToken, startedAt, result);
            } else if (
                child.getName().contains(runToken)
                    && child.lastModified() >= startedAt - 5000
                    && isMediaFile(child)
            ) {
                result.add(child);
            }
        }
    }

    private JSONObject buildAudioLibraryJson() {
        JSONObject result = new JSONObject();
        try {
            List<File> files = new ArrayList<>();
            File downloads = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
            File music = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MUSIC);
            collectAudioFiles(downloads, files);
            if (!music.equals(downloads)) collectAudioFiles(music, files);
            files.sort((left, right) -> Long.compare(right.lastModified(), left.lastModified()));

            JSONArray tracks = new JSONArray();
            int maximum = Math.min(files.size(), 2000);
            for (int index = 0; index < maximum; index++) {
                File file = files.get(index);
                JSONObject track = new JSONObject();
                track.put("title", stripExtension(file.getName()));
                track.put("uploader", file.getParentFile() != null ? file.getParentFile().getName() : "الجهاز");
                track.put("url", file.getAbsolutePath());
                track.put("filepath", file.getAbsolutePath());
                track.put("format", extensionOf(file.getName()).toUpperCase(Locale.ROOT));
                track.put("size", file.length());
                track.put("thumbnail", "");
                tracks.put(track);
            }
            result.put("tracks", tracks);
            result.put("folder", downloads.getAbsolutePath());
        } catch (Exception exception) {
            try {
                result.put("tracks", new JSONArray());
                result.put("error", exception.getLocalizedMessage());
            } catch (Exception ignored) {
            }
        }
        return result;
    }

    private void collectAudioFiles(File directory, List<File> files) {
        if (directory == null || !directory.isDirectory()) return;
        File[] children = directory.listFiles();
        if (children == null) return;
        for (File child : children) {
            if (child.isDirectory()) collectAudioFiles(child, files);
            else if (isAudioFile(child)) files.add(child);
        }
    }

    private boolean isAudioFile(File file) {
        String extension = extensionOf(file.getName()).toLowerCase(Locale.ROOT);
        return extension.matches("mp3|m4a|aac|flac|ogg|opus|wav|wma");
    }

    private boolean isMediaFile(File file) {
        String extension = extensionOf(file.getName()).toLowerCase(Locale.ROOT);
        return extension.matches("mp4|mkv|webm|mov|avi|mp3|m4a|aac|flac|ogg|opus|wav|wma");
    }

    private void sendProgress(
        String status,
        float percent,
        String message,
        JSONObject extra,
        int ignored
    ) {
        try {
            JSONObject payload = extra != null ? extra : new JSONObject();
            payload.put("status", status);
            payload.put("percent", percent);
            if ("error".equals(status) || "cancelled".equals(status)) payload.put("error", message);
            else if (message != null) payload.put("msg", message);
            dispatchJsonObjectCallback("updateProgress", payload);
        } catch (Exception ignoredException) {
        }
    }

    private void dispatchJsonObjectCallback(String functionName, JSONObject payload) {
        runOnUiThread(() -> {
            if (bridge == null || bridge.getWebView() == null) return;
            String script = "if (typeof window." + functionName + " === 'function') { window."
                + functionName + "(" + payload + "); }";
            bridge.getWebView().evaluateJavascript(script, null);
        });
    }

    private void dispatchJsonStringCallback(String functionName, JSONObject payload) {
        runOnUiThread(() -> {
            if (bridge == null || bridge.getWebView() == null) return;
            String script = "if (typeof window." + functionName + " === 'function') { window."
                + functionName + "(" + JSONObject.quote(payload.toString()) + "); }";
            bridge.getWebView().evaluateJavascript(script, null);
        });
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQUEST_CODE_PICK_FOLDER || resultCode != Activity.RESULT_OK || data == null) {
            return;
        }
        Uri treeUri = data.getData();
        if (treeUri == null) return;
        try {
            getContentResolver().takePersistableUriPermission(
                treeUri,
                Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
            );
        } catch (Exception ignored) {
        }
        String path = treeUri.getLastPathSegment();
        if (path != null && path.contains(":")) path = path.substring(path.indexOf(":") + 1);
        sendFolderPathToWebView(path != null && !path.isEmpty() ? path : treeUri.getPath());
    }

    private void sendFolderPathToWebView(String folderPath) {
        JSONObject payload = new JSONObject();
        try {
            payload.put("path", folderPath == null ? "" : folderPath);
        } catch (Exception ignored) {
        }
        runOnUiThread(() -> {
            if (bridge == null || bridge.getWebView() == null) return;
            String script = "if (window.handleSelectedFolder) { window.handleSelectedFolder("
                + JSONObject.quote(payload.optString("path")) + "); }";
            bridge.getWebView().evaluateJavascript(script, null);
        });
    }

    private void handleIntent(Intent intent) {
        if (intent == null || !Intent.ACTION_SEND.equals(intent.getAction())) return;
        String type = intent.getType();
        if (type == null || !type.startsWith("text/")) return;
        String sharedText = intent.getStringExtra(Intent.EXTRA_TEXT);
        if (sharedText == null || sharedText.isEmpty()) return;
        String extractedUrl = extractUrl(sharedText);
        if (extractedUrl == null) return;
        pendingSharedUrl = extractedUrl;
        sendUrlToWebView(extractedUrl);
    }

    private String extractUrl(String text) {
        Matcher matcher = URL_PATTERN.matcher(text);
        return matcher.find() ? matcher.group() : (isValidWebUrl(text) ? text.trim() : null);
    }

    private void sendUrlToWebView(String url) {
        runOnUiThread(() -> {
            if (bridge == null || bridge.getWebView() == null) return;
            String quoted = JSONObject.quote(url);
            String script = "if (window.handleSharedUrl) { window.handleSharedUrl(" + quoted
                + "); } else { window.pendingSharedUrl = " + quoted + "; }";
            bridge.getWebView().evaluateJavascript(script, null);
        });
    }

    private boolean isValidWebUrl(String url) {
        if (url == null) return false;
        try {
            Uri parsed = Uri.parse(url.trim());
            return ("http".equalsIgnoreCase(parsed.getScheme()) || "https".equalsIgnoreCase(parsed.getScheme()))
                && parsed.getHost() != null;
        } catch (Exception exception) {
            return false;
        }
    }

    private String cleanAndroidError(Exception exception) {
        String message = exception.getLocalizedMessage();
        if (message == null || message.trim().isEmpty()) message = exception.toString();
        String lower = message.toLowerCase(Locale.ROOT);
        if (lower.contains("private video") || lower.contains("login required")) {
            return "هذا المحتوى خاص أو يتطلب تسجيل الدخول.";
        }
        if (lower.contains("unavailable")) return "هذا المحتوى غير متاح أو محذوف.";
        if (lower.contains("unsupported url")) return "الرابط غير مدعوم حاليًا.";
        if (lower.contains("network") || lower.contains("connection") || lower.contains("timed out")) {
            return "تعذر الاتصال بالشبكة. تحقق من الإنترنت.";
        }
        return message.replaceAll("(?i)ERROR:\\s*(?:\\[.*?\\]\\s*)?", "").trim();
    }

    private String extractJsonObject(String output) {
        if (output == null) return "";
        int start = output.indexOf('{');
        int end = output.lastIndexOf('}');
        return start >= 0 && end > start ? output.substring(start, end + 1) : "";
    }

    private String sanitizeFileName(String value) {
        String safe = value == null ? "" : value.replaceAll("[\\\\/:*?\"<>|\\r\\n]+", "_").trim();
        return safe.isEmpty() ? "SDN_Media" : safe;
    }

    private String extensionOf(String name) {
        int dot = name == null ? -1 : name.lastIndexOf('.');
        return dot >= 0 && dot < name.length() - 1 ? name.substring(dot + 1) : "";
    }

    private String stripExtension(String name) {
        int dot = name == null ? -1 : name.lastIndexOf('.');
        return dot > 0 ? name.substring(0, dot) : (name == null ? "" : name);
    }
}
