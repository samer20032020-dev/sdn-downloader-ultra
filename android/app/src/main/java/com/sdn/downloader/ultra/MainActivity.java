package com.sdn.downloader.ultra;

import android.Manifest;
import android.app.Activity;
import android.app.DownloadManager;
import android.content.ContentResolver;
import android.content.ContentUris;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.media.MediaScannerConnection;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.provider.Settings;
import android.util.Log;
import android.webkit.JavascriptInterface;
import android.webkit.MimeTypeMap;
import android.widget.Toast;

import androidx.core.content.FileProvider;
import androidx.documentfile.provider.DocumentFile;

import com.getcapacitor.BridgeActivity;
import com.yausername.ffmpeg.FFmpeg;
import com.yausername.youtubedl_android.YoutubeDL;
import com.yausername.youtubedl_android.YoutubeDLException;
import com.yausername.youtubedl_android.YoutubeDLRequest;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
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
    private static final int REQUEST_CODE_PICK_COOKIE = 9998;
    private static final int REQUEST_CODE_PERMISSIONS = 9997;
    private static final long YTDLP_UPDATE_INTERVAL_MS = 24L * 60L * 60L * 1000L;
    private static final Pattern URL_PATTERN = Pattern.compile("https?://\\S+");
    private static final String PREFS_TREE_URI = "sdn_tree_uri";
    private static final String PUBLIC_FOLDER_NAME = "SDN Downloader";

    private final ExecutorService mediaExecutor = Executors.newSingleThreadExecutor();
    private final ExecutorService updateExecutor = Executors.newSingleThreadExecutor();
    private final AtomicBoolean mediaBusy = new AtomicBoolean(false);
    private final AtomicBoolean cancellationRequested = new AtomicBoolean(false);
    private volatile boolean mediaEngineReady = false;
    private volatile String activeProcessId = "";
    private volatile long lastNotifyAt = 0L;
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
            if (!mediaBusy.get() && !activeProcessId.isEmpty()) {
                YoutubeDL.getInstance().destroyProcessById(activeProcessId);
            }
        } catch (Exception ignored) {
        }
        if (!mediaBusy.get()) {
            mediaExecutor.shutdownNow();
        }
        updateExecutor.shutdownNow();
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
            long lastChecked = getPreferences(Context.MODE_PRIVATE).getLong("yt_dlp_checked_at", 0L);
            long now = System.currentTimeMillis();
            if (now - lastChecked < YTDLP_UPDATE_INTERVAL_MS) {
                return;
            }
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
            runOnUiThread(() -> {
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
            });
        }

        @JavascriptInterface
        public void pickCookieFile() {
            runOnUiThread(() -> {
                try {
                    Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                    intent.addCategory(Intent.CATEGORY_OPENABLE);
                    intent.setType("*/*");
                    startActivityForResult(intent, REQUEST_CODE_PICK_COOKIE);
                } catch (Exception exception) {
                    Log.w(TAG, "Cookie picker failed", exception);
                }
            });
        }

        @JavascriptInterface
        public String getSharedUrl() {
            String url = pendingSharedUrl;
            pendingSharedUrl = null;
            return url != null ? url : "";
        }

        @JavascriptInterface
        public boolean fetchMediaInfo(String url) {
            return fetchMediaInfoEx(url, "none", "");
        }

        @JavascriptInterface
        public boolean fetchMediaInfoEx(String url, String cookies, String proxy) {
            if (!isValidWebUrl(url) || mediaBusy.get()) return false;
            mediaExecutor.execute(() -> fetchMediaInfoInternal(url.trim(), cookies, proxy));
            return true;
        }

        @JavascriptInterface
        public boolean downloadMedia(String url, String optionJson) {
            if (!isValidWebUrl(url) || !mediaBusy.compareAndSet(false, true)) return false;
            cancellationRequested.set(false);
            requestRuntimePermissions();
            mediaExecutor.execute(() -> {
                try {
                    downloadMediaInternal(url.trim(), optionJson);
                } catch (Exception fatal) {
                    Log.e(TAG, "Unexpected download failure", fatal);
                    sendProgress("error", 0, cleanAndroidError(fatal), null, 0);
                } finally {
                    mediaBusy.set(false);
                    activeProcessId = "";
                    stopDownloadService();
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
                if (path.startsWith("content://")) {
                    return getContentResolver().delete(Uri.parse(path), null, null) > 0;
                }
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
                Log.w(TAG, "deleteFile failed", exception);
                return false;
            }
        }

        @JavascriptInterface
        public void openDownloads() {
            runOnUiThread(() -> {
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
                    fallback.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    startActivity(fallback);
                }
            });
        }

        @JavascriptInterface
        public boolean downloadUpdate(String url, String sha256) {
            if (!isValidWebUrl(url)) return false;
            downloadUpdateInternal(url.trim(), sha256 == null ? "" : sha256.trim());
            return true;
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

    private String cleanMediaUrl(String rawUrl) {
        if (rawUrl == null || rawUrl.trim().isEmpty()) return "";
        String url = rawUrl.trim();
        try {
            Uri uri = Uri.parse(url);
            String host = uri.getHost() != null ? uri.getHost().toLowerCase(Locale.ROOT) : "";
            boolean isYouTube = "youtu.be".equals(host) || "www.youtu.be".equals(host)
                || host.endsWith("youtube.com");
            if (!isYouTube) return url;

            String playlistId = uri.getQueryParameter("list");
            String videoId = uri.getQueryParameter("v");
            if (videoId == null || videoId.isEmpty()) {
                if ("youtu.be".equals(host) || "www.youtu.be".equals(host)) {
                    String path = uri.getPath();
                    if (path != null) {
                        path = path.replaceAll("^/+", "");
                        int slash = path.indexOf('/');
                        videoId = slash > 0 ? path.substring(0, slash) : path;
                    }
                } else if (uri.getPath() != null && uri.getPath().startsWith("/shorts/")) {
                    String[] parts = uri.getPath().split("/shorts/")[1].split("/");
                    videoId = parts.length > 0 ? parts[0] : "";
                } else if (uri.getPath() != null && uri.getPath().startsWith("/embed/")) {
                    String[] parts = uri.getPath().split("/embed/")[1].split("/");
                    videoId = parts.length > 0 ? parts[0] : "";
                }
            }

            if (playlistId != null && !playlistId.isEmpty()) {
                String upper = playlistId.toUpperCase(Locale.ROOT);
                boolean isUnviewable = upper.startsWith("RD") || upper.startsWith("UL")
                    || upper.startsWith("PU") || "WL".equals(upper) || "LL".equals(upper) || "LM".equals(upper);
                if (isUnviewable) {
                    if (videoId == null || videoId.isEmpty()) {
                        Matcher m = Pattern.compile("^RD(?:MM|AMVM)?([a-zA-Z0-9_-]{11})$", Pattern.CASE_INSENSITIVE).matcher(playlistId);
                        if (m.find()) videoId = m.group(1);
                    }
                    if (videoId != null && !videoId.isEmpty()) {
                        return "https://www.youtube.com/watch?v=" + videoId;
                    }
                }
            }
        } catch (Exception ignored) {
        }
        return url;
    }

    private void fetchMediaInfoInternal(String url, String cookies, String proxy) {
        JSONObject response = new JSONObject();
        String targetUrl = cleanMediaUrl(url);
        try {
            if (!initializeMediaEngine()) throw new Exception("تعذر تهيئة محرك الوسائط.");
            YoutubeDLRequest request = new YoutubeDLRequest(targetUrl);
            request.addOption("--dump-single-json");
            request.addOption("--flat-playlist");
            request.addOption("--skip-download");
            request.addOption("--no-warnings");
            JSONObject probeOptions = new JSONObject();
            probeOptions.put("cookies", cookies == null ? "none" : cookies);
            probeOptions.put("proxy", proxy == null ? "" : proxy);
            applyAccessOptions(request, probeOptions);

            String output = YoutubeDL.getInstance().execute(request).getOut();
            String jsonText = extractJsonObject(output);
            if (jsonText.isEmpty()) throw new Exception("لم تُرجع المنصة معلومات قابلة للقراءة.");
            response.put("data", new JSONObject(jsonText));
            response.put("source_url", targetUrl);
        } catch (Exception exception) {
            Log.e(TAG, "Android media info failed", exception);
            try {
                response.put("error", cleanAndroidError(exception));
                response.put("source_url", targetUrl);
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

            File downloadRoot = getWorkingDirectory();
            if (!downloadRoot.exists() && !downloadRoot.mkdirs()) {
                throw new Exception("تعذر إنشاء مجلد العمل المؤقت.");
            }

            YoutubeDLRequest request = new YoutubeDLRequest(cleanMediaUrl(url));
            request.addOption("--no-mtime");
            request.addOption("--continue");
            request.addOption("--retries", 15);
            request.addOption("--fragment-retries", 15);
            request.addOption("--concurrent-fragments", option.optBoolean("turbo", false) ? "4" : "1");
            request.addOption("--http-chunk-size", "10M");
            request.addOption("--no-overwrites");
            request.addOption("--windows-filenames");

            long rateLimit = option.optLong("ratelimit", 0);
            if (rateLimit > 0) request.addOption("--limit-rate", String.valueOf(rateLimit));

            if (option.optBoolean("allow_live", true)) {
                request.addOption("--live-from-start");
            } else {
                request.addOption("--match-filter", "!is_live");
            }

            if (option.optBoolean("download_subtitles", false)) {
                request.addOption("--write-subs");
                request.addOption("--write-auto-subs");
                request.addOption("--sub-langs", "ar,en");
                request.addOption("--convert-subs", "srt");
                request.addOption("--ignore-errors");
            }

            applyTrimOptions(request, option);

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

            request.addOption("-o", buildOutputTemplate(downloadRoot, isPlaylist, qualityTag, runToken));
            applyAccessOptions(request, option);

            startDownloadService(isPlaylist ? "تنزيل القائمة" : "تنزيل الوسائط");
            activeProcessId = "sdn-" + runToken;
            Function3<Float, Long, String, Unit> callback = (progress, eta, line) -> {
                JSONObject extra = new JSONObject();
                try {
                    extra.put("eta_str", eta != null ? eta + " ثانية" : "");
                    extra.put("speed_str", line == null ? "" : line);
                } catch (Exception ignored) {
                }
                float value = progress == null ? 0 : progress;
                sendProgress("downloading", value, "جاري التنزيل", extra, 0);
                updateDownloadService("جاري التنزيل", Math.round(value) + "%", Math.round(value));
                return Unit.INSTANCE;
            };

            YoutubeDL.getInstance().execute(request, activeProcessId, callback);
            List<File> outputFiles = findRunFiles(downloadRoot, runToken, startedAt);
            if (outputFiles.isEmpty()) throw new Exception("اكتمل الأمر لكن لم يتم العثور على الملف النهائي.");

            List<String> exportedPaths = exportFinishedFiles(outputFiles);

            JSONObject completed = new JSONObject();
            completed.put("status", "complete");
            completed.put("count", exportedPaths.size());
            completed.put("is_playlist", isPlaylist);
            completed.put("media_type", isAudio ? "audio" : "video");
            completed.put("directory", publicDirectoryLabel());
            completed.put("filepath", exportedPaths.isEmpty() ? "" : exportedPaths.get(0));
            completed.put("elapsed", Math.round((System.currentTimeMillis() - startedAt) / 100.0) / 10.0);
            JSONArray filesJson = new JSONArray();
            for (int index = 0; index < exportedPaths.size(); index++) {
                JSONObject fileJson = new JSONObject();
                fileJson.put("filepath", exportedPaths.get(index));
                fileJson.put("title", stripExtension(outputFiles.get(index).getName()));
                fileJson.put("playable_url", "");
                filesJson.put(fileJson);
            }
            completed.put("files", filesJson);
            dispatchJsonObjectCallback("updateProgress", completed);
        } catch (Exception exception) {
            Log.e(TAG, "Android yt-dlp download failed", exception);
            if (cancellationRequested.get()) {
                sendProgress("cancelled", 0, "تم إلغاء التنزيل", null, 0);
            } else {
                sendProgress("error", 0, cleanAndroidError(exception), null, 0);
            }
        } finally {
            stopDownloadService();
        }
    }

    private void applyAccessOptions(YoutubeDLRequest request, JSONObject option) {
        String cookies = option.optString("cookies", "");
        if (!cookies.isEmpty() && !"none".equals(cookies)) {
            File cookieFile = new File(cookies);
            if (cookieFile.isFile()) request.addOption("--cookies", cookieFile.getAbsolutePath());
        }
        String proxy = option.optString("proxy", "").trim();
        if (!proxy.isEmpty()) request.addOption("--proxy", proxy);
    }

    private void applyTrimOptions(YoutubeDLRequest request, JSONObject option) {
        String start = toHms(option.optString("trim_start", ""));
        String end = toHms(option.optString("trim_end", ""));
        if (start == null && end == null) return;
        String section = "*" + (start != null ? start : "00:00:00") + "-" + (end != null ? end : "inf");
        request.addOption("--download-sections", section);
    }

    private String toHms(String value) {
        if (value == null) return null;
        String trimmed = value.trim();
        if (trimmed.isEmpty()) return null;
        String[] parts = trimmed.split(":");
        try {
            int hours = 0, minutes = 0, seconds = 0;
            if (parts.length == 3) {
                hours = Integer.parseInt(parts[0].trim());
                minutes = Integer.parseInt(parts[1].trim());
                seconds = Integer.parseInt(parts[2].trim());
            } else if (parts.length == 2) {
                minutes = Integer.parseInt(parts[0].trim());
                seconds = Integer.parseInt(parts[1].trim());
            } else {
                seconds = Integer.parseInt(parts[0].trim());
            }
            if (hours < 0 || minutes < 0 || seconds < 0) return null;
            return String.format(Locale.US, "%02d:%02d:%02d", hours, minutes, seconds);
        } catch (Exception exception) {
            return null;
        }
    }

    private String buildOutputTemplate(File root, boolean isPlaylist, String qualityTag, String runToken) {
        if (isPlaylist) {
            return new File(
                root,
                "%(playlist_title|Playlist).120B/%(playlist_index)03d - %(title).150B [%(id)s] ["
                    + qualityTag + "] [" + runToken + "].%(ext)s"
            ).getAbsolutePath();
        }
        return new File(
            root,
            "%(title).170B [%(id)s] [" + qualityTag + "] [" + runToken + "].%(ext)s"
        ).getAbsolutePath();
    }

    private String fallbackFormat(JSONObject option, boolean isAudio) {
        if (isAudio) return "bestaudio/best";
        int height = option.optInt("quality", 0);
        String filter = height > 0 ? "[height<=" + height + "]" : "";
        return "bestvideo" + filter + "[ext=mp4]+bestaudio[ext=m4a]/bestvideo"
            + filter + "+bestaudio/best" + filter + "/best";
    }

    private File getWorkingDirectory() {
        File base = getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
        if (base == null) base = getFilesDir();
        return new File(base, PUBLIC_FOLDER_NAME);
    }

    private String publicDirectoryLabel() {
        return "Download/" + PUBLIC_FOLDER_NAME;
    }

    private List<String> exportFinishedFiles(List<File> files) {
        List<String> exportedPaths = new ArrayList<>();
        for (File file : files) {
            Uri exported = exportFinishedFile(file);
            if (exported != null) {
                exportedPaths.add(exported.toString());
                try {
                    // The working copy is no longer needed once exported.
                    if (!file.delete()) {
                        Log.w(TAG, "Could not remove working copy: " + file.getAbsolutePath());
                    }
                } catch (Exception ignored) {
                }
            } else {
                exportedPaths.add(Uri.fromFile(file).toString());
            }
        }
        return exportedPaths;
    }

    private Uri exportFinishedFile(File source) {
        Uri treeUri = getPersistedTreeUri();
        if (treeUri != null) {
            Uri copied = copyToDocumentTree(treeUri, source);
            if (copied != null) return copied;
            Log.w(TAG, "SAF export failed, falling back to public storage");
        }
        return copyToPublicStorage(source);
    }

    private Uri copyToDocumentTree(Uri treeUri, File source) {
        try {
            DocumentFile root = DocumentFile.fromTreeUri(this, treeUri);
            if (root == null || !root.canWrite()) return null;
            DocumentFile document = root.createFile(mimeTypeOf(source), source.getName());
            if (document == null) return null;
            try (InputStream input = new FileInputStream(source);
                 OutputStream output = getContentResolver().openOutputStream(document.getUri())) {
                if (output == null) throw new IOException("openOutputStream returned null");
                copyStream(input, output);
            } catch (Exception exception) {
                document.delete();
                throw exception;
            }
            return document.getUri();
        } catch (Exception exception) {
            Log.w(TAG, "copyToDocumentTree failed", exception);
            return null;
        }
    }

    private Uri copyToPublicStorage(File source) {
        if (Build.VERSION.SDK_INT >= 29) {
            ContentResolver resolver = getContentResolver();
            ContentValues values = new ContentValues();
            values.put(MediaStore.MediaColumns.DISPLAY_NAME, source.getName());
            values.put(MediaStore.MediaColumns.MIME_TYPE, mimeTypeOf(source));
            values.put(
                MediaStore.MediaColumns.RELATIVE_PATH,
                Environment.DIRECTORY_DOWNLOADS + "/" + PUBLIC_FOLDER_NAME
            );
            values.put(MediaStore.MediaColumns.IS_PENDING, 1);
            Uri uri = null;
            try {
                uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
                if (uri == null) return null;
                try (InputStream input = new FileInputStream(source);
                     OutputStream output = resolver.openOutputStream(uri)) {
                    if (output == null) throw new IOException("openOutputStream returned null");
                    copyStream(input, output);
                }
                ContentValues done = new ContentValues();
                done.put(MediaStore.MediaColumns.IS_PENDING, 0);
                resolver.update(uri, done, null, null);
                return uri;
            } catch (Exception exception) {
                Log.w(TAG, "MediaStore export failed", exception);
                if (uri != null) {
                    try {
                        resolver.delete(uri, null, null);
                    } catch (Exception ignored) {
                    }
                }
                return null;
            }
        }

        if (!hasLegacyStoragePermission()) return null;
        try {
            File publicRoot = new File(
                Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS),
                PUBLIC_FOLDER_NAME
            );
            if (!publicRoot.exists() && !publicRoot.mkdirs()) return null;
            File destination = uniqueFile(publicRoot, source.getName());
            try (InputStream input = new FileInputStream(source);
                 OutputStream output = new FileOutputStream(destination)) {
                copyStream(input, output);
            }
            MediaScannerConnection.scanFile(
                this,
                new String[]{destination.getAbsolutePath()},
                null,
                null
            );
            return Uri.fromFile(destination);
        } catch (Exception exception) {
            Log.w(TAG, "Legacy public export failed", exception);
            return null;
        }
    }

    private File uniqueFile(File directory, String name) {
        File candidate = new File(directory, name);
        if (!candidate.exists()) return candidate;
        String base = stripExtension(name);
        String extension = extensionOf(name);
        for (int index = 1; index < 1000; index++) {
            String candidateName = base + " (" + index + ")" + (extension.isEmpty() ? "" : "." + extension);
            candidate = new File(directory, candidateName);
            if (!candidate.exists()) return candidate;
        }
        return new File(directory, base + "_" + System.currentTimeMillis()
            + (extension.isEmpty() ? "" : "." + extension));
    }

    private boolean hasLegacyStoragePermission() {
        return Build.VERSION.SDK_INT > 28
            || checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED;
    }

    private void requestRuntimePermissions() {
        runOnUiThread(() -> {
            try {
                List<String> missing = new ArrayList<>();
                if (Build.VERSION.SDK_INT >= 33
                    && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                    missing.add(Manifest.permission.POST_NOTIFICATIONS);
                }
                if (Build.VERSION.SDK_INT >= 33
                    && checkSelfPermission(Manifest.permission.READ_MEDIA_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                    missing.add(Manifest.permission.READ_MEDIA_AUDIO);
                }
                if (Build.VERSION.SDK_INT <= 28
                    && checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
                    missing.add(Manifest.permission.WRITE_EXTERNAL_STORAGE);
                }
                if (!missing.isEmpty()) {
                    requestPermissions(missing.toArray(new String[0]), REQUEST_CODE_PERMISSIONS);
                }
            } catch (Exception exception) {
                Log.w(TAG, "Permission request skipped", exception);
            }
        });
    }

    private void startDownloadService(String title) {
        try {
            Intent intent = new Intent(this, DownloadForegroundService.class);
            intent.setAction(DownloadForegroundService.ACTION_START);
            intent.putExtra(DownloadForegroundService.EXTRA_TITLE, title);
            intent.putExtra(DownloadForegroundService.EXTRA_TEXT, "يبدأ التنزيل الآن...");
            intent.putExtra(DownloadForegroundService.EXTRA_PERCENT, 0);
            if (Build.VERSION.SDK_INT >= 26) startForegroundService(intent);
            else startService(intent);
        } catch (Exception exception) {
            Log.w(TAG, "Foreground service start failed", exception);
        }
    }

    private void updateDownloadService(String title, String text, int percent) {
        long now = System.currentTimeMillis();
        if (now - lastNotifyAt < 1000) return;
        lastNotifyAt = now;
        try {
            Intent intent = new Intent(this, DownloadForegroundService.class);
            intent.setAction(DownloadForegroundService.ACTION_UPDATE);
            intent.putExtra(DownloadForegroundService.EXTRA_TITLE, title);
            intent.putExtra(DownloadForegroundService.EXTRA_TEXT, text);
            intent.putExtra(DownloadForegroundService.EXTRA_PERCENT, percent);
            startService(intent);
        } catch (Exception ignored) {
        }
    }

    private void stopDownloadService() {
        try {
            stopService(new Intent(this, DownloadForegroundService.class));
        } catch (Exception ignored) {
        }
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
            List<JSONObject> tracks = new ArrayList<>();
            Set<String> seen = new HashSet<>();
            collectLocalAudioTracks(getWorkingDirectory(), tracks, seen);
            collectMediaStoreAudioTracks(tracks, seen);
            tracks.sort((left, right) -> Long.compare(
                right.optLong("modified", 0L),
                left.optLong("modified", 0L)
            ));

            JSONArray array = new JSONArray();
            int maximum = Math.min(tracks.size(), 2000);
            for (int index = 0; index < maximum; index++) {
                array.put(tracks.get(index));
            }
            result.put("tracks", array);
            result.put("folder", publicDirectoryLabel());
        } catch (Exception exception) {
            try {
                result.put("tracks", new JSONArray());
                result.put("error", exception.getLocalizedMessage());
            } catch (Exception ignored) {
            }
        }
        return result;
    }

    private void collectLocalAudioTracks(File directory, List<JSONObject> tracks, Set<String> seen) {
        if (directory == null || !directory.isDirectory()) return;
        File[] children = directory.listFiles();
        if (children == null) return;
        for (File child : children) {
            if (child.isDirectory()) {
                collectLocalAudioTracks(child, tracks, seen);
            } else if (isAudioFile(child)) {
                addAudioTrack(tracks, seen, child.getAbsolutePath(), child.getName(),
                    child.getParentFile() != null ? child.getParentFile().getName() : "الجهاز",
                    child.length(), child.lastModified());
            }
        }
    }

    private void collectMediaStoreAudioTracks(List<JSONObject> tracks, Set<String> seen) {
        Cursor cursor = null;
        try {
            ContentResolver resolver = getContentResolver();
            String[] projection;
            if (Build.VERSION.SDK_INT >= 29) {
                projection = new String[]{
                    MediaStore.Audio.Media._ID,
                    MediaStore.Audio.Media.DISPLAY_NAME,
                    MediaStore.Audio.Media.SIZE,
                    MediaStore.Audio.Media.DATE_MODIFIED,
                    MediaStore.Audio.Media.RELATIVE_PATH,
                };
            } else {
                projection = new String[]{
                    MediaStore.Audio.Media._ID,
                    MediaStore.Audio.Media.DISPLAY_NAME,
                    MediaStore.Audio.Media.SIZE,
                    MediaStore.Audio.Media.DATE_MODIFIED,
                    MediaStore.Audio.Media.DATA,
                };
            }
            cursor = resolver.query(
                MediaStore.Audio.Media.EXTERNAL_CONTENT_URI,
                projection,
                MediaStore.Audio.Media.SIZE + " > 0",
                null,
                MediaStore.Audio.Media.DATE_MODIFIED + " DESC"
            );
            if (cursor == null) return;
            int idIndex = cursor.getColumnIndex(MediaStore.Audio.Media._ID);
            int nameIndex = cursor.getColumnIndex(MediaStore.Audio.Media.DISPLAY_NAME);
            int sizeIndex = cursor.getColumnIndex(MediaStore.Audio.Media.SIZE);
            int dateIndex = cursor.getColumnIndex(MediaStore.Audio.Media.DATE_MODIFIED);
            int extraIndex = cursor.getColumnIndex(
                Build.VERSION.SDK_INT >= 29
                    ? MediaStore.Audio.Media.RELATIVE_PATH
                    : MediaStore.Audio.Media.DATA
            );
            while (cursor.moveToNext()) {
                String name = nameIndex >= 0 ? cursor.getString(nameIndex) : null;
                if (name == null || !isAudioName(name)) continue;
                long size = sizeIndex >= 0 ? cursor.getLong(sizeIndex) : 0;
                long modified = dateIndex >= 0 ? cursor.getLong(dateIndex) * 1000L : 0L;
                String path;
                if (Build.VERSION.SDK_INT >= 29) {
                    long id = idIndex >= 0 ? cursor.getLong(idIndex) : -1;
                    if (id < 0) continue;
                    path = ContentUris.withAppendedId(MediaStore.Audio.Media.EXTERNAL_CONTENT_URI, id).toString();
                } else {
                    path = extraIndex >= 0 ? cursor.getString(extraIndex) : null;
                    if (path == null || path.isEmpty()) continue;
                }
                String uploader = extraIndex >= 0 && Build.VERSION.SDK_INT < 29 && cursor.getString(extraIndex) != null
                    ? new File(cursor.getString(extraIndex)).getParent()
                    : null;
                addAudioTrack(tracks, seen, path, name, uploader == null ? "المكتبة" : uploader, size, modified);
            }
        } catch (Exception exception) {
            Log.w(TAG, "MediaStore audio query failed", exception);
        } finally {
            if (cursor != null) cursor.close();
        }
    }

    private void addAudioTrack(
        List<JSONObject> tracks,
        Set<String> seen,
        String path,
        String name,
        String uploader,
        long size,
        long modified
    ) {
        String key = name + "|" + size;
        if (!seen.add(key)) return;
        try {
            JSONObject track = new JSONObject();
            track.put("title", stripExtension(name));
            track.put("uploader", uploader == null ? "الجهاز" : uploader);
            track.put("url", path);
            track.put("filepath", path);
            track.put("format", extensionOf(name).toUpperCase(Locale.ROOT));
            track.put("size", size);
            track.put("modified", modified);
            track.put("thumbnail", "");
            tracks.add(track);
        } catch (Exception ignored) {
        }
    }

    private void downloadUpdateInternal(String url, String expectedSha256) {
        updateExecutor.execute(() -> {
            File updatesDir = new File(getCacheDir(), "updates");
            if (!updatesDir.exists() && !updatesDir.mkdirs()) {
                sendUpdateError("تعذر تجهيز مجلد التحديث");
                return;
            }
            File apkFile = new File(updatesDir, "SDN_Update.apk");
            HttpURLConnection connection = null;
            try {
                connection = openFollowingRedirects(new URL(url));
                long total = connection.getContentLengthLong();
                MessageDigest digest = MessageDigest.getInstance("SHA-256");
                long downloaded = 0L;
                long lastSent = 0L;
                try (InputStream input = connection.getInputStream();
                     FileOutputStream output = new FileOutputStream(apkFile)) {
                    byte[] buffer = new byte[64 * 1024];
                    int read;
                    while ((read = input.read(buffer)) != -1) {
                        output.write(buffer, 0, read);
                        digest.update(buffer, 0, read);
                        downloaded += read;
                        long now = System.currentTimeMillis();
                        if (now - lastSent > 400) {
                            lastSent = now;
                            int percent = total > 0 ? (int) (downloaded * 100 / total) : 50;
                            sendUpdateProgress(percent, downloaded, total);
                        }
                    }
                }
                String actualSha = toHex(digest.digest());
                if (!expectedSha256.isEmpty() && !actualSha.equalsIgnoreCase(expectedSha256)) {
                    apkFile.delete();
                    sendUpdateError("فشل التحقق من بصمة ملف التحديث");
                    return;
                }
                sendUpdateComplete();
                installApkFile(apkFile);
            } catch (Exception exception) {
                Log.e(TAG, "Update download failed", exception);
                apkFile.delete();
                sendUpdateError("تعذر تنزيل التحديث: " + exception.getLocalizedMessage());
            } finally {
                if (connection != null) connection.disconnect();
            }
        });
    }

    private HttpURLConnection openFollowingRedirects(URL url) throws IOException {
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setInstanceFollowRedirects(false);
        connection.setConnectTimeout(20000);
        connection.setReadTimeout(60000);
        connection.setRequestProperty("User-Agent", "SDN-Downloader-Ultra");
        int status = connection.getResponseCode();
        if (status >= 300 && status < 400) {
            String location = connection.getHeaderField("Location");
            connection.disconnect();
            if (location != null && !location.isEmpty()) {
                return openFollowingRedirects(new URL(location));
            }
        }
        return connection;
    }

    private void installApkFile(File apkFile) {
        runOnUiThread(() -> {
            try {
                if (Build.VERSION.SDK_INT >= 26 && !getPackageManager().canRequestPackageInstalls()) {
                    Intent settingsIntent = new Intent(
                        Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                        Uri.parse("package:" + getPackageName())
                    );
                    settingsIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    startActivity(settingsIntent);
                    Toast.makeText(
                        this,
                        "اسمح بتثبيت التطبيقات من SDN ثم أعد المحاولة",
                        Toast.LENGTH_LONG
                    ).show();
                    return;
                }
                Uri apkUri = FileProvider.getUriForFile(this, getPackageName() + ".fileprovider", apkFile);
                Intent installIntent = new Intent(Intent.ACTION_VIEW);
                installIntent.setDataAndType(apkUri, "application/vnd.android.package-archive");
                installIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_GRANT_READ_URI_PERMISSION);
                startActivity(installIntent);
            } catch (Exception exception) {
                Log.e(TAG, "APK install intent failed", exception);
                sendUpdateError("تعذر فتح مثبّت الحزمة: " + exception.getLocalizedMessage());
            }
        });
    }

    private void sendUpdateProgress(int percent, long downloaded, long total) {
        JSONObject payload = new JSONObject();
        try {
            payload.put("status", "downloading");
            payload.put("kind", "android");
            payload.put("pct", percent);
            payload.put("downloaded", downloaded);
            payload.put("total", total);
        } catch (Exception ignored) {
        }
        dispatchJsonObjectCallback("onUpdateProgress", payload);
    }

    private void sendUpdateComplete() {
        JSONObject payload = new JSONObject();
        try {
            payload.put("status", "complete");
            payload.put("kind", "android");
        } catch (Exception ignored) {
        }
        dispatchJsonObjectCallback("onUpdateProgress", payload);
    }

    private void sendUpdateError(String message) {
        JSONObject payload = new JSONObject();
        try {
            payload.put("status", "error");
            payload.put("kind", "android");
            payload.put("error", message);
        } catch (Exception ignored) {
        }
        dispatchJsonObjectCallback("onUpdateProgress", payload);
    }

    private String toHex(byte[] bytes) {
        StringBuilder builder = new StringBuilder(bytes.length * 2);
        for (byte value : bytes) {
            builder.append(Character.forDigit((value >> 4) & 0xF, 16));
            builder.append(Character.forDigit(value & 0xF, 16));
        }
        return builder.toString();
    }

    private Uri getPersistedTreeUri() {
        try {
            String stored = getPreferences(Context.MODE_PRIVATE).getString(PREFS_TREE_URI, null);
            if (stored == null || stored.isEmpty()) return null;
            return Uri.parse(stored);
        } catch (Exception exception) {
            return null;
        }
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
        if (resultCode != Activity.RESULT_OK || data == null) return;

        if (requestCode == REQUEST_CODE_PICK_FOLDER) {
            Uri treeUri = data.getData();
            if (treeUri == null) return;
            try {
                getContentResolver().takePersistableUriPermission(
                    treeUri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                );
            } catch (Exception ignored) {
            }
            SharedPreferences preferences = getPreferences(Context.MODE_PRIVATE);
            preferences.edit().putString(PREFS_TREE_URI, treeUri.toString()).apply();
            String path = treeUri.getLastPathSegment();
            if (path != null && path.contains(":")) path = path.substring(path.indexOf(":") + 1);
            sendFolderPathToWebView(path != null && !path.isEmpty() ? path : treeUri.getPath());
        } else if (requestCode == REQUEST_CODE_PICK_COOKIE) {
            Uri sourceUri = data.getData();
            if (sourceUri == null) return;
            try {
                File cookieFile = new File(getCacheDir(), "sdn_cookies.txt");
                try (InputStream input = getContentResolver().openInputStream(sourceUri);
                     FileOutputStream output = new FileOutputStream(cookieFile)) {
                    if (input == null) throw new IOException("openInputStream returned null");
                    copyStream(input, output);
                }
                sendCookiePathToWebView(cookieFile.getAbsolutePath());
            } catch (Exception exception) {
                Log.w(TAG, "Cookie import failed", exception);
                runOnUiThread(() -> Toast.makeText(
                    this,
                    "❌ تعذر قراءة ملف الكوكيز",
                    Toast.LENGTH_SHORT
                ).show());
            }
        }
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

    private void sendCookiePathToWebView(String cookiePath) {
        runOnUiThread(() -> {
            if (bridge == null || bridge.getWebView() == null) return;
            String script = "if (window.handleCookieFileSelected) { window.handleCookieFileSelected("
                + JSONObject.quote(cookiePath) + "); }";
            bridge.getWebView().evaluateJavascript(script, null);
        });
    }

    private void handleIntent(Intent intent) {
        if (intent == null) return;
        String action = intent.getAction();
        if (Intent.ACTION_SEND.equals(action)) {
            String type = intent.getType();
            if (type == null || !type.startsWith("text/")) return;
            String sharedText = intent.getStringExtra(Intent.EXTRA_TEXT);
            String extractedUrl = extractUrl(sharedText);
            if (extractedUrl == null) return;
            pendingSharedUrl = extractedUrl;
            sendUrlToWebView(extractedUrl);
        } else if (Intent.ACTION_SEND_MULTIPLE.equals(action)) {
            ArrayList<String> sharedTexts = intent.getStringArrayListExtra(Intent.EXTRA_TEXT);
            if (sharedTexts == null) return;
            for (String text : sharedTexts) {
                String extractedUrl = extractUrl(text);
                if (extractedUrl != null) {
                    pendingSharedUrl = extractedUrl;
                    sendUrlToWebView(extractedUrl);
                    return;
                }
            }
        }
    }

    private String extractUrl(String text) {
        if (text == null || text.isEmpty()) return null;
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
        if (lower.contains("unviewable") || lower.contains("this playlist type is unviewable")) {
            return "قائمة التشغيل هذه من نوع ميكس (Mix) أو خاصة وغير متاحة كقائمة.";
        }
        if (lower.contains("playlist does not exist")) {
            if (lower.contains("wl") || lower.contains("watch later")) {
                return "🔒 قائمة «المشاهدة لاحقاً» (Watch Later) خاصة بحسابك في يوتيوب ولا يمكن الوصول إليها بدون كوكيز. انقل الفيديوهات لقائمة جديدة (غير مدرجة أو عامة) أو أضف ملف cookies.txt.";
            }
            if (lower.contains("ll") || lower.contains("liked")) {
                return "🔒 قائمة «الفيديوهات التي أعجبتني» خاصة بحسابك الشخصي. انقل الفيديوهات لقائمة جديدة أو أضف ملف كوكيز.";
            }
            return "❌ قائمة التشغيل غير موجودة أو تم حذفها، أو أنها خاصة وتتطلب كوكيز مسجلة الدخول.";
        }
        if (lower.contains("403") || lower.contains("forbidden")) {
            return "خوادم المنصة رفضت الطلب مؤقتًا (HTTP 403: Forbidden). جرب جودة أخرى.";
        }
        if (lower.contains("429") || lower.contains("too many requests")) {
            return "المنصة حدّت الطلبات مؤقتًا (HTTP 429). انتظر قليلًا أو استخدم الكوكيز/البروكسي.";
        }
        if (lower.contains("private video") || lower.contains("login required")
            || lower.contains("sign in to confirm")) {
            return "هذا المحتوى خاص أو يتطلب تسجيل الدخول. أضف ملف كوكيز من الإعدادات.";
        }
        if (lower.contains("unavailable")) return "هذا المحتوى غير متاح أو محذوف.";
        if (lower.contains("unsupported url")) return "الرابط غير مدعوم حاليًا.";
        if (lower.contains("match filter") || lower.contains("does not pass filter")) {
            return "تم رفض البث المباشر حسب الإعدادات. فعّل خيار البث المباشر أولًا.";
        }
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

    private boolean isAudioFile(File file) {
        return isAudioName(file == null ? "" : file.getName());
    }

    private boolean isAudioName(String name) {
        return extensionOf(name).toLowerCase(Locale.ROOT).matches("mp3|m4a|aac|flac|ogg|opus|wav|wma");
    }

    private boolean isMediaFile(File file) {
        String extension = extensionOf(file.getName()).toLowerCase(Locale.ROOT);
        return extension.matches("mp4|mkv|webm|mov|avi|mp3|m4a|aac|flac|ogg|opus|wav|wma|srt|vtt|ass");
    }

    private String mimeTypeOf(File file) {
        String extension = extensionOf(file.getName()).toLowerCase(Locale.ROOT);
        String mime = MimeTypeMap.getSingleton().getMimeTypeFromExtension(extension);
        if (mime != null && !mime.isEmpty()) return mime;
        if (isAudioName(file.getName())) return "audio/mpeg";
        if (extension.matches("mp4|mkv|webm|mov|avi")) return "video/mp4";
        return "application/octet-stream";
    }

    private void copyStream(InputStream input, OutputStream output) throws IOException {
        byte[] buffer = new byte[64 * 1024];
        int read;
        while ((read = input.read(buffer)) != -1) {
            output.write(buffer, 0, read);
        }
        output.flush();
    }

    private String fileNameOf(String path) {
        try {
            if (path.startsWith("content://")) {
                Uri uri = Uri.parse(path);
                String last = uri.getLastPathSegment();
                if (last != null && last.contains("/")) last = last.substring(last.lastIndexOf('/') + 1);
                return last == null ? "SDN_Media" : last;
            }
            if (path.startsWith("file://")) return new File(Uri.parse(path).getPath()).getName();
            return new File(path).getName();
        } catch (Exception exception) {
            return "SDN_Media";
        }
    }
}
