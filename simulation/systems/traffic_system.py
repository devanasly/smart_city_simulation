"""
traffic_system.py — نظام المرور الواقعي (الإصدار المُصلح)
============================================================

المشكلة التي تم إصلاحها:
    النموذج القديم كان يستخدم road_capacity = 618 × 0.15 = 92.7 مركبة،
    مما يجعل 60 مركبة (سكان=200) تعطي كثافة 64% فقط وازدحام ~17%.

الحل:
    استبدال نموذج BPR الخطي بدالة Sigmoid معدّلة تعطي نطاقاً واقعياً:
    - سكان=50   → ~35%  (تدفق حر)
    - سكان=100  → ~47%  (معتدل)
    - سكان=200  → ~74%  (ازدحام شديد)
    - سكان=500+ → ~90%+ (احتقار)

طبقات الحساب:
    1. دالة Sigmoid معدّلة على كثافة المركبات
    2. تأثير التقاطعات (يضيف ضغطاً عند الكثافة العالية)
    3. تأثير طابور الوقود (Spillback)
    4. تأثير الوباء (يقلل الحركة)
    5. تأثير ساعات الذروة
    6. معامل كثافة المرور من الإعدادات
    7. تمهيد EMA لمنع التغيير المفاجئ
"""

import math

# =====================================================
# ثوابت النموذج المُصلح
# =====================================================

# السعة الأساسية: عدد بلاطات الطريق / 10
# مع 618 بلاطة سعة = 61.8 مركبة
ROAD_CAPACITY_DIVISOR   = 10.0

# معاملات دالة Sigmoid
# k: حدة الانحدار
# x0: نقطة الانعطاف (الكثافة التي تعطي ~50% ازدحام)
SIGMOID_K               = 2.2
SIGMOID_X0              = 0.6

# معامل كثافة المرور من الإعدادات
# density=0.1 → factor=0.67، density=1.0 → factor=1.30
DENSITY_FACTOR_BASE     = 0.6
DENSITY_FACTOR_SCALE    = 0.7

# تأثير التقاطعات
INTERSECTION_EFFECT     = 0.12

# تأثير طابور الوقود
QUEUE_SPILLBACK_FACTOR  = 0.025

# تأثير الوباء على الحركة
EPIDEMIC_MOBILITY_REDUC = 0.35

# ساعات الذروة
PEAK_HOUR_MULTIPLIER    = 1.40
PEAK_HOURS = [
    (7 * 60,  9 * 60),   # ذروة الصباح
    (17 * 60, 19 * 60),  # ذروة المساء
]

# تمهيد EMA
EMA_ALPHA               = 0.10

# اقصى تأخير بالثواني
MAX_DELAY_SECONDS       = 180.0

# عتبات التسمية
THRESHOLD_FREE_FLOW     = 0.30
THRESHOLD_MODERATE      = 0.55
THRESHOLD_HEAVY         = 0.75


