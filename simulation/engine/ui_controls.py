"""
ui_controls.py  (VISUAL REDESIGN - DON'T TOUCH LOGIC)
======================================================
واجهة التحكم في نافذة Pygame

[المنطق]: لم يتغير أي شيء في منطق معالجة الأحداث أو تحديث WorldState.
[البصريات]: أُعيد تصميم الواجهة بالكامل:
  - لوحة جانبية يمينية (250px) بدلاً من شريط سفلي
  - أزرار مستطيلة محسّنة مع تأثير hover وactive
  - عرض مقاييس حية مع أشرطة تقدم ملونة
  - لوحة ألوان متسقة (رمادي مزرق داكن + نصوص بيضاء)
  - مؤشر حالة المحاكاة (يعمل/متوقف) مع لون ديناميكي
"""
import pygame

# =====================================================
# لوحة الألوان  (بصريات فقط)
# =====================================================
# --- ألوان اللوحة الجانبية ---
COLOR_PANEL_BG      = ( 22,  30,  48)   # رمادي مزرق داكن جداً - خلفية اللوحة
COLOR_PANEL_BORDER  = ( 50,  70, 110)   # أزرق رمادي - حد اللوحة
COLOR_PANEL_SECTION = ( 30,  42,  65)   # أزرق داكن - خلفية الأقسام
COLOR_PANEL_DIVIDER = ( 45,  60,  90)   # خط فاصل بين الأقسام

# --- ألوان النصوص ---
COLOR_TEXT_TITLE    = (180, 210, 255)   # أزرق فاتح - عناوين
COLOR_TEXT_LABEL    = (140, 165, 200)   # رمادي مزرق - تسميات
COLOR_TEXT_VALUE    = (230, 240, 255)   # أبيض مزرق - قيم
COLOR_TEXT_WHITE    = (255, 255, 255)   # أبيض - نصوص الأزرار

# --- ألوان الأزرار ---
COLOR_BTN_RESUME    = ( 30, 130,  60)   # أخضر - Resume
COLOR_BTN_RESUME_H  = ( 45, 170,  80)   # أخضر فاتح - hover
COLOR_BTN_RESUME_A  = ( 20,  90,  40)   # أخضر داكن - active
COLOR_BTN_PAUSE     = (180, 130,  20)   # ذهبي - Pause
COLOR_BTN_PAUSE_H   = (220, 165,  30)   # ذهبي فاتح - hover
COLOR_BTN_PAUSE_A   = (130,  90,  10)   # ذهبي داكن - active
COLOR_BTN_RESET     = (160,  35,  35)   # أحمر - Reset
COLOR_BTN_RESET_H   = (200,  50,  50)   # أحمر فاتح - hover
COLOR_BTN_RESET_A   = (110,  20,  20)   # أحمر داكن - active
COLOR_BTN_SPEED     = ( 40,  60, 100)   # أزرق - Speed
COLOR_BTN_SPEED_H   = ( 60,  90, 145)   # أزرق فاتح - hover
COLOR_BTN_SPEED_A   = ( 80, 140, 220)   # أزرق ساطع - active

# --- ألوان أشرطة التقدم ---
COLOR_BAR_BG        = ( 35,  45,  70)   # خلفية الشريط
COLOR_BAR_INFECTED  = (220,  60,  60)   # أحمر - مصابون
COLOR_BAR_RECOVERED = ( 50, 180,  80)   # أخضر - متعافون
COLOR_BAR_HOSPITAL  = (220, 160,  30)   # ذهبي - مستشفى
COLOR_BAR_GAS       = (240, 200,  50)   # أصفر - وقود
COLOR_BAR_TRAFFIC   = (160,  80, 220)   # بنفسجي - مرور

# --- ألوان مؤشر الحالة ---
COLOR_STATUS_RUN    = ( 50, 200,  80)   # أخضر - يعمل
COLOR_STATUS_PAUSE  = (220, 160,  30)   # ذهبي - متوقف

# =====================================================
# ثوابت أبعاد اللوحة الجانبية  (بصريات)
# =====================================================
SIDEBAR_WIDTH  = 250
SIDEBAR_X      = 1000   # يبدأ بعد منطقة المدينة (1000px)
SIDEBAR_Y      = 0
SIDEBAR_HEIGHT = 700    # ارتفاع النافذة الكامل


