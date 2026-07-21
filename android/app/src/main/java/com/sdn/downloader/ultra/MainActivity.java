package com.sdn.downloader.ultra;

import android.content.Intent;
import android.os.Bundle;
import com.getcapacitor.BridgeActivity;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class MainActivity extends BridgeActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        handleIntent(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        handleIntent(intent);
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
