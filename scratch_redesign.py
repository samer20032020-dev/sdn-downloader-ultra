import sys
sys.stdout.reconfigure(encoding='utf-8')

new_css = """/* ==========================================================================
   ULTRA-LUXURY, SOFT & MODERN SETTINGS DESIGN SYSTEM (100% REDESIGN)
   ========================================================================== */

.settings-panel {
  display: none;
  flex-direction: column;
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
  padding: 10px 8px 50px 8px;
  animation: fadeInSettings 0.28s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
.settings-panel.active {
  display: flex !important;
  flex-direction: column !important;
}

@keyframes fadeInSettings {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ── Minimalist Glowing Header ── */
.settings-header-clean {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
  padding: 4px 6px;
}
.settings-header-info {
  display: flex;
  align-items: center;
  gap: 14px;
}
.settings-header-icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(56, 189, 248, 0.18) 0%, rgba(99, 102, 241, 0.18) 100%);
  border: 1px solid rgba(56, 189, 248, 0.35);
  color: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  box-shadow: 0 4px 20px rgba(56, 189, 248, 0.2);
  flex-shrink: 0;
}
.settings-title-main {
  font-size: 1.35rem;
  font-weight: 800;
  color: var(--text-main);
  letter-spacing: -0.015em;
  margin: 0;
}
.settings-subtitle-main {
  font-size: 0.82rem;
  color: var(--text-sub);
  margin-top: 3px;
  line-height: 1.4;
}

/* ── Floating Segmented Filter Bar ── */
.settings-filter-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow-x: auto;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 999px;
  padding: 5px;
  margin-bottom: 24px;
  scrollbar-width: none;
  backdrop-filter: blur(12px);
}
.settings-filter-bar::-webkit-scrollbar { display: none; }
.settings-filter-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 16px;
  border-radius: 999px;
  font-size: 0.82rem;
  font-weight: 700;
  font-family: inherit;
  color: var(--text-sub);
  background: transparent;
  border: none;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
  flex-shrink: 0;
}
.settings-filter-pill:hover {
  color: var(--text-main);
  background: rgba(255, 255, 255, 0.06);
}
.settings-filter-pill.active {
  color: #ffffff;
  background: linear-gradient(135deg, #0284c7 0%, #38bdf8 100%);
  box-shadow: 0 3px 12px rgba(56, 189, 248, 0.35);
}

/* ── Section Titles (macOS / iOS 18 style) ── */
.settings-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  font-weight: 800;
  color: var(--primary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 8px;
  margin-inline-start: 8px;
}
.settings-section-title i {
  font-size: 0.78rem;
}

/* ── Grouped Glass Cards (STRICT COLUMN FLEX) ── */
.settings-cards-grid {
  display: flex !important;
  flex-direction: column !important;
  gap: 20px;
  width: 100%;
}
.settings-card {
  display: flex !important;
  flex-direction: column !important;
  width: 100%;
  background: linear-gradient(165deg, rgba(17, 24, 39, 0.72) 0%, rgba(10, 15, 28, 0.88) 100%);
  border: 1px solid rgba(255, 255, 255, 0.075);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 10px 32px -8px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(28px);
  -webkit-backdrop-filter: blur(28px);
  transition: border-color 0.22s ease, box-shadow 0.22s ease;
}
.settings-card:hover {
  border-color: rgba(56, 189, 248, 0.22);
}

/* ── Clean Full-Width Rows ── */
.settings-items-list {
  display: flex !important;
  flex-direction: column !important;
  width: 100%;
}
.settings-row {
  display: flex !important;
  flex-direction: row !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 16px;
  padding: 14px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.045);
  transition: background 0.15s ease;
  width: 100%;
  box-sizing: border-box;
}
.settings-row:last-child {
  border-bottom: none;
}
.settings-row:hover {
  background: rgba(255, 255, 255, 0.02);
}

.row-info {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1;
  min-width: 0;
}
.row-icon {
  width: 36px;
  height: 36px;
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
  flex-shrink: 0;
  border: 1px solid rgba(255, 255, 255, 0.06);
}
.row-texts {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.row-title {
  font-size: 0.92rem;
  font-weight: 700;
  color: var(--text-main);
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.row-desc {
  font-size: 0.77rem;
  color: var(--text-sub);
  margin-top: 3px;
  line-height: 1.42;
}

/* ── Soft Badges ── */
.soft-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 7px;
  border-radius: 6px;
  font-size: 0.68rem;
  font-weight: 700;
  background: rgba(56, 189, 248, 0.12);
  color: var(--primary);
  border: 1px solid rgba(56, 189, 248, 0.22);
}

/* ── Luxury iOS 18 Switch ── */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 46px;
  height: 26px;
  flex-shrink: 0;
  cursor: pointer;
}
.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  inset: 0;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.14);
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.slider:before {
  position: absolute;
  content: "";
  height: 20px;
  width: 20px;
  left: 2px;
  bottom: 2px;
  background: #ffffff;
  border-radius: 50%;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
}
.toggle-switch input:checked + .slider {
  background: linear-gradient(135deg, #0284c7 0%, #38bdf8 100%);
  border-color: rgba(56, 189, 248, 0.6);
  box-shadow: 0 0 14px rgba(56, 189, 248, 0.45);
}
.toggle-switch input:checked + .slider:before {
  transform: translateX(20px);
}

/* ── Modern Dropdown Selects ── */
.custom-select-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
}
.select-dropdown {
  appearance: none;
  -webkit-appearance: none;
  background: rgba(255, 255, 255, 0.055);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--text-main);
  padding: 8px 34px 8px 14px;
  border-radius: 12px;
  font-size: 0.83rem;
  font-family: inherit;
  font-weight: 700;
  cursor: pointer;
  outline: none;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  min-width: 155px;
}
.select-dropdown:hover {
  background: rgba(255, 255, 255, 0.085);
  border-color: rgba(56, 189, 248, 0.4);
}
.select-dropdown:focus {
  border-color: var(--primary);
  box-shadow: 0 0 14px var(--primary-glow);
}
.select-dropdown option {
  background: #0b1120;
  color: #f8fafc;
}
.select-chevron {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.72rem;
  color: var(--muted);
  pointer-events: none;
}

/* ── Storage Folder Display & Action ── */
.storage-control-group {
  display: flex;
  align-items: center;
  gap: 10px;
}
.storage-path-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(0, 0, 0, 0.28);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 6px 12px;
  max-width: 240px;
  overflow: hidden;
}
.path-box-icon {
  font-size: 0.85rem;
  color: var(--primary);
  flex-shrink: 0;
}
.path-text {
  font-family: monospace;
  font-size: 0.76rem !important;
  color: var(--primary) !important;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  direction: ltr;
}
.settings-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 15px;
  border-radius: 11px;
  font-size: 0.82rem;
  font-weight: 700;
  border: none;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  white-space: nowrap;
}
.settings-action-btn.primary-glow-btn {
  background: linear-gradient(135deg, #0284c7 0%, #38bdf8 100%);
  color: #fff;
  box-shadow: 0 3px 12px rgba(56, 189, 248, 0.28);
}
.settings-action-btn.primary-glow-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 5px 18px rgba(56, 189, 248, 0.42);
}
.settings-action-btn.amber-btn {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.3);
}
.settings-action-btn.amber-btn:hover {
  background: rgba(245, 158, 11, 0.25);
}

/* ── YouTube Connected Account Row ── */
.youtube-account-row {
  display: flex !important;
  flex-direction: row !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 16px;
  padding: 16px 20px;
  background: rgba(239, 68, 68, 0.04);
  border-bottom: 1px solid rgba(255, 255, 255, 0.045);
  box-sizing: border-box;
}
.yt-account-info {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  flex: 1;
}
.yt-icon-box {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  position: relative;
  flex-shrink: 0;
  border: 1px solid rgba(239, 68, 68, 0.25);
}
.yt-live-pulse {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
}
.yt-status-badge {
  font-size: 0.7rem;
  padding: 2px 9px;
  border-radius: 999px;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-sub);
}
.yt-status-badge.active {
  background: rgba(16, 185, 129, 0.16);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
}
.yt-desc-text {
  font-size: 0.77rem;
  color: var(--text-sub);
  margin-top: 3px;
  line-height: 1.42;
}
.yt-login-btn {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: #fff;
  border: none;
  padding: 8px 18px;
  border-radius: 11px;
  font-weight: 700;
  font-size: 0.82rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  box-shadow: 0 3px 12px rgba(239, 68, 68, 0.3);
  transition: all 0.2s ease;
  white-space: nowrap;
}
.yt-login-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 5px 18px rgba(239, 68, 68, 0.45);
}
.yt-logout-btn {
  background: rgba(244, 63, 94, 0.12);
  color: #f43f5e;
  border: 1px solid rgba(244, 63, 94, 0.3);
  padding: 8px 16px;
  border-radius: 11px;
  font-weight: 700;
  font-size: 0.82rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
  white-space: nowrap;
}
.yt-logout-btn:hover {
  background: rgba(244, 63, 94, 0.2);
}

/* ── Proxy Input ── */
.proxy-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}
.custom-proxy-input {
  background: rgba(255, 255, 255, 0.055);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 11px;
  padding: 7px 12px 7px 32px;
  color: var(--text-main);
  font-size: 0.82rem;
  font-family: monospace;
  outline: none;
  transition: all 0.2s ease;
  direction: ltr;
  width: 200px;
}
.custom-proxy-input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 12px var(--primary-glow);
}
.proxy-prefix-icon {
  position: absolute;
  left: 10px;
  font-size: 0.78rem;
  color: var(--muted);
  pointer-events: none;
}

/* ── System Status Tiles Grid ── */
.system-hub-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding: 16px 20px;
  box-sizing: border-box;
  width: 100%;
}
@media (max-width: 580px) {
  .system-hub-grid { grid-template-columns: 1fr; }
}
.system-tile {
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  padding: 13px 15px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  transition: all 0.2s ease;
}
.system-tile:hover {
  background: rgba(255, 255, 255, 0.045);
  border-color: rgba(255, 255, 255, 0.09);
}
.tile-info {
  display: flex;
  align-items: center;
  gap: 11px;
  min-width: 0;
}
.tile-icon-wrap {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
  flex-shrink: 0;
}
.tile-title {
  font-size: 0.88rem;
  font-weight: 700;
  color: var(--text-main);
}
.system-btn {
  padding: 6px 14px;
  border-radius: 9px;
  font-size: 0.78rem;
  font-weight: 700;
  border: none;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
  white-space: nowrap;
  font-family: inherit;
}
.system-btn.primary-btn {
  background: rgba(56, 189, 248, 0.14);
  color: var(--primary);
  border: 1px solid rgba(56, 189, 248, 0.3);
}
.system-btn.primary-btn:hover {
  background: rgba(56, 189, 248, 0.24);
}
.system-btn.emerald-btn {
  background: rgba(16, 185, 129, 0.14);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
}
.system-btn.emerald-btn:hover {
  background: rgba(16, 185, 129, 0.24);
}

/* ── Light Theme Adaptations ── */
body.light-theme .settings-card {
  background: #ffffff;
  border-color: rgba(15, 23, 42, 0.08);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
}
body.light-theme .settings-row {
  border-bottom-color: rgba(15, 23, 42, 0.05);
}
body.light-theme .settings-row:hover {
  background: rgba(15, 23, 42, 0.02);
}
body.light-theme .settings-filter-bar {
  background: rgba(15, 23, 42, 0.04);
  border-color: rgba(15, 23, 42, 0.08);
}
body.light-theme .settings-filter-pill {
  color: #475569;
}
body.light-theme .settings-filter-pill:hover {
  background: rgba(15, 23, 42, 0.06);
  color: #0f172a;
}
body.light-theme .settings-filter-pill.active {
  color: #fff;
  background: linear-gradient(135deg, #0284c7 0%, #38bdf8 100%);
}
body.light-theme .slider {
  background: rgba(15, 23, 42, 0.12);
  border-color: rgba(15, 23, 42, 0.08);
}
body.light-theme .select-dropdown,
body.light-theme .custom-proxy-input {
  background: #f8fafc;
  border-color: rgba(15, 23, 42, 0.12);
  color: #0f172a;
}
body.light-theme .select-dropdown option {
  background: #ffffff;
  color: #0f172a;
}
body.light-theme .storage-path-box {
  background: #f1f5f9;
  border-color: rgba(15, 23, 42, 0.08);
}
body.light-theme .system-tile {
  background: #f8fafc;
  border-color: rgba(15, 23, 42, 0.06);
}
body.light-theme .youtube-account-row {
  background: rgba(239, 68, 68, 0.03);
  border-bottom-color: rgba(15, 23, 42, 0.05);
}
"""

