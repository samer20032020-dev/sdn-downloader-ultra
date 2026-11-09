import sys
sys.stdout.reconfigure(encoding='utf-8')

css_content = """/* ==========================================================================
   ULTRA-SOFT, MINIMALIST & REFINED SETTINGS DESIGN SYSTEM
   ========================================================================== */

.settings-panel {
  display: none;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  max-width: 820px;
  margin: 0 auto;
  animation: fadeInSettings 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
.settings-panel.active {
  display: flex;
}

@keyframes fadeInSettings {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ── Minimalist Clean Header ── */
.settings-header-clean {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 6px 8px 6px;
}
.settings-header-info {
  display: flex;
  align-items: center;
  gap: 12px;
}
.settings-header-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: rgba(56, 189, 248, 0.12);
  color: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.15rem;
  box-shadow: 0 0 20px rgba(56, 189, 248, 0.15);
}
.settings-title-main {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--text-main);
  letter-spacing: -0.02em;
  margin: 0;
}
.settings-subtitle-main {
  font-size: 0.8rem;
  color: var(--text-sub);
  margin-top: 2px;
}

/* ── Category Filter Pills ── */
.settings-filter-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow-x: auto;
  padding: 2px 2px 6px 2px;
  scrollbar-width: none;
}
.settings-filter-bar::-webkit-scrollbar { display: none; }
.settings-filter-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 9999px;
  font-size: 0.8rem;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-sub);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.07);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}
.settings-filter-pill:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-main);
  transform: translateY(-1px);
}
.settings-filter-pill.active {
  background: rgba(56, 189, 248, 0.14);
  border-color: rgba(56, 189, 248, 0.35);
  color: #38bdf8;
  box-shadow: 0 2px 10px rgba(56, 189, 248, 0.15);
}

/* ── Group Card ── */
.settings-cards-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.settings-card {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 18px;
  overflow: hidden;
  backdrop-filter: blur(20px);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.settings-card:hover {
  border-color: rgba(255, 255, 255, 0.12);
}

.settings-card-header {
  padding: 14px 18px 10px 18px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}
.card-icon {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
  flex-shrink: 0;
}
.card-title {
  font-size: 0.94rem;
  font-weight: 700;
  color: var(--text-main);
  margin: 0;
}
.card-desc {
  font-size: 0.76rem;
  color: var(--text-sub);
  margin-top: 2px;
}

/* ── Setting Rows ── */
.settings-items-list {
  display: flex;
  flex-direction: column;
}
.settings-row, .settings-item-row {
  padding: 13px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.035);
  transition: background 0.15s ease;
}
.settings-row:last-child, .settings-item-row:last-child {
  border-bottom: none;
}
.settings-row:hover, .settings-item-row:hover {
  background: rgba(255, 255, 255, 0.018);
}
.row-info, .settings-label {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}
.row-icon, .item-icon-box {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  flex-shrink: 0;
}
.row-texts {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.row-title, .settings-title {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text-main);
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.row-desc, .settings-desc {
  font-size: 0.76rem;
  color: var(--text-sub);
  margin-top: 2px;
  line-height: 1.4;
}

/* ── Soft Badges & Pills ── */
.soft-badge, .item-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 7px;
  border-radius: 6px;
  font-size: 0.68rem;
  font-weight: 600;
  background: rgba(56, 189, 248, 0.1);
  color: var(--primary);
  border: 1px solid rgba(56, 189, 248, 0.2);
}

/* ── Soft Spring Toggle Switch ── */
.toggle-switch, .soft-switch {
  position: relative;
  display: inline-block;
  width: 42px;
  height: 24px;
  flex-shrink: 0;
  cursor: pointer;
}
.toggle-switch input, .soft-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.slider, .soft-slider {
  position: absolute;
  inset: 0;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 9999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: all 0.28s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.slider:before, .soft-slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 2px;
  bottom: 2px;
  background: #ffffff;
  border-radius: 50%;
  transition: all 0.28s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.25);
}
.toggle-switch input:checked + .slider,
.soft-switch input:checked + .soft-slider {
  background: #0284c7;
  border-color: #38bdf8;
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.35);
}
.toggle-switch input:checked + .slider:before,
.soft-switch input:checked + .soft-slider:before {
  transform: translateX(18px);
}

/* ── Soft Select Dropdowns ── */
.custom-select-wrap, .soft-select-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
}
.select-dropdown, .soft-select {
  appearance: none;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.09);
  color: var(--text-main);
  padding: 6px 28px 6px 12px;
  border-radius: 10px;
  font-size: 0.82rem;
  font-family: inherit;
  font-weight: 600;
  cursor: pointer;
  outline: none;
  transition: all 0.2s ease;
  min-width: 150px;
}
.select-dropdown:hover, .soft-select:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(56, 189, 248, 0.4);
}
.select-dropdown:focus, .soft-select:focus {
  border-color: var(--primary);
  box-shadow: 0 0 10px var(--primary-glow);
}
.select-chevron {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.7rem;
  color: var(--muted);
  pointer-events: none;
}

/* ── Path Display Box ── */
.storage-path-box, .soft-path-box {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(0, 0, 0, 0.22);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 9px;
  padding: 5px 10px;
  max-width: 260px;
  overflow: hidden;
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
.path-box-icon {
  font-size: 0.8rem;
  color: var(--muted);
  flex-shrink: 0;
}

/* ── Action Buttons ── */
.settings-action-btn, .settings-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 10px;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.2s ease;
  border: none;
  outline: none;
  white-space: nowrap;
}
.settings-action-btn.primary-glow-btn, .settings-btn.primary {
  background: linear-gradient(135deg, #0284c7, #38bdf8);
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(56, 189, 248, 0.25);
}
.settings-action-btn.primary-glow-btn:hover, .settings-btn.primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(56, 189, 248, 0.35);
}
.settings-action-btn.amber-btn {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.3);
}
.settings-action-btn.amber-btn:hover {
  background: rgba(245, 158, 11, 0.25);
}
.settings-btn.secondary {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-main);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.settings-btn.secondary:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.16);
}
.settings-btn.danger, .yt-logout-btn {
  background: rgba(244, 63, 94, 0.12);
  color: #f43f5e;
  border: 1px solid rgba(244, 63, 94, 0.25);
  padding: 7px 14px;
  border-radius: 10px;
  font-weight: 700;
  font-size: 0.8rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}
.settings-btn.danger:hover, .yt-logout-btn:hover {
  background: rgba(244, 63, 94, 0.2);
}

/* ── YouTube Account Row ── */
.youtube-vip-banner {
  padding: 14px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: rgba(239, 68, 68, 0.04);
  border-bottom: 1px solid rgba(255, 255, 255, 0.035);
}
.yt-account-info {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  flex: 1;
}
.yt-icon-box {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.15rem;
  position: relative;
  flex-shrink: 0;
}
.yt-live-pulse, .yt-dot {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 6px #10b981;
}
.yt-status-badge {
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 9999px;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-sub);
}
.yt-status-badge.active {
  background: rgba(16, 185, 129, 0.14);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
}
.yt-desc-text {
  font-size: 0.76rem;
  color: var(--text-sub);
  margin-top: 3px;
  line-height: 1.4;
}
.yt-buttons-area {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.yt-login-btn {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: #fff;
  border: none;
  padding: 7px 16px;
  border-radius: 10px;
  font-weight: 700;
  font-size: 0.8rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.25);
  transition: all 0.2s ease;
}
.yt-login-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(239, 68, 68, 0.35);
}

/* ── Proxy Input ── */
.proxy-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}
.custom-proxy-input {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 6px 12px 6px 28px;
  color: var(--text-main);
  font-size: 0.8rem;
  font-family: monospace;
  outline: none;
  transition: all 0.2s ease;
  direction: ltr;
  width: 210px;
}
.custom-proxy-input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 10px var(--primary-glow);
}
.proxy-prefix-icon {
  position: absolute;
  left: 9px;
  font-size: 0.75rem;
  color: var(--muted);
  pointer-events: none;
}

/* ── System Status Tiles ── */
.system-hub-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  padding: 14px 18px;
}
@media (max-width: 580px) {
  .system-hub-grid { grid-template-columns: 1fr; }
}
.system-tile {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 14px;
  padding: 12px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  transition: all 0.2s ease;
}
.system-tile:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.08);
}
.tile-info {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.tile-icon-wrap {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  flex-shrink: 0;
}
.tile-title {
  font-size: 0.86rem;
  font-weight: 700;
  color: var(--text-main);
}
.system-btn {
  padding: 5px 12px;
  border-radius: 8px;
  font-size: 0.76rem;
  font-weight: 700;
  border: none;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  transition: all 0.2s;
  white-space: nowrap;
}
.system-btn.primary-btn {
  background: rgba(56, 189, 248, 0.12);
  color: var(--primary);
  border: 1px solid rgba(56, 189, 248, 0.25);
}
.system-btn.primary-btn:hover {
  background: rgba(56, 189, 248, 0.22);
}
.system-btn.emerald-btn {
  background: rgba(16, 185, 129, 0.12);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.25);
}
.system-btn.emerald-btn:hover {
  background: rgba(16, 185, 129, 0.22);
}

/* ── Light Mode Overrides ── */
body.light-theme .settings-header-icon {
  background: rgba(2, 132, 199, 0.1);
  color: var(--primary);
}
body.light-theme .settings-filter-pill {
  background: rgba(0, 0, 0, 0.035);
  border-color: rgba(0, 0, 0, 0.08);
  color: #475569;
}
body.light-theme .settings-filter-pill:hover {
  background: rgba(0, 0, 0, 0.06);
  color: #0f172a;
}
body.light-theme .settings-filter-pill.active {
  background: rgba(2, 132, 199, 0.1);
  border-color: rgba(2, 132, 199, 0.3);
  color: #0284c7;
}
body.light-theme .settings-card {
  background: rgba(255, 255, 255, 0.94);
  border-color: rgba(15, 23, 42, 0.08);
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.03);
}
body.light-theme .settings-card-header {
  border-bottom-color: rgba(0, 0, 0, 0.05);
}
body.light-theme .settings-row,
body.light-theme .settings-item-row {
  border-bottom-color: rgba(0, 0, 0, 0.04);
}
body.light-theme .settings-row:hover,
body.light-theme .settings-item-row:hover {
  background: rgba(0, 0, 0, 0.015);
}
body.light-theme .slider,
body.light-theme .soft-slider {
  background: rgba(0, 0, 0, 0.12);
  border-color: rgba(0, 0, 0, 0.1);
}
body.light-theme .select-dropdown,
body.light-theme .soft-select,
body.light-theme .custom-proxy-input {
  background: rgba(0, 0, 0, 0.035);
  border-color: rgba(0, 0, 0, 0.1);
  color: #0f172a;
}
body.light-theme .storage-path-box,
body.light-theme .soft-path-box {
  background: rgba(0, 0, 0, 0.04);
  border-color: rgba(0, 0, 0, 0.08);
}
body.light-theme .system-tile {
  background: rgba(0, 0, 0, 0.02);
  border-color: rgba(0, 0, 0, 0.06);
}
body.light-theme .youtube-vip-banner {
  background: rgba(239, 68, 68, 0.03);
  border-bottom-color: rgba(0, 0, 0, 0.05);
}
"""