class TrafficSystem:
    """
    نظام المرور الواقعي — يستخدم دالة Sigmoid معدّلة
    لحساب الازدحام بناءً على كثافة المركبات الفعلية.
    """

    def __init__(self, world_state, city_map):
        self.world_state   = world_state
        self.city_map      = city_map

        # السعة الأساسية للطريق
        self.total_road_tiles = max(1, len(city_map.road_tiles))
        self.road_capacity    = self.total_road_tiles / ROAD_CAPACITY_DIVISOR

        # حساب عدد التقاطعات مرة واحدة عند التهيئة
        self._count_intersections()

        # حالة الازدحام
        self.congestion_level = 0.0
        self._raw_congestion  = 0.0
        self.avg_delay        = 0.0
        self._live_density    = 0.0
        self._is_peak_hour    = False
        self._flow_rate       = 0.0
        self._flow_counter    = 0
        self._flow_timer      = 0.0
        self._history         = []

    # ==========================================================
    # دالة التحديث الرئيسية
    # ==========================================================

    def update(self, vehicles: list, delta_time: float):
        """
        تحديث مستوى الازدحام في كل اطار.

        الخطوات:
        1. حساب الكثافة الفعلية (مركبات متحركة / سعة الطريق)
        2. تطبيق دالة Sigmoid لتحويل الكثافة الى نسبة ازدحام
        3. اضافة تأثيرات التقاطعات والطابور والوباء والذروة
        4. تطبيق معامل كثافة المرور من الاعدادات
        5. تمهيد EMA
        6. تحديث world_state
        """
        if not vehicles:
            self._apply_ema(0.0)
            self._update_world_state(vehicles)
            return

        # --- الطبقة 1: كثافة المركبات الفعلية ---
        moving_vehicles    = sum(1 for v in vehicles
                                 if getattr(v, "state", "moving") == "moving")
        self._live_density = moving_vehicles / self.road_capacity

        # --- الطبقة 2: دالة Sigmoid المعدّلة ---
        # sigmoid(d) = 1 / (1 + e^(-k * (d - x0)))
        # عند d=x0=0.6: base = 0.5 (50% ازدحام)
        d    = self._live_density
        base = 1.0 / (1.0 + math.exp(-SIGMOID_K * (d - SIGMOID_X0)))

        # --- الطبقة 3: تأثير التقاطعات ---
        inter_ratio = self._intersection_count / max(1, self.total_road_tiles)
        inter_boost = INTERSECTION_EFFECT * inter_ratio * (d ** 1.5)
        base        = min(1.0, base + inter_boost)

        # --- الطبقة 4: تأثير طابور الوقود (Queue Spillback) ---
        gas_queue = self.world_state.metrics.get("gas_queue_length", 0)
        spillback = min(0.12, gas_queue * QUEUE_SPILLBACK_FACTOR)
        base      = min(1.0, base + spillback)

        # --- الطبقة 5: تأثير الوباء على الحركة ---
        total_pop       = max(1, self.world_state.metrics.get("total_population", 1))
        infected        = self.world_state.metrics.get("infected", 0)
        infection_ratio = infected / total_pop
        epidemic_factor = max(0.25, 1.0 - infection_ratio * EPIDEMIC_MOBILITY_REDUC)
        base           *= epidemic_factor

        # --- الطبقة 6: تأثير ساعات الذروة ---
        sim_minutes        = self.world_state.simulation_time
        day_minutes        = sim_minutes % (24 * 60)
        self._is_peak_hour = any(s <= day_minutes <= e for s, e in PEAK_HOURS)
        if self._is_peak_hour:
            base = min(1.0, base * PEAK_HOUR_MULTIPLIER)

        # --- الطبقة 7: معامل كثافة المرور من الاعدادات ---
        # traffic_density=0.1 → factor=0.67
        # traffic_density=0.85 → factor=1.20
        # traffic_density=1.0  → factor=1.30
        density_factor = DENSITY_FACTOR_BASE + self.world_state.traffic_density * DENSITY_FACTOR_SCALE
        base           = min(1.0, base * density_factor)

        # --- التمهيد الزمني بـ EMA ---
        self._raw_congestion = base
        self._apply_ema(base)

        # --- حساب التأخير الواقعي ---
        c              = self.congestion_level
        self.avg_delay = MAX_DELAY_SECONDS * (c ** 2.0)

        # --- معدل التدفق ---
        self._flow_timer   += delta_time
        self._flow_counter += moving_vehicles
        if self._flow_timer >= 60.0:
            self._flow_rate    = self._flow_counter / self._flow_timer
            self._flow_counter = 0
            self._flow_timer   = 0.0

        self._history.append(self.congestion_level)
        if len(self._history) > 300:
            self._history.pop(0)

        self._update_world_state(vehicles)

    # ==========================================================
    # دوال مساعدة
    # ==========================================================

    def _apply_ema(self, raw: float):
        """تطبيق التمهيد الزمني بـ EMA لمنع التغيير المفاجئ."""
        self.congestion_level = (
            EMA_ALPHA * raw + (1.0 - EMA_ALPHA) * self.congestion_level
        )
        self.congestion_level = max(0.0, min(1.0, self.congestion_level))

    def _count_intersections(self):
        """حساب عدد التقاطعات (بلاطات طريق لها 3+ جيران طرق)."""
        from simulation.engine.city_map import TILE_SIZE, TILE_ROAD
        count = 0
        for tx, ty in self.city_map.road_tiles:
            col = tx // TILE_SIZE
            row = ty // TILE_SIZE
            neighbors = sum(
                1 for dc, dr in [(0, 1), (0, -1), (1, 0), (-1, 0)]
                if (0 <= row + dr < self.city_map.grid.shape[0] and
                    0 <= col + dc < self.city_map.grid.shape[1] and
                    self.city_map.grid[row + dr][col + dc] == TILE_ROAD)
            )
            if neighbors >= 3:
                count += 1
        self._intersection_count = count

    def _update_world_state(self, vehicles: list):
        """تحديث جميع مقاييس المرور في الحالة العالمية."""
        ws = self.world_state
        ws.metrics["traffic_congestion"]   = round(self.congestion_level, 3)
        ws.metrics["traffic_avg_delay"]    = round(self.avg_delay, 1)
        ws.metrics["traffic_density_live"] = round(self._live_density, 3)
        ws.metrics["traffic_peak_hour"]    = 1 if self._is_peak_hour else 0
        ws.metrics["traffic_flow_rate"]    = round(self._flow_rate, 1)
        ws.metrics["traffic_moving_count"] = sum(
            1 for v in vehicles if getattr(v, "state", "moving") == "moving"
        )
        c = self.congestion_level
        if c < THRESHOLD_FREE_FLOW:
            label = "Free Flow"
        elif c < THRESHOLD_MODERATE:
            label = "Moderate"
        elif c < THRESHOLD_HEAVY:
            label = "Heavy"
        else:
            label = "Gridlock"
        ws.metrics["traffic_label"] = label

    # ==========================================================
    # واجهة عامة
    # ==========================================================

    def get_congestion_level(self) -> float:
        """ارجاع مستوى الازدحام الحالي المُمهَّد (0.0 - 1.0)."""
        return self.congestion_level

    def get_congestion_label(self) -> str:
        """ارجاع وصف نصي لمستوى الازدحام."""
        c = self.congestion_level
        if c < THRESHOLD_FREE_FLOW:
            return "Free Flow"
        elif c < THRESHOLD_MODERATE:
            return "Moderate"
        elif c < THRESHOLD_HEAVY:
            return "Heavy"
        else:
            return "Gridlock"

    def get_speed_factor(self) -> float:
        """
        ارجاع معامل السرعة للمركبات بناءً على الازدحام.
        congestion=0.0 → 1.0 (سرعة كاملة)
        congestion=0.5 → 0.50
        congestion=1.0 → 0.10 (حركة زحف)
        """
        return max(0.10, (1.0 - self.congestion_level) ** 1.5)

    def draw_congestion_overlay(self, surface):
        """
        رسم طبقة تصورية للازدحام على الخريطة.
        اخضر = تدفق حر، اصفر = معتدل، احمر = احتقار.
        """
        import pygame
        if self.congestion_level < 0.05:
            return
        from simulation.engine.city_map import TILE_SIZE
        alpha = int(self.congestion_level * 100)
        c = self.congestion_level
        if c < 0.5:
            r, g = int(c * 2 * 255), 200
        else:
            r, g = 255, int((1.0 - c) * 2 * 200)
        overlay_color = (r, g, 0, alpha)
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for tile in self.city_map.road_tiles:
            col = tile[0] // TILE_SIZE
            row = tile[1] // TILE_SIZE
            rect = pygame.Rect(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(overlay, overlay_color, rect)
        surface.blit(overlay, (0, 0))
