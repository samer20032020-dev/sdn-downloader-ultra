package com.sdn.downloader.ultra;

import android.app.Activity;
import android.app.DownloadManager;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.webkit.JavascriptInterface;
import android.widget.Toast;
import com.getcapacitor.BridgeActivity;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class MainActivity extends BridgeActivity {
    private static final int REQUEST_CODE_PICK_FOLDER = 9999;
    private String pendingSharedUrl = null;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        handleIntent(getIntent());
        setupAndroidBridge();
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        handleIntent(intent);
    }

    @Override
    public void onResume() {
        super.onResume();
        setupAndroidBridge();
    }

    private void setupAndroidBridge() {
        this.runOnUiThread(() -> {
            if (bridge != null && bridge.getWebView() != null) {
                bridge.getWebView().addJavascriptInterface(new AndroidBridge(), "androidInterface");
            }
        });
    }

    public class AndroidBridge {
        @JavascriptInterface
        public void pickFolder() {
            try {
                Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
                startActivityForResult(intent, REQUEST_CODE_PICK_FOLDER);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        @JavascriptInterface
        public String getSharedUrl() {
            String url = pendingSharedUrl;
            pendingSharedUrl = null;
            return url != null ? url : "";
        }

        @JavascriptInterface
        public boolean downloadFile(String url, String fileName, String mimeType, String subDir) {
            try {
                if (url == null || url.isEmpty()) return false;
                DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
                request.setTitle(fileName != null && !fileName.isEmpty() ? fileName : "SDN_Video");
                request.setDescription("تحميل عبر SDN Downloader Ultra");
                request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                
                String destinationDir = Environment.DIRECTORY_DOWNLOADS;
                if (subDir != null && !subDir.isEmpty()) {
                    if (subDir.equalsIgnoreCase("Movies")) destinationDir = Environment.DIRECTORY_MOVIES;
                    else if (subDir.equalsIgnoreCase("Music")) destinationDir = Environment.DIRECTORY_MUSIC;
                    else if (subDir.equalsIgnoreCase("DCIM")) destinationDir = Environment.DIRECTORY_DCIM;
                }
                
                request.setDestinationInExternalPublicDir(destinationDir, fileName);
                if (mimeType != null && !mimeType.isEmpty()) {
                    request.setMimeType(mimeType);
                }

                DownloadManager manager = (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);
                if (manager != null) {
                    manager.enqueue(request);
                    runOnUiThread(() -> Toast.makeText(MainActivity.this, "⚡ بدأ التحميل في الخلفية: " + fileName, Toast.LENGTH_SHORT).show());
                    return true;
                }
            } catch (Exception e) {
                e.printStackTrace();
                runOnUiThread(() -> Toast.makeText(MainActivity.this, "❌ خطأ في التنزيل: " + e.getLocalizedMessage(), Toast.LENGTH_LONG).show());
            }
            return false;
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_CODE_PICK_FOLDER && resultCode == Activity.RESULT_OK && data != null) {
            Uri treeUri = data.getData();
            if (treeUri != null) {
                try {
                    getContentResolver().takePersistableUriPermission(
                        treeUri,
                        Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                    );
                } catch (Exception e) {}
                String path = treeUri.getLastPathSegment();
                if (path != null && path.contains(":")) {
                    path = path.substring(path.indexOf(":") + 1);
                }
                sendFolderPathToWebView(path != null && !path.isEmpty() ? path : treeUri.getPath());
            }
        }
    }

    private void sendFolderPathToWebView(final String folderPath) {
        this.runOnUiThread(() -> {
            if (bridge != null && bridge.getWebView() != null) {
                String safePath = folderPath.replace("'", "\\'").replace("\n", "");
                String js = "if (window.handleSelectedFolder) { window.handleSelectedFolder('" + safePath + "'); }";
                bridge.getWebView().evaluateJavascript(js, null);
            }
        });
    }

    private void handleIntent(Intent intent) {
        if (intent == null) return;
        String action = intent.getAction();
        String type = intent.getType();

        if (Intent.ACTION_SEND.equals(action) && type != null) {
            if ("text/plain".equals(type) || type.startsWith("text/")) {
                String sharedText = intent.getStringExtra(Intent.EXTRA_TEXT);
                if (sharedText != null && !sharedText.isEmpty()) {
                    String extractedUrl = extractUrl(sharedText);
                    if (extractedUrl != null) {
                        pendingSharedUrl = extractedUrl;
                        sendUrlToWebView(extractedUrl);
                    }
                }
            }
        }
    }

    private String extractUrl(String text) {
        Pattern pattern = Pattern.compile("https?://\\S+");
        Matcher matcher = pattern.matcher(text);
        if (matcher.find()) {
            return matcher.group();
        }
        return text;
    }

    private void sendUrlToWebView(final String url) {
        this.runOnUiThread(() -> {
            if (bridge != null && bridge.getWebView() != null) {
                String safeUrl = url.replace("'", "\\'").replace("\n", "");
                String js = "if (window.handleSharedUrl) { window.handleSharedUrl('" + safeUrl + "'); } else { window.pendingSharedUrl = '" + safeUrl + "'; }";
                bridge.getWebView().evaluateJavascript(js, null);
            }
        });
    }
}