html_content = """    <div id="viewSettings" class="settings-panel">
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

      <!-- Category Filter Pills -->
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
          <div class="settings-card-header">
            <div class="card-icon" style="background: rgba(56, 189, 248, 0.12); color: #38bdf8;">
              <i class="fas fa-palette"></i>
            </div>
            <div>
              <h3 class="card-title">المظهر والواجهة</h3>
              <p class="card-desc">السمة البصرية وجودة التنزيل الافتراضية ومعدل السرعة</p>
            </div>
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
          <div class="settings-card-header">
            <div class="card-icon" style="background: rgba(16, 185, 129, 0.12); color: #10b981;">
              <i class="fas fa-hdd"></i>
            </div>
            <div>
              <h3 class="card-title">التخزين والملفات والحافظة</h3>
              <p class="card-desc">تحديد مسار حفظ التنزيلات وسلوك فحص الحافظة التلقائي</p>
            </div>
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
                  <div class="storage-path-box">
                    <i class="fas fa-folder-open path-box-icon"></i>
                    <span class="path-text" id="savePathTxt">Downloads</span>
                  </div>
                </div>
              </div>
              <div class="settings-control">
                <button class="settings-action-btn primary-glow-btn" id="changeFolderBtn">
                  <i class="fas fa-folder-plus"></i> تغيير المجلد
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
          <div class="settings-card-header">
            <div class="card-icon" style="background: rgba(239, 68, 68, 0.12); color: #ef4444;">
              <i class="fab fa-youtube"></i>
            </div>
            <div>
              <h3 class="card-title">حساب YouTube والكوكيز</h3>
              <p class="card-desc">تخطي القيود العمرية (18+)، تنزيل المشاهدة لاحقاً، وتجاوز الحجب</p>
            </div>
          </div>

          <div class="settings-items-list">
            <!-- YouTube Account Row -->
            <div class="youtube-vip-banner" id="youtubeLoginRow">
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
          <div class="settings-card-header">
            <div class="card-icon" style="background: rgba(245, 158, 11, 0.12); color: #f59e0b;">
              <i class="fas fa-bolt"></i>
            </div>
            <div>
              <h3 class="card-title">السرعة والأداء والإشعارات</h3>
              <p class="card-desc">تسريع النقل المتوازي، تسجيل البث، والتنبيهات</p>
            </div>
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
                <div class="row-icon" style="color: #38bdf8; background: rgba(56, 189, 248, 0.12);">
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
          <div class="settings-card-header">
            <div class="card-icon" style="background: rgba(99, 102, 241, 0.12); color: #6366f1;">
              <i class="fas fa-server"></i>
            </div>
            <div>
              <h3 class="card-title">حالة النظام ومحرّك التنزيل</h3>
              <p class="card-desc">معلومات النسخة ومحرك الاستخراج والفحص اليدوي للتحديثات</p>
            </div>
          </div>

          <div class="system-hub-grid">
            <!-- App Version Tile -->
            <div class="system-tile">
              <div class="tile-info">
                <div class="tile-icon-wrap" style="color:#38bdf8; background:rgba(56, 189, 248, 0.1);">
                  <i class="fas fa-cube"></i>
                </div>
                <div class="row-texts">
                  <div class="tile-title">برنامج SDN Downloader</div>
                  <div class="row-desc" id="settingsVersionTxt">SDN v1.0.30</div>
                </div>
              </div>
              <button class="system-btn primary-btn" id="checkUpdatesManualBtn">
                <i class="fas fa-redo-alt"></i> فحص التحديثات
              </button>
            </div>

            <!-- yt-dlp Engine Tile -->
            <div class="system-tile">
              <div class="tile-info">
                <div class="tile-icon-wrap" style="color:#10b981; background:rgba(16, 185, 129, 0.1);">
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
css_start_marker = "/* ==========================================================================\n   ULTRA-SOFT, ORGANIC & REFINED SETTINGS DESIGN SYSTEM"
css_end_marker = "/* Ultra-Clean, Soft, Minimalist Downloader Hub */"

pos_css_start = content.find(css_start_marker)
pos_css_end = content.find(css_end_marker)

if pos_css_start == -1 or pos_css_end == -1:
    print(f"Error: CSS markers not found! start={pos_css_start}, end={pos_css_end}")
    sys.exit(1)

content = content[:pos_css_start] + css_content + "\n" + content[pos_css_end:]

# 2. Replace HTML
html_start_marker = '<div id="viewSettings" class="settings-panel">'
html_end_marker = '</div><!-- End viewSettings -->'

pos_html_start = content.find(html_start_marker)
pos_html_end = content.find(html_end_marker)

if pos_html_start == -1 or pos_html_end == -1:
    print(f"Error: HTML markers not found! start={pos_html_start}, end={pos_html_end}")
    sys.exit(1)

pos_html_end += len(html_end_marker)
content = content[:pos_html_start] + html_content + content[pos_html_end:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully replaced settings CSS and HTML in ui/index.html!")
