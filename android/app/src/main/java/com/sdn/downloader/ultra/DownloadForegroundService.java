package com.sdn.downloader.ultra;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;

import androidx.core.app.NotificationCompat;

public class DownloadForegroundService extends Service {
    public static final String ACTION_START = "com.sdn.downloader.ultra.action.START";
    public static final String ACTION_UPDATE = "com.sdn.downloader.ultra.action.UPDATE";
    public static final String ACTION_STOP = "com.sdn.downloader.ultra.action.STOP";
    public static final String EXTRA_TITLE = "title";
    public static final String EXTRA_TEXT = "text";
    public static final String EXTRA_PERCENT = "percent";

    private static final String CHANNEL_ID = "sdn_downloads";
    private static final int NOTIFICATION_ID = 4420;

    private PowerManager.WakeLock wakeLock;
    private boolean foregroundStarted = false;

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        acquireWakeLock();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent != null ? intent.getAction() : null;
        if (ACTION_STOP.equals(action)) {
            stopSelf();
            return START_NOT_STICKY;
        }

        String title = intent != null && intent.getStringExtra(EXTRA_TITLE) != null
            ? intent.getStringExtra(EXTRA_TITLE)
            : "جاري التنزيل...";
        String text = intent != null && intent.getStringExtra(EXTRA_TEXT) != null
            ? intent.getStringExtra(EXTRA_TEXT)
            : "";
        int percent = intent != null ? intent.getIntExtra(EXTRA_PERCENT, -1) : -1;

        Notification notification = buildNotification(title, text, percent);
        if (!foregroundStarted) {
            if (Build.VERSION.SDK_INT >= 29) {
                startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);
            } else {
                startForeground(NOTIFICATION_ID, notification);
            }
            foregroundStarted = true;
        } else {
            NotificationManager manager = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
            if (manager != null) manager.notify(NOTIFICATION_ID, notification);
        }
        return START_STICKY;
    }

    private Notification buildNotification(String title, String text, int percent) {
        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(title)
            .setContentText(text)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setPriority(NotificationCompat.PRIORITY_LOW);
        if (percent >= 0) {
            builder.setProgress(100, Math.max(0, Math.min(percent, 100)), false);
        } else {
            builder.setProgress(0, 0, true);
        }
        return builder.build();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT < 26) return;
        NotificationManager manager = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        if (manager == null) return;
        NotificationChannel channel = new NotificationChannel(
            CHANNEL_ID,
            "تنزيلات SDN",
            NotificationManager.IMPORTANCE_LOW
        );
        channel.setDescription("إشعارات تقدم التنزيل في الخلفية");
        manager.createNotificationChannel(channel);
    }

    private void acquireWakeLock() {
        try {
            PowerManager powerManager = (PowerManager) getSystemService(POWER_SERVICE);
            if (powerManager == null) return;
            wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "SDN:download");
            wakeLock.setReferenceCounted(false);
            wakeLock.acquire(2 * 60 * 60 * 1000L);
        } catch (Exception ignored) {
        }
    }

    @Override
    public void onDestroy() {
        if (wakeLock != null && wakeLock.isHeld()) {
            try {
                wakeLock.release();
            } catch (Exception ignored) {
            }
        }
        if (Build.VERSION.SDK_INT >= 24) {
            stopForeground(STOP_FOREGROUND_REMOVE);
        } else {
            stopForeground(true);
        }
        foregroundStarted = false;
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
