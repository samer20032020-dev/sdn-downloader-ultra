package com.sdn.downloader.ultra;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import com.getcapacitor.BridgeActivity;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class MainActivity extends BridgeActivity {
    private static final int REQUEST_CODE_PICK_FOLDER = 9999;

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
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_CODE_PICK_FOLDER && resultCode == Activity.RESULT_OK && data != null) {
            Uri treeUri = data.getData();
            if (treeUri != null) {
                getContentResolver().takePersistableUriPermission(
                    treeUri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                );
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
                String js = "if (window.handleSharedUrl) { window.handleSharedUrl('" + safeUrl + "'); } else { document.addEventListener('DOMContentLoaded', function() { if (window.handleSharedUrl) window.handleSharedUrl('" + safeUrl + "'); }); }";
                bridge.getWebView().evaluateJavascript(js, null);
            }
        });
    }
}
