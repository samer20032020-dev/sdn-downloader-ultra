/*==============================================================================
  SDN Downloader Ultra - Android Bridge Emulator (Mobile Web Version)
  ==============================================================================
  هذا الملف يجعل واجهة الهاتف (www/index.html) تعمل كتطبيق حقيقي على أي هاتف
  (أندرويد، آيفون، إلخ) مباشرة في المتصفح، دون الحاجة إلى كود Java/Kotlin أصلي.
  
  يقوم بمحاكاة كائن window.androidInterface بالكامل ويخزن البيانات محلياً في
  متصفح الهاتف باستخدام localStorage، بحيث تعمل جميع الأزرار والميزات.
==============================================================================*/

(function() {
  'use strict';

  // ---------- إعدادات التخزين المحلي ----------
  const STORAGE_KEYS = {
    DOWNLOADS: 'sdn_mobile_downloads',
    MUSIC_TRACKS: 'sdn_music_tracks',
    HISTORY: 'sdn_mobile_history',
    SETTINGS: 'sdn_mobile_settings',
    SAVE_PATH: 'sdn_mobile_save_path'
  };

  // ---------- دوال مساعدة للتخزين ----------
  function getStorage(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch (e) {
      return fallback;
    }
  }

  function setStorage(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (e) {
      console.warn('SDN Bridge: فشل في التخزين المحلي', e);
      return false;
    }
  }

  // ---------- توليد معرف فريد ----------
  function generateId() {
    return 'sdn_' + Date.now() + '_' + Math.random().toString(36).slice(2, 11);
  }

  // ---------- كائن الواجهة المحاكى ----------
  const AndroidBridge = {

    // === التحقق من تسجيل دخول يوتيوب (محاكاة) ===
    isYouTubeLoggedIn: function() {
      const settings = getStorage(STORAGE_KEYS.SETTINGS, {});
      return Boolean(settings.youtube_logged_in);
    },

    // === بدء تسجيل دخول يوتيوب (محاكاة - يفتح نافذة يوتيوب في تبويب جديد) ===
    startYouTubeLogin: function() {
      const loginUrl = 'https://accounts.google.com/ServiceLogin?service=youtube&continue=https%3A%2F%2Fwww.youtube.com%2F';
      try {
        window.open(loginUrl, '_blank');
      } catch (e) {
        console.warn('SDN Bridge: تعذر فتح نافذة تسجيل الدخول', e);
      }
      // محاكاة النجاح بعد تخزين الحالة
      const settings = getStorage(STORAGE_KEYS.SETTINGS, {});
      settings.youtube_logged_in = true;
      setStorage(STORAGE_KEYS.SETTINGS, settings);
      if (window.onYouTubeLoginComplete) {
        setTimeout(() => window.onYouTubeLoginComplete(true), 1000);
      }
    },

    // === تسجيل خروج من يوتيوب ===
    logoutYouTube: function() {
      const settings = getStorage(STORAGE_KEYS.SETTINGS, {});
      settings.youtube_logged_in = false;
      setStorage(STORAGE_KEYS.SETTINGS, settings);
      if (window.onYouTubeLoginComplete) {
        window.onYouTubeLoginComplete(false);
      }
    },

    // === فتح متصفح يوتيوب الذكي (محاكاة - يفتح يوتيوب في تبويب جديد) ===
    openYouTubeBrowser: function(startUrl) {
      const url = startUrl || 'https://www.youtube.com';
      try {
        window.open(url, '_blank');
      } catch (e) {
        console.warn('SDN Bridge: تعذر فتح متصفح يوتيوب', e);
      }
    },

    // === جلب معلومات الوسائط (محاكاة - يعرض رسالة أن backend غير متاح في المتصفح) ===
    fetchMediaInfo: function(url) {
      console.log('SDN Bridge: fetchMediaInfo called with', url);
      if (window.onAndroidMediaInfo) {
        window.onAndroidMediaInfo(JSON.stringify({
          error: 'هذه النسخة تعمل في متصفح الهاتف. للتحميل الفعلي يرجى استخدام تطبيق سطح المكتب (Windows) أو تطبيق أندرويد الأصلي.'
        }));
      }
    },

    fetchMediaInfoEx: function(url, cookieSource, proxyValue) {
      console.log('SDN Bridge: fetchMediaInfoEx called with', url, cookieSource, proxyValue);
      if (window.onAndroidMediaInfo) {
        window.onAndroidMediaInfo(JSON.stringify({
          error: 'هذه النسخة تعمل في متصفح الهاتف. للتحميل الفعلي يرجى استخدام تطبيق سطح المكتب (Windows) أو تطبيق أندرويد الأصلي.'
        }));
      }
    },

    // === بدء تنزيل وسائط (محاكاة - يسجل في السجل المحلي) ===
    downloadMedia: function(url, optionJson) {
      console.log('SDN Bridge: downloadMedia called', url, optionJson);
      let option = {};
      try { option = JSON.parse(optionJson); } catch (e) { option = {}; }

      const isAudio = option.type === 'audio' || option.is_audio === true;
      const quality = option.quality || (isAudio ? '320' : '1080');
      const ext = isAudio ? (option.ext || 'mp3') : 'mp4';

      // إنشاء عنصر تنزيل محاكي
      const downloadItem = {
        id: generateId(),
        url: url,
        title: 'جاري التحضير...',
        quality: quality,
        ext: ext,
        type: isAudio ? 'audio' : 'video',
        status: 'downloading',
        progress: 0,
        speed: '0 KB/s',
        eta: '',
        filepath: '',
        date: new Date().toISOString(),
        isAudio: isAudio
      };

      // حفظ في التنزيلات النشطة
      const downloads = getStorage(STORAGE_KEYS.DOWNLOADS, []);
      downloads.unshift(downloadItem);
      setStorage(STORAGE_KEYS.DOWNLOADS, downloads);

      // تحديث واجهة التقدم إذا كانت موجودة
      if (window.updateProgress) {
        window.updateProgress({
          status: 'downloading',
          percent: 0,
          msg: '🚀 جاري 준비 التحميل... (نسخة متصفح)',
          item_title: downloadItem.title,
          speed_str: 'جاري الاتصال...',
          downloaded_str: '0 KB',
          total_str: ''
        });
      }

      // محاكاة تقدم التحميل
      let progress = 0;
      const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 95) progress = 95;

        downloadItem.progress = progress;
        downloadItem.speed = Math.floor(Math.random() * 500 + 100) + ' KB/s';

        // تحديث التخزين
        const currentDownloads = getStorage(STORAGE_KEYS.DOWNLOADS, []);
        const idx = currentDownloads.findIndex(d => d.id === downloadItem.id);
        if (idx >= 0) {
          currentDownloads[idx] = downloadItem;
          setStorage(STORAGE_KEYS.DOWNLOADS, currentDownloads);
        }

        if (window.updateProgress) {
          window.updateProgress({
            status: 'downloading',
            percent: progress,
            msg: '⬇️ جاري التحميل...',
            item_title: downloadItem.title,
            speed_str: downloadItem.speed,
            downloaded_str: Math.floor(progress * 10) + ' KB',
            total_str: '10000 KB'
          });
        }

        if (progress >= 95) {
          clearInterval(interval);
          setTimeout(() => {
            downloadItem.status = 'finished';
            downloadItem.progress = 100;
            downloadItem.title = 'ملف وسائط (' + ext.toUpperCase() + ')';
            downloadItem.filepath = '/sdn_downloads/' + downloadItem.id + '.' + ext;

            const currentDownloads2 = getStorage(STORAGE_KEYS.DOWNLOADS, []);
            const idx2 = currentDownloads2.findIndex(d => d.id === downloadItem.id);
            if (idx2 >= 0) {
              currentDownloads2[idx2] = downloadItem;
              setStorage(STORAGE_KEYS.DOWNLOADS, currentDownloads2);
            }

            if (window.updateProgress) {
              window.updateProgress({
                status: 'finished',
                percent: 100,
                msg: '🎉 اكتمل التحميل بنجاح! (نسخة متصفح)',
                item_title: downloadItem.title,
                speed_str: '',
                downloaded_str: '10000 KB',
                total_str: '10000 KB'
              });
            }

            // إضافة إلى المكتبة الصوتية إذا كان صوتاً
            if (isAudio) {
              const tracks = getStorage(STORAGE_KEYS.MUSIC_TRACKS, []);
              const track = {
                id: downloadItem.id,
                title: downloadItem.title,
                uploader: 'SDN Mobile',
                format: ext.toUpperCase(),
                size: 10000,
                url: downloadItem.filepath,
                filepath: downloadItem.filepath,
                thumbnail: 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=300',
                date: downloadItem.date
              };
              tracks.unshift(track);
              setStorage(STORAGE_KEYS.MUSIC_TRACKS, tracks);
              if (window.refreshAudioPlaylist) {
                window.refreshAudioPlaylist();
              }
            }

            // إضافة إلى السجل
            const history = getStorage(STORAGE_KEYS.HISTORY, []);
            history.unshift({
              title: downloadItem.title,
              quality: isAudio ? 'صوت MP3' : 'فيديو MP4',
              type: isAudio ? 'audio' : 'video',
              filepath: downloadItem.filepath,
              url: url,
              date: downloadItem.date
            });
            setStorage(STORAGE_KEYS.HISTORY, history);
            if (window.refreshHistoryUI) {
              window.refreshHistoryUI();
            }

          }, 500);
        }
      }, 800);

      return true; // بدأ التنزيل
    },

    // === إلغاء التنزيل ===
    cancelDownload: function() {
      const downloads = getStorage(STORAGE_KEYS.DOWNLOADS, []);
      const active = downloads.find(d => d.status === 'downloading');
      if (active) {
        active.status = 'cancelled';
        setStorage(STORAGE_KEYS.DOWNLOADS, downloads);
      }
      if (window.updateProgress) {
        window.updateProgress({
          status: 'cancelled',
          percent: 0,
          msg: '🛑 تم إلغاء التنزيل',
          error: 'تم الإلغاء من قبل المستخدم'
        });
      }
      return true;
    },

    // === قائمة الملفات الصوتية ===
    listAudioFiles: function() {
      const tracks = getStorage(STORAGE_KEYS.MUSIC_TRACKS, []);
      return JSON.stringify({ tracks: tracks, folder: 'التنزيلات (محلي)' });
    },

    // === فتح مجلد التنزيلات (محاكاة) ===
    openDownloads: function() {
      const path = getStorage(STORAGE_KEYS.SAVE_PATH, 'التنزيلات الداخلية للهاتف');
      alert('📁 مجلد الحفظ الحالي:\n' + path + '\n\n(هذه النسخة تعمل في المتصفح، الملفات تُحفظ في التخزين المحلي للمتصفح)');
    },

    // === حذف ملف ===
    deleteFile: function(filepath) {
      if (!filepath) return false;
      const tracks = getStorage(STORAGE_KEYS.MUSIC_TRACKS, []);
      const filtered = tracks.filter(t => t.filepath !== filepath && t.url !== filepath);
      setStorage(STORAGE_KEYS.MUSIC_TRACKS, filtered);

      const downloads = getStorage(STORAGE_KEYS.DOWNLOADS, []);
      const filteredDl = downloads.filter(d => d.filepath !== filepath && d.url !== filepath);
      setStorage(STORAGE_KEYS.DOWNLOADS, filteredDl);

      if (window.refreshAudioPlaylist) window.refreshAudioPlaylist();
      if (window.refreshDownloadsList) window.refreshDownloadsList();
      return true;
    },

    // === اختيار مجلد الحفظ (محاكاة) ===
    pickFolder: function() {
      const path = prompt('أدخل اسم مجلد الحفظ:', getStorage(STORAGE_KEYS.SAVE_PATH, 'التنزيلات'));
      if (path && path.trim()) {
        setStorage(STORAGE_KEYS.SAVE_PATH, path.trim());
        if (window.handleSelectedFolder) {
          window.handleSelectedFolder(path.trim());
        }
        alert('✅ تم تحديد مجلد الحفظ: ' + path.trim());
      }
    },

    // === اختيار ملف كوكيز (محاكاة) ===
    pickCookieFile: function() {
      alert('📁 اختيار ملف الكوكيز:\nهذه الميزة متاحة في تطبيق أندرويد الأصلي.\nفي نسخة المتصفح، يتم استخدام الكوكيز الافتراضية.');
    },

    // === تنزيل تحديث (محاكاة) ===
    downloadUpdate: function(url, path) {
      alert('📦 تحديث التطبيق:\nالرابط: ' + url + '\n\nهذه النسخة تعمل في المتصفح. يرجى تحميل أحدث إصدار من تطبيق سطح المكتب أو من متجر التطبيقات.');
    },

    // === جلب الرابط المشترك (محاكاة) ===
    getSharedUrl: function() {
      return getStorage('sdn_shared_url', null);
    },

    // === تعيين رابط مشترك ===
    setSharedUrl: function(url) {
      setStorage('sdn_shared_url', url);
    }

  };

  // ---------- تعيين الواجهة على النافذة ----------
  window.androidInterface = AndroidBridge;

  // ---------- إشعار المستخدم بأن هذه نسخة متصفح ----------
  // يمكن تفعيله أو تعطيله حسب الحاجة
  /*
  setTimeout(() => {
    const existing = document.getElementById('sdn-browser-notice');
    if (!existing && typeof toast === 'function') {
      toast('📱 تعمل SDN في متصفح هاتفك. certaines الميزات تتطلب تطبيق أندرويد الأصلي.', 'fas fa-info-circle');
    }
  }, 2000);
  */

  console.log('SDN Android Bridge Emulator loaded successfully.');

  // ---------- إشعار ترحيب عند تحميل الصفحة ----------
  if (typeof toast === 'function') {
    setTimeout(() => {
      toast('📱 SDN تعمل في متصفح هاتفك. جميع أدوات التنزيل والموسيقى متاحة. للتحميل الفعلي من يوتيوب استخدم تطبيق سطح المكتب (Windows).', 'fas fa-info-circle');
    }, 1500);
  }

})();