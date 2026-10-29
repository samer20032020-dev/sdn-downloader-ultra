/*==============================================================================
  SDN Downloader Ultra - Service Worker (PWA)
  ==============================================================================
  يجعل تطبيق الهاتف يعمل دون إنترنت ويخزن الموارد مؤقتاً لأداء أسرع.
==============================================================================*/

const CACHE_NAME = 'sdn-mobile-v1.0.60';
const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './android_bridge.js',
  './manifest.json',
  'https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&family=Tajawal:wght@400;500;700;800;900&display=swap',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=100',
  'https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=500',
  'https://images.unsplash.com/photo-1492691527719-9d1e07e534b4?w=300'
];

// تثبيت Service Worker وتخزين الموارد الأساسية
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('SDN SW: تخزين الموارد الأساسية');
        return cache.addAll(ASSETS_TO_CACHE);
      })
      .then(() => self.skipWaiting())
  );
});

// تفعيل Service Worker وحذف التخزين القديم
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

// اعتراض الطلبات وتقديمها من التخزين المؤقت إذا كانت متوفرة
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // تجاهل الطلبات الخارجية غير الضرورية
  if (!url.hostname.includes('unsplash.com') && 
      !url.hostname.includes('fonts.googleapis.com') &&
      !url.hostname.includes('cdnjs.cloudflare.com') &&
      url.origin !== self.location.origin) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return fetch(event.request)
          .then((response) => {
            // تخزين الاستجابات الناجحة للطلبات الأساسية فقط
            if (response.ok && event.request.method === 'GET' && 
                (url.origin === self.location.origin || url.hostname.includes('unsplash.com'))) {
              const responseClone = response.clone();
              caches.open(CACHE_NAME).then((cache) => {
                cache.put(event.request, responseClone);
              });
            }
            return response;
          })
          .catch(() => {
            // إذا فشل الاتصال ولم يكن هناك نسخة مخزنة، أعرض صفحة بسيطة
            if (event.request.mode === 'navigate') {
              return caches.match('./index.html');
            }
          });
      })
  );
});

// معالجة الرسائل من التطبيق الرئيسي
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