new_html = """        <div id="viewSettings" class="settings-panel">
      <!-- Minimalist Clean Header -->
      <div class="settings-header-clean">
        <div class="settings-header-info">
          <div class="settings-header-icon"><i class="fas fa-sliders-h"></i></div>
          <div>
            <h2 class="settings-title-main">الإعدادات</h2>
            <p class="settings-subtitle-main">تخصيص الخيارات، التخزين، ومحرك التنزيل</p>
          </div>
        </div>
      </div>

      <!-- Floating Segmented Filter Bar -->
      <div class="settings-filter-bar">
        <button class="settings-filter-pill active" onclick="filterSettingsCategory('all', this)">
          <i class="fas fa-layer-group"></i> <span>الكل</span>
        </button>
        <button class="settings-filter-pill" onclick="filterSettingsCategory('appearance', this)">
          <i class="fas fa-palette"></i> <span>المظهر</span>
        </button>
        <button class="settings-filter-pill" onclick="filterSettingsCategory('storage', this)">
          <i class="fas fa-folder"></i> <span>التخزين</span>
        </button>
        <button class="settings-filter-pill" onclick="filterSettingsCategory('accounts', this)">
          <i class="fab fa-youtube"></i> <span>الحسابات</span>
        </button>
        <button class="settings-filter-pill" onclick="filterSettingsCategory('performance', this)">
          <i class="fas fa-bolt"></i> <span>الأداء</span>
        </button>
        <button class="settings-filter-pill" onclick="filterSettingsCategory('system', this)">
          <i class="fas fa-info-circle"></i> <span>النظام</span>
        </button>
      </div>

      <!-- Container for all cards -->
      <div class="settings-cards-grid">
        <!-- Category 1: Appearance & Defaults (المظهر وجودة التنزيل) -->
        <div class="settings-card" data-category="appearance">
          <div class="settings-section-title" style="padding: 14px 20px 6px 20px; margin: 0;">
            <i class="fas fa-palette"></i> المظهر والواجهة الافتراضية
          </div>

          <div class="settings-items-list">
            <!-- Theme Toggle -->
            <div class="settings-row">
              <div class="row-info">
                <div class="row-icon" style="color: #f59e0b; background: rgba(245, 158, 11, 0.12);">
                  <i class="fas fa-moon" id="themeIcon"></i>
                </div>
                <div class="row-texts">
                  <div class="row-title">الـثـيـم (داكن / فاتح) <span class="soft-badge" id="themeBadgeText">ليلي</span></div>
                  <div class="row-desc">التبديل الفوري بين الوضع الليلي المظلم والثيم الأبيض النظيف</div>
                </div>
              </div>
              <div class="settings-control">
                <label class="toggle-switch">
                  <input type="checkbox" id="themeToggle">
                  <span class="slider"></span>
                </label>
              </div>
            </div>

            <!-- Default Quality -->
            <div class="settings-row">
              <div class="row-info">
                <div class="row-icon" style="color: #38bdf8; background: rgba(56, 189, 248, 0.12);">
                  <i class="fas fa-photo-video"></i>
                </div>
                <div class="row-texts">
                  <div class="row-title">جودة التنزيل الافتراضية</div>
                  <div class="row-desc">تحديد الجودة المفضلة تلقائياً عند فحص أي رابط فيديو جديد</div>
                </div>
              </div>
              <div class="settings-control">
                <div class="custom-select-wrap">
                  <select class="select-dropdown" id="defaultQualitySelect">
                    <option value="best">👑 أفضل جودة متاحة (Best)</option>
                    <option value="2160">🌟 4K Ultra HD (2160p)</option>
                    <option value="1080">🎬 1080p (Full HD)</option>
                    <option value="720" selected>⚡ 720p (HD)</option>
                    <option value="480">📱 480p (SD)</option>
                    <option value="360">📉 360p (خفيف)</option>
                    <option value="mp3">🎵 صوت MP3 فقط</option>
                  </select>
                  <i class="fas fa-chevron-down select-chevron"></i>
                </div>
              </div>
            </div>

            <!-- Speed Limit -->
            <div class="settings-row">
              <div class="row-info">
                <div class="row-icon" style="color: #10b981; background: rgba(16, 185, 129, 0.12);">
                  <i class="fas fa-tachometer-alt"></i>
                </div>
                <div class="row-texts">
                  <div class="row-title">تحديد سرعة التحميل</div>
                  <div class="row-desc">ضبط الحد الأقصى للسرعة لتجنب استهلاك كامل سرعة الشبكة</div>
                </div>
              </div>
              <div class="settings-control">
                <div class="custom-select-wrap">
                  <select class="select-dropdown" id="speedLimitSelect">
                    <option value="0" selected>🚀 أقصى سرعة (بلا قيود)</option>
                    <option value="500">🐢 500 KB/s</option>
                    <option value="1000">⚡ 1 MB/s</option>
                    <option value="2000">🔥 2 MB/s</option>
                    <option value="5000">💨 5 MB/s</option>
                  </select>
                  <i class="fas fa-chevron-down select-chevron"></i>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Category 2: Storage & Files (التخزين والحفظ) -->
        <div class="settings-card" data-category="storage">
          <div class="settings-section-title" style="padding: 14px 20px 6px 20px; margin: 0;">
            <i class="fas fa-hdd"></i> التخزين والحفظ والملفات
          </div>

          <div class="settings-items-list">
            <!-- Save Path -->
            <div class="settings-row">
              <div class="row-info">
                <div class="row-icon" style="color: #10b981; background: rgba(16, 185, 129, 0.12);">
                  <i class="fas fa-folder"></i>
                </div>
                <div class="row-texts">
                  <div class="row-title">مجلد حفظ التحميلات</div>
                  <div class="row-desc">المسار الذي تحفظ به جميع الفيديوهات والصوتيات</div>
                </div>
              </div>
              <div class="settings-control storage-control-group">
                <div class="storage-path-box">
                  <i class="fas fa-folder-open path-box-icon"></i>
                  <span class="path-text" id="savePathTxt">Downloads</span>
                </div>
                <button class="settings-action-btn primary-glow-btn" id="changeFolderBtn">
                  <i class="fas fa-folder-plus"></i> تغيير
                </button>
              </div>
            </div>

            <!-- Auto Paste -->
            <div class="settings-row">
              <div class="row-info">
                <div class="row-icon" style="color: #8b5cf6; background: rgba(139, 92, 246, 0.12);">
                  <i class="fas fa-paste"></i>
                </div>
                <div class="row-texts">
                  <div class="row-title">لصق الحافظة التلقائي</div>
                  <div class="row-desc">قراءة الروابط المنسوخة تلقائياً وفحصها فور فتح التطبيق</div>
                </div>
              </div>
              <div class="settings-control">
                <label class="toggle-switch">
                  <input type="checkbox" id="autoPasteToggle" checked>
                  <span class="slider"></span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <!-- Category 3: Accounts & Cookies (حساب YouTube والتسجيل) -->
        <div class="settings-card" data-category="accounts">
          <div class="settings-section-title" style="padding: 14px 20px 6px 20px; margin: 0;">
            <i class="fab fa-youtube"></i> حساب YouTube وتكامل الكوكيز
          </div>

          <div class="settings-items-list">
            <!-- YouTube Account Row -->
            <div class="youtube-account-row" id="youtubeLoginRow">
              <div class="yt-account-info">
                <div class="yt-icon-box">
                  <i class="fab fa-youtube"></i>
                  <span class="yt-live-pulse" id="ytPulseDot" style="display:none;"></span>
                </div>
                <div class="row-texts">
                  <div class="row-title">
                    حساب YouTube
                    <span id="youtubeBadge" class="yt-status-badge">غير متصل</span>
                    <span id="statYoutubeStatus" style="display:none;">غير متصل</span>
                  </div>
                  <div class="yt-desc-text" id="youtubeLoginStatus">
                    يتيح تنزيل قائمة المشاهدة لاحقاً، المحتوى المقيد عمرياً (18+)، والفيديوهات الخاصة بحسابك مباشرة.
                  </div>
                </div>
              </div>
              <div class="yt-buttons-area">
                <button class="yt-login-btn" id="youtubeLoginBtn" onclick="startYouTubeLogin()">
                  <i class="fas fa-sign-in-alt"></i> تسجيل الدخول
                </button>
                <button class="yt-logout-btn" id="youtubeLogoutBtn" style="display:none;" onclick="logoutYouTube()">
                  <i class="fas fa-sign-out-alt"></i> تسجيل الخروج
                </button>
              </div>
            </div>

            <!-- Cookie Source -->
            <div class="settings-row">
              <div class="row-info">
                <div class="row-icon" style="color: #ec4899; background: rgba(236, 72, 153, 0.12);">
                  <i class="fas fa-cookie-bite"></i>
                </div>
                <div class="row-texts">
                  <div class="row-title">مصدر الكوكيز (Cookies)</div>
                  <div class="row-desc" id="cookieSourceDesc">للمحتوى الخاص أو الذي يتطلب جلسة دخول</div>
                </div>
              </div>
              <div class="settings-control">
                <div class="custom-select-wrap">
                  <select class="select-dropdown" id="cookieSourceSelect">
                    <option value="none" selected>🚫 بدون كوكيز (افتراضي)</option>
                    <option value="youtube_login" id="youtubeLoginOption">🔴 حساب YouTube المسجل</option>
                    <option value="chrome">🌐 Google Chrome</option>
                    <option value="edge">🌐 Microsoft Edge</option>
                    <option value="firefox">🦊 Mozilla Firefox</option>
                    <option value="brave">🦁 Brave Browser</option>
                    <option value="opera">🔴 Opera</option>
                    <option value="file">📁 ملف كوكيز مخصص (.txt)</option>
                  </select>
                  <i class="fas fa-chevron-down select-chevron"></i>
                </div>
              </div>
            </div>

            <!-- Cookie File Row (Conditional) -->
            <div class="settings-row" id="cookieFileRow" style="display:none;">
              <div class="row-info">
                <div class="row-icon" style="color: #f59e0b; background: rgba(245, 158, 11, 0.12);">
                  <i class="fas fa-file-code"></i>
                </div>
                <div class="row-texts">
                  <div class="row-title">ملف الكوكيز المحدد</div>
                  <div class="storage-path-box">
                    <i class="fas fa-file-alt path-box-icon"></i>
                    <span class="path-text" id="cookieFileTxt">لم يتم اختيار ملف</span>
                  </div>
                </div>
              </div>
              <div class="settings-control">
                <button class="settings-action-btn amber-btn" id="pickCookieFileBtn">
                  <i class="fas fa-file-upload"></i> اختيار ملف
                </button>
              </div>
            </div>

            <!-- Proxy -->
            <div class="settings-row">
              <div class="row-info">
                <div class="row-icon" style="color: #6366f1; background: rgba(99, 102, 241, 0.12);">
                  <i class="fas fa-network-wired"></i>
                </div>
                <div class="row-texts">
                  <div class="row-title">البروكسي (Proxy اختياري)</div>
                  <div class="row-desc">مثال: http://127.0.0.1:8080 أو socks5://127.0.0.1:1080</div>
                </div>
              </div>
              <div class="settings-control">
                <div class="proxy-input-wrapper">
                  <i class="fas fa-globe proxy-prefix-icon"></i>
                  <input type="text" id="proxyInp" dir="ltr" placeholder="http://host:port" class="custom-proxy-input">
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Category 4: Performance & Speed (السرعة الفائقة والأداء) -->
        <div class="settings-card" data-category="performance">
          <div class="settings-section-title" style="padding: 14px 20px 6px 20px; margin: 0;">
            <i class="fas fa-bolt"></i> السرعة الفائقة والأداء
          </div>

          <div class="settings-items-list">
            <!-- Turbo Mode -->
            <div class="settings-row">
              <div class="row-info">
                <div class="row-icon" style="color: #f59e0b; background: rgba(245, 158, 11, 0.12);">
                  <i class="fas fa-rocket"></i>
                </div>
                <div class="row-texts">
                  <div class="row-title">وضع السرعة الفائقة (Turbo Mode)</div>
                  <div class="row-desc">تنزيل أجزاء الملف بالتوازي للوصول إلى أقصى طاقة اتصال</div>
                </div>
              </div>
              <div class="settings-control">
                <label class="toggle-switch">
                  <input type="checkbox" id="turboModeToggle" checked>
                  <span class="slider"></span>
                </label>
              </div>
            </div>

            <!-- Smart Live Detect -->
            <div class="settings-row">
              <div class="row-info">
                <div class="row-icon" style="color: #ef4444; background: rgba(239, 68, 68, 0.12);">
                  <i class="fas fa-satellite-dish"></i>
                </div>
                <div class="row-texts">
                  <div class="row-title">السماح بتنزيل البث المباشر</div>
                  <div class="row-desc">تسجيل البث المباشر من بدايته بدلاً من رفض الرابط</div>
                </div>
              </div>
              <div class="settings-control">
                <label class="toggle-switch">
                  <input type="checkbox" id="smartLiveDetectToggle" checked>
                  <span class="slider"></span>
                </label>
              </div>
            </div>

            <!-- Auto Update -->
            <div class="settings-row">
              <div class="row-info">
                <div class="row-icon" style="color: #06b6d4; background: rgba(6, 182, 212, 0.12);">
                  <i class="fas fa-sync-alt"></i>
                </div>
                <div class="row-texts">
                  <div class="row-title">التحديث التلقائي الدوري</div>
                  <div class="row-desc">إشعار فوري عند توفر تحديثات أمنية وتوافق المواقع</div>
                </div>
              </div>
              <div class="settings-control">
                <label class="toggle-switch">
                  <input type="checkbox" id="autoUpdateToggle" checked>
                  <span class="slider"></span>
                </label>
              </div>
            </div>

            <!-- Completion Alert Sound / Haptic -->
            <div class="settings-row">
              <div class="row-info">
                <div class="row-icon" style="color: #10b981; background: rgba(16, 185, 129, 0.12);">
                  <i class="fas fa-bell"></i>
                </div>
                <div class="row-texts">
                  <div class="row-title">تنبيه واهتزاز الاكتمال</div>
                  <div class="row-desc">إشعار هادئ عند اكتمال تنزيل الملف</div>
                </div>
              </div>
              <div class="settings-control">
                <label class="toggle-switch">
                  <input type="checkbox" id="soundToggle">
                  <span class="slider"></span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <!-- Category 5: System & Engine (معلومات النظام والمحرك) -->
        <div class="settings-card" data-category="system">
          <div class="settings-section-title" style="padding: 14px 20px 6px 20px; margin: 0;">
            <i class="fas fa-server"></i> حالة النظام ومحرّك التنزيل
          </div>

          <div class="system-hub-grid">
            <!-- App Version Tile -->
            <div class="system-tile">
              <div class="tile-info">
                <div class="tile-icon-wrap" style="color:#38bdf8; background:rgba(56, 189, 248, 0.12);">
                  <i class="fas fa-cube"></i>
                </div>
                <div class="row-texts">
                  <div class="tile-title">تطبيق SDN Downloader</div>
                  <div class="row-desc" id="settingsVersionTxt">SDN v1.0.32</div>
                </div>
              </div>
              <button class="system-btn primary-btn" id="checkUpdatesManualBtn">
                <i class="fas fa-redo-alt"></i> فحص التحديثات
              </button>
            </div>

            <!-- yt-dlp Engine Tile -->
            <div class="system-tile">
              <div class="tile-info">
                <div class="tile-icon-wrap" style="color:#10b981; background:rgba(16, 185, 129, 0.12);">
                  <i class="fas fa-microchip"></i>
                </div>
                <div class="row-texts">
                  <div class="tile-title">محرّك الاستخراج (yt-dlp)</div>
                  <div class="row-desc" id="engineVersionTxt">الإصدار: قيد الفحص...</div>
                </div>
              </div>
              <button class="system-btn emerald-btn" id="updateEngineBtn">
                <i class="fas fa-cloud-download-alt"></i> تحديث المحرك
              </button>
            </div>
          </div>
        </div>
      </div><!-- End settings-cards-grid -->
    </div><!-- End viewSettings -->"""

file_path = 'ui/index.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace CSS
css_start = content.find("/* ==========================================================================\n   ULTRA-SOFT, MINIMALIST & REFINED SETTINGS DESIGN SYSTEM")
css_end = content.find("/* Ultra-Clean, Soft, Minimalist Downloader Hub */")

if css_start == -1 or css_end == -1:
    print(f"Error locating CSS: start={css_start}, end={css_end}")
    sys.exit(1)

content = content[:css_start] + new_css + "\n" + content[css_end:]

# 2. Replace HTML
html_start = content.find('<div id="viewSettings" class="settings-panel">')
html_end = content.find('</div><!-- End viewSettings -->')

if html_start == -1 or html_end == -1:
    print(f"Error locating HTML: start={html_start}, end={html_end}")
    sys.exit(1)

html_end += len('</div><!-- End viewSettings -->')
content = content[:html_start] + new_html + content[html_end:]

# 3. Fix filterSettingsCategory functions
content = content.replace("card.style.display = 'flex';", "card.style.display = 'flex';\n      card.style.flexDirection = 'column';")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("100% Redesign successfully applied to ui/index.html!")