class Button:
    """
    زر مستطيل محسّن مع تأثيرات hover وactive.
    [المنطق]: نفس واجهة handle_event() - لم يتغير.
    [البصريات]: ألوان ديناميكية، إطار، نص متمركز.
    """

    def __init__(self, x: int, y: int, w: int, h: int, text: str,
                 color=(40, 60, 100),
                 hover_color=(60, 90, 145),
                 active_color=(80, 140, 220)):
        self.rect         = pygame.Rect(x, y, w, h)
        self.text         = text
        self.color        = color
        self.hover_color  = hover_color
        self.active_color = active_color
        self.is_hovered   = False
        self.is_active    = False
        # الخط - يُهيَّأ عند أول استخدام
        self._font = None

    def _get_font(self):
        """تهيئة الخط عند الحاجة (lazy initialization)."""
        if self._font is None:
            try:
                self._font = pygame.font.SysFont("Arial", 12, bold=True)
            except Exception:
                self._font = pygame.font.Font(None, 14)
        return self._font

    def draw(self, surface):
        """
        رسم الزر مع تأثيرات hover وactive.
        [الألوان]:
          - عادي: اللون الأساسي
          - hover: لون أفتح
          - active: لون مختلف يدل على الحالة الفعّالة
        """
        # اختيار اللون حسب الحالة
        if self.is_active:
            bg_color = self.active_color
        elif self.is_hovered:
            bg_color = self.hover_color
        else:
            bg_color = self.color

        # رسم خلفية الزر
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=5)

        # إطار الزر
        border_color = (min(255, bg_color[0] + 40),
                        min(255, bg_color[1] + 40),
                        min(255, bg_color[2] + 40))
        pygame.draw.rect(surface, border_color, self.rect, 1, border_radius=5)

        # ظل خفيف في الأسفل
        shadow_rect = pygame.Rect(self.rect.x + 1, self.rect.y + 1,
                                  self.rect.w - 2, self.rect.h - 2)
        pygame.draw.rect(surface, (0, 0, 0, 60), shadow_rect, 1, border_radius=4)

        # نص الزر
        font = self._get_font()
        text_surf = font.render(self.text, True, COLOR_TEXT_WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def handle_event(self, event) -> bool:
        """
        معالجة أحداث الماوس. [لا تعديل في المنطق]
        يُعيد True إذا تم النقر على الزر.
        """
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                return True
        return False


class UIControls:
    """
    لوحة التحكم الكاملة في نافذة Pygame.
    [المنطق]: نفس منطق handle_events() وupdate() - لم يتغير.
    [البصريات]: أُعيد تصميم اللوحة كشريط جانبي أيمن احترافي.

    هيكل اللوحة الجانبية:
    ┌─────────────────────┐
    │  Smart City Sim     │  ← عنوان
    ├─────────────────────┤
    │  [حالة المحاكاة]    │  ← مؤشر يعمل/متوقف
    ├─────────────────────┤
    │  الوقت              │  ← معلومات الجلسة
    │  السكان             │
    ├─────────────────────┤
    │  [SIR bars]         │  ← أشرطة الوباء
    ├─────────────────────┤
    │  المستشفى           │  ← شريط إشغال
    │  الطابور            │  ← شريط الطابور
    │  الازدحام           │  ← شريط المرور
    ├─────────────────────┤
    │  [Resume] [Pause]   │  ← أزرار التحكم
    │  [Reset]            │
    ├─────────────────────┤
    │  [x1][x2][x5][x10]  │  ← أزرار السرعة
    └─────────────────────┘
    """

    # ثوابت اللوحة الجانبية (تُستخدم في main.py أيضاً)
    PANEL_X      = SIDEBAR_X
    PANEL_Y      = SIDEBAR_Y
    PANEL_WIDTH  = SIDEBAR_WIDTH
    PANEL_HEIGHT = SIDEBAR_HEIGHT

    def __init__(self, world_state):
        self.world_state = world_state
        self._init_fonts()
        self._init_buttons()
        # مؤقت تحديث اللقطات (لا تعديل في المنطق)
        self._last_snapshot_time = 0.0
        self._snapshot_interval  = 1.0

    def _init_fonts(self):
        """تهيئة الخطوط المستخدمة في اللوحة."""
        try:
            self.font_title  = pygame.font.SysFont("Arial", 14, bold=True)
            self.font_label  = pygame.font.SysFont("Arial", 11)
            self.font_value  = pygame.font.SysFont("Arial", 13, bold=True)
            self.font_small  = pygame.font.SysFont("Arial", 10)
            self.font_status = pygame.font.SysFont("Arial", 12, bold=True)
        except Exception:
            self.font_title  = pygame.font.Font(None, 16)
            self.font_label  = pygame.font.Font(None, 12)
            self.font_value  = pygame.font.Font(None, 14)
            self.font_small  = pygame.font.Font(None, 11)
            self.font_status = pygame.font.Font(None, 13)

    def _init_buttons(self):
        """
        إنشاء أزرار التحكم داخل اللوحة الجانبية.
        [المنطق]: نفس الأزرار وnفس الخصائص - فقط المواقع والألوان تغيرت.
        """
        px = SIDEBAR_X + 10   # هامش أيسر داخل اللوحة
        bw = (SIDEBAR_WIDTH - 30) // 2   # عرض الزر (نصف اللوحة)
        bh = 32

        # --- صف أول: Resume و Pause ---
        y1 = 490
        self.btn_resume = Button(
            px, y1, bw, bh, "Resume",
            color=COLOR_BTN_RESUME,
            hover_color=COLOR_BTN_RESUME_H,
            active_color=COLOR_BTN_RESUME_A
        )
        self.btn_pause = Button(
            px + bw + 10, y1, bw, bh, "Pause",
            color=COLOR_BTN_PAUSE,
            hover_color=COLOR_BTN_PAUSE_H,
            active_color=COLOR_BTN_PAUSE_A
        )

        # --- صف ثانٍ: Reset ---
        y2 = y1 + bh + 8
        self.btn_reset = Button(
            px, y2, SIDEBAR_WIDTH - 20, bh, "Reset Simulation",
            color=COLOR_BTN_RESET,
            hover_color=COLOR_BTN_RESET_H,
            active_color=COLOR_BTN_RESET_A
        )

        # --- صف ثالث: أزرار السرعة ---
        y3 = y2 + bh + 16
        speeds = [("x1", 1), ("x2", 2), ("x5", 5), ("x10", 10)]
        sbw = (SIDEBAR_WIDTH - 30) // 4   # عرض كل زر سرعة
        self.speed_buttons = []
        for i, (label, factor) in enumerate(speeds):
            btn = Button(
                px + i * (sbw + 4), y3, sbw, 28, label,
                color=COLOR_BTN_SPEED,
                hover_color=COLOR_BTN_SPEED_H,
                active_color=COLOR_BTN_SPEED_A
            )
            btn.speed_factor = factor
            if factor == self.world_state.speed_factor:
                btn.is_active = True
            self.speed_buttons.append(btn)

    # ==========================================================
    # معالجة الأحداث  (لا تعديل في المنطق)
    # ==========================================================
    def handle_events(self, events) -> str:
        """
        معالجة أحداث الواجهة. [لا تعديل في المنطق]
        يُعيد اسم الإجراء: 'resume', 'pause', 'reset', 'speed', أو ''.
        """
        action = ""
        for event in events:
            if self.btn_resume.handle_event(event):
                action = "resume"
            elif self.btn_pause.handle_event(event):
                action = "pause"
            elif self.btn_reset.handle_event(event):
                action = "reset"
            else:
                for btn in self.speed_buttons:
                    if btn.handle_event(event):
                        for b in self.speed_buttons:
                            b.is_active = False
                        btn.is_active = True
                        self.world_state.speed_factor = btn.speed_factor
                        action = "speed"
                        break
        # تحديث حالة أزرار Resume/Pause
        self.btn_resume.is_active = not self.world_state.paused
        self.btn_pause.is_active  = self.world_state.paused
        return action

    # ==========================================================
    # دالة الرسم الرئيسية  (بصريات فقط)
    # ==========================================================
    def draw(self, surface):
        """
        رسم اللوحة الجانبية الكاملة.
        [البنية]:
          - خلفية اللوحة الجانبية
          - عنوان النظام
          - مؤشر الحالة (يعمل/متوقف)
          - معلومات الجلسة والوقت
          - مقاييس الوباء (SIR) مع أشرطة
          - مقاييس الخدمات (مستشفى، وقود، مرور)
          - أزرار التحكم
          - أزرار السرعة
        """
        # --- خلفية اللوحة الجانبية ---
        panel_surf = pygame.Surface((SIDEBAR_WIDTH, SIDEBAR_HEIGHT))
        panel_surf.fill(COLOR_PANEL_BG)
        surface.blit(panel_surf, (SIDEBAR_X, SIDEBAR_Y))

        # --- حد اللوحة (خط عمودي أيسر) ---
        pygame.draw.line(surface, COLOR_PANEL_BORDER,
                         (SIDEBAR_X, 0), (SIDEBAR_X, SIDEBAR_HEIGHT), 2)

        # --- رسم الأقسام ---
        y_cursor = 12
        y_cursor = self._draw_header(surface, y_cursor)
        y_cursor = self._draw_status_badge(surface, y_cursor)
        y_cursor = self._draw_session_info(surface, y_cursor)
        y_cursor = self._draw_sir_metrics(surface, y_cursor)
        y_cursor = self._draw_service_metrics(surface, y_cursor)
        self._draw_legend(surface, y_cursor)

        # --- رسم الأزرار ---
        self.btn_resume.draw(surface)
        self.btn_pause.draw(surface)
        self.btn_reset.draw(surface)
        for btn in self.speed_buttons:
            btn.draw(surface)

        # --- تسمية قسم السرعة ---
        spd_label = self.font_small.render("Simulation Speed", True, COLOR_TEXT_LABEL)
        surface.blit(spd_label, (SIDEBAR_X + 10, 572))

    # ----------------------------------------------------------
    # دوال رسم الأقسام  (بصريات فقط)
    # ----------------------------------------------------------

    def _draw_header(self, surface, y: int) -> int:
        """رسم عنوان النظام في أعلى اللوحة."""
        # خلفية العنوان
        pygame.draw.rect(surface, COLOR_PANEL_SECTION,
                         (SIDEBAR_X, y - 4, SIDEBAR_WIDTH, 36))

        title = self.font_title.render("Smart City Sim", True, COLOR_TEXT_TITLE)
        surface.blit(title, (SIDEBAR_X + 10, y))

        subtitle = self.font_small.render("نظام محاكاة المدينة الذكية", True, COLOR_TEXT_LABEL)
        surface.blit(subtitle, (SIDEBAR_X + 10, y + 18))

        self._draw_divider(surface, y + 36)
        return y + 50

    def _draw_status_badge(self, surface, y: int) -> int:
        """
        رسم مؤشر حالة المحاكاة (يعمل/متوقف).
        [الألوان]: أخضر = يعمل، ذهبي = متوقف.
        """
        ws = self.world_state
        if ws.paused:
            status_text  = "  PAUSED"
            status_color = COLOR_STATUS_PAUSE
            dot_color    = COLOR_STATUS_PAUSE
        else:
            status_text  = "  RUNNING"
            status_color = COLOR_STATUS_RUN
            dot_color    = COLOR_STATUS_RUN

        # خلفية المؤشر
        badge_rect = pygame.Rect(SIDEBAR_X + 10, y, SIDEBAR_WIDTH - 20, 26)
        bg_color = (20, 50, 20) if not ws.paused else (50, 40, 10)
        pygame.draw.rect(surface, bg_color, badge_rect, border_radius=4)
        pygame.draw.rect(surface, status_color, badge_rect, 1, border_radius=4)

        # نقطة ملونة
        pygame.draw.circle(surface, dot_color,
                           (SIDEBAR_X + 22, y + 13), 5)

        # نص الحالة
        status_surf = self.font_status.render(status_text, True, status_color)
        surface.blit(status_surf, (SIDEBAR_X + 30, y + 6))

        # سرعة المحاكاة على اليمين
        spd_text = f"x{ws.speed_factor}"
        spd_surf = self.font_value.render(spd_text, True, COLOR_TEXT_LABEL)
        surface.blit(spd_surf, (SIDEBAR_X + SIDEBAR_WIDTH - spd_surf.get_width() - 12, y + 6))

        self._draw_divider(surface, y + 32)
        return y + 44

    def _draw_session_info(self, surface, y: int) -> int:
        """رسم معلومات الجلسة والوقت."""
        ws = self.world_state

        self._draw_section_title(surface, y, "Session Info")
        y += 18

        # الوقت
        self._draw_metric_row(surface, y,
                              "Sim Time:",
                              ws.get_sim_time_display(),
                              COLOR_TEXT_VALUE)
        y += 18

        # معرّف الجلسة (مختصر)
        sid = ws.session_id.replace("session_", "")[:12]
        self._draw_metric_row(surface, y, "Session ID:", sid, COLOR_TEXT_LABEL)
        y += 18

        # --- قسم السكان والمواليد والوفيات ---
        # [بصريات]: عرض عدد السكان ثم بطاقتي المواليد والوفيات بجانب بعض
        pop    = ws.metrics.get("total_population", 0)
        births = ws.metrics.get("total_births", 0)
        deaths = ws.metrics.get("total_deaths", 0)

        # عدد السكان الكلي
        self._draw_metric_row(surface, y, "Population:", str(pop), COLOR_TEXT_VALUE)
        y += 18

        # --- بطاقتا المواليد والوفيات في صف واحد ---
        # [الألوان]: أخضر داكن للمواليد، أحمر داكن للوفيات
        bx = SIDEBAR_X + 10
        bw = (SIDEBAR_WIDTH - 20) // 2 - 4

        # بطاقة المواليد (أخضر)
        pygame.draw.rect(surface, (15, 45, 20),
                         (bx, y, bw, 28), border_radius=4)
        pygame.draw.rect(surface, (40, 140, 60),
                         (bx, y, bw, 28), 1, border_radius=4)
        b_icon = self.font_small.render("+ Births", True, (80, 200, 100))
        b_val  = self.font_value.render(str(births), True, (120, 230, 140))
        surface.blit(b_icon, (bx + 5, y + 3))
        surface.blit(b_val,  (bx + bw - b_val.get_width() - 5, y + 12))

        # بطاقة الوفيات (أحمر)
        dx = bx + bw + 8
        pygame.draw.rect(surface, (45, 15, 15),
                         (dx, y, bw, 28), border_radius=4)
        pygame.draw.rect(surface, (160, 40, 40),
                         (dx, y, bw, 28), 1, border_radius=4)
        d_icon = self.font_small.render("- Deaths", True, (220, 80, 80))
        d_val  = self.font_value.render(str(deaths), True, (240, 120, 120))
        surface.blit(d_icon, (dx + 5, y + 3))
        surface.blit(d_val,  (dx + bw - d_val.get_width() - 5, y + 12))

        y += 34
        self._draw_divider(surface, y + 4)
        return y + 14

    def _draw_sir_metrics(self, surface, y: int) -> int:
        """
        رسم مقاييس نموذج SIR مع أشرطة تقدم ملونة.
        [الألوان]: أزرق=S، أحمر=I، أخضر=R.
        """
        ws  = self.world_state
        m   = ws.metrics
        pop = max(1, m.get("total_population", 1))

        S = m.get("susceptible", pop)
        I = m.get("infected",    0)
        R = m.get("recovered",   0)

        self._draw_section_title(surface, y, "Epidemic (SIR)")
        y += 18

        bar_data = [
            ("Susceptible (S)", S, pop, (70, 130, 220)),
            ("Infected (I)",    I, pop, COLOR_BAR_INFECTED),
            ("Recovered (R)",   R, pop, COLOR_BAR_RECOVERED),
        ]
        for label, val, total, color in bar_data:
            self._draw_progress_bar(surface, y, label, val, total, color)
            y += 22

        self._draw_divider(surface, y + 2)
        return y + 12

    def _draw_service_metrics(self, surface, y: int) -> int:
        """
        رسم مقاييس الخدمات (مستشفى، وقود، مرور) مع أشرطة.
        """
        ws = self.world_state
        m  = ws.metrics

        self._draw_section_title(surface, y, "City Services")
        y += 18

        # إشغال المستشفى
        hosp_occ = m.get("hospital_occupancy", 0)
        hosp_cap = max(1, ws.hospital_capacity)
        self._draw_progress_bar(surface, y, "Hospital",
                                hosp_occ, hosp_cap, COLOR_BAR_HOSPITAL,
                                suffix=f"{hosp_occ}/{hosp_cap}")
        y += 22

        # طابور محطة الوقود
        gas_q = m.get("gas_queue_length", 0)
        self._draw_progress_bar(surface, y, "Gas Queue",
                                min(gas_q, 20), 20, COLOR_BAR_GAS,
                                suffix=str(gas_q))
        y += 22

        # ازدحام المرور
        cong = m.get("traffic_congestion", 0.0)
        self._draw_progress_bar(surface, y, "Traffic",
                                int(cong * 100), 100, COLOR_BAR_TRAFFIC,
                                suffix=f"{cong:.0%}")
        y += 22

        self._draw_divider(surface, y + 2)
        return y + 12

    def _draw_legend(self, surface, y: int):
        """رسم مفتاح الألوان للوكلاء."""
        self._draw_section_title(surface, y, "Agent Legend")
        y += 18
        legend = [
            ("Susceptible", (70, 130, 220)),
            ("Infected",    (220,  60,  60)),
            ("Recovered",   ( 50, 180,  80)),
            ("Vehicle",     (200, 200,  80)),
        ]
        for i, (lbl, color) in enumerate(legend):
            lx = SIDEBAR_X + 10 + (i % 2) * 115
            ly = y + (i // 2) * 16
            pygame.draw.circle(surface, color, (lx + 5, ly + 6), 5)
            txt = self.font_small.render(lbl, True, COLOR_TEXT_LABEL)
            surface.blit(txt, (lx + 14, ly))

    # ----------------------------------------------------------
    # دوال مساعدة للرسم  (بصريات فقط)
    # ----------------------------------------------------------

    def _draw_section_title(self, surface, y: int, title: str):
        """رسم عنوان قسم."""
        txt = self.font_label.render(title.upper(), True, COLOR_TEXT_TITLE)
        surface.blit(txt, (SIDEBAR_X + 10, y))

    def _draw_metric_row(self, surface, y: int, label: str, value: str, val_color):
        """رسم صف مقياس (تسمية + قيمة)."""
        lbl_surf = self.font_label.render(label, True, COLOR_TEXT_LABEL)
        val_surf = self.font_value.render(value, True, val_color)
        surface.blit(lbl_surf, (SIDEBAR_X + 10, y))
        surface.blit(val_surf, (SIDEBAR_X + SIDEBAR_WIDTH - val_surf.get_width() - 10, y))

    def _draw_progress_bar(self, surface, y: int, label: str,
                           value: int, total: int,
                           bar_color: tuple, suffix: str = None):
        """
        رسم شريط تقدم مع تسمية وقيمة.
        [الألوان]: خلفية رمادية داكنة + لون الشريط حسب المقياس.
        """
        bar_x  = SIDEBAR_X + 10
        bar_w  = SIDEBAR_WIDTH - 20
        bar_h  = 8
        lbl_h  = 11

        # تسمية
        lbl_surf = self.font_small.render(label, True, COLOR_TEXT_LABEL)
        surface.blit(lbl_surf, (bar_x, y))

        # قيمة على اليمين
        val_str  = suffix if suffix else str(value)
        val_surf = self.font_small.render(val_str, True, COLOR_TEXT_VALUE)
        surface.blit(val_surf, (bar_x + bar_w - val_surf.get_width(), y))

        # شريط التقدم
        bar_y = y + lbl_h
        # خلفية الشريط
        pygame.draw.rect(surface, COLOR_BAR_BG,
                         (bar_x, bar_y, bar_w, bar_h), border_radius=3)
        # ملء الشريط
        if total > 0:
            fill_w = int(bar_w * min(value, total) / total)
            if fill_w > 0:
                pygame.draw.rect(surface, bar_color,
                                 (bar_x, bar_y, fill_w, bar_h), border_radius=3)
        # إطار الشريط
        pygame.draw.rect(surface, COLOR_PANEL_DIVIDER,
                         (bar_x, bar_y, bar_w, bar_h), 1, border_radius=3)

    def _draw_divider(self, surface, y: int):
        """رسم خط فاصل أفقي."""
        pygame.draw.line(surface, COLOR_PANEL_DIVIDER,
                         (SIDEBAR_X + 8, y),
                         (SIDEBAR_X + SIDEBAR_WIDTH - 8, y), 1)

    # ==========================================================
    # تحديث المؤقت  (لا تعديل في المنطق)
    # ==========================================================
    def update(self, delta_time: float):
        """تحديث مؤقت تسجيل اللقطات. [لا تعديل في المنطق]"""
        self._last_snapshot_time += delta_time
        if self._last_snapshot_time >= self._snapshot_interval:
            self._last_snapshot_time = 0.0
            self.world_state.record_snapshot()
