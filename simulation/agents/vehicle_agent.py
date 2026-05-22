"""
vehicle_agent.py  (MOVEMENT FIX - DON'T TOUCH FUEL/STATE LOGIC)
================================================================
وكيل المركبة (Vehicle Agent)

[المنطق الأصلي]: لم يتغير شيء في:
  - حالات المركبة (moving, waiting, refueling)
  - استهلاك الوقود وneeds_fuel() وgo_to_gas_station() وrefuel()
  - تأثير الازدحام على السرعة
  - التفاعل مع نظام محطة الوقود

[منطق الحركة الجديد]:
  - حركة اتجاهية (أعلى/أسفل/يسار/يمين) على الطرق فقط
  - التحقق من الموقع التالي قبل التحرك (is_road)
  - تغيير الاتجاه فقط عند التقاطعات أو العوائق
  - لا تدخل المباني أو المستشفى أو محطة الوقود
  - حركة مستقيمة بدون اهتزاز (jitter)
  - الاتجاه البصري (angle) يتحدث تلقائياً من الاتجاه الحالي

كيف يعمل نظام الحركة الجديد؟
  1. المركبة تبدأ على بلاطة طريق عشوائية
  2. تختار اتجاهاً صالحاً من get_valid_directions() (طرق فقط)
  3. تتحرك في هذا الاتجاه بخطوات سلسة (speed * dt)
  4. عند كل خطوة: تحسب الموقع التالي ثم تتحقق من is_road()
  5. إذا كان الموقع التالي غير طريق: تبحث عن اتجاه جديد
  6. عند التقاطعات: احتمالية تغيير الاتجاه (أقل من الأشخاص)
  7. المركبات لا تنعطف إلا عند التقاطعات = حركة واقعية

لماذا المركبات أكثر صرامة من الأشخاص؟
  المركبات تسير على الطرق فقط (is_road) بينما الأشخاص يمكنهم
  المشي على الحدائق والمستشفى ومحطة الوقود أيضاً (is_walkable).
"""

import random
import math
import pygame

# --- حالات المركبة (لا تعديل) ---
STATE_MOVING    = "moving"     # تتحرك على الطريق
STATE_WAITING   = "waiting"    # في طابور محطة الوقود
STATE_REFUELING = "refueling"  # تُعبَّأ بالوقود

# --- أبعاد المركبة (لا تعديل) ---
VEHICLE_WIDTH  = 10
VEHICLE_HEIGHT = 6

# --- ألوان المركبات (لا تعديل) ---
VEHICLE_COLORS = [
    (255, 200,  50),   # أصفر
    (50,  150, 255),   # أزرق
    (255, 100,  50),   # برتقالي
    (200,  50, 200),   # بنفسجي
    (50,  220, 150),   # أخضر فاتح
]

# =====================================================
# ثوابت منطق الحركة الجديد
# =====================================================
# حجم البلاطة (يجب أن يتطابق مع city_map.TILE_SIZE)
_TILE_SIZE = 20

# سرعة المركبات بالبكسل/ثانية
VEHICLE_SPEED_MIN = 45.0
VEHICLE_SPEED_MAX = 85.0

# احتمالية تغيير الاتجاه عند التقاطع
# قيمة أقل = المركبة تكمل مسارها أكثر (حركة أكثر واقعية)
TURN_PROBABILITY = 0.40

# الحد الأقصى للبقاء عالقاً بالثواني قبل المحاذاة القسرية
MAX_STUCK_TIME = 1.0


class VehicleAgent:
    """
    وكيل المركبة: تتحرك على الطرق فقط وتتجه لمحطة الوقود عند نفاد الوقود.

    نظام الحركة:
      - كل مركبة لديها اتجاه حالي (dir_x, dir_y) مُطبَّع
      - تتحرك في هذا الاتجاه حتى تصل لعائق أو تقاطع
      - عند التقاطع: احتمالية تغيير الاتجاه
      - عند العائق: تغيير الاتجاه فوراً
      - الاتجاه البصري (angle) يُحسب من (dir_x, dir_y)
    """

    _id_counter = 0

    def __init__(self, city_map, world_state):
        VehicleAgent._id_counter += 1
        self.id = VehicleAgent._id_counter

        self.city_map    = city_map
        self.world_state = world_state

        # --- الموقع الابتدائي على طريق عشوائي ---
        start = city_map.get_random_road_tile()
        self.x = float(start[0])
        self.y = float(start[1])

        # --- الاتجاه البصري بالدرجات (للرسم) ---
        self.angle = 0.0

        # --- الاتجاه الحالي المُطبَّع (dir_x, dir_y) ---
        # القيم الممكنة: (0,-1) أعلى | (0,1) أسفل | (-1,0) يسار | (1,0) يمين
        self.dir_x = 0.0
        self.dir_y = 0.0
        self._choose_new_direction()

        # --- الوجهة (للتوافق مع الكود القديم وgo_to_gas_station) ---
        dest = city_map.get_random_road_tile()
        self.dest_x = float(dest[0])
        self.dest_y = float(dest[1])

        # --- السرعة ---
        self.base_speed = random.uniform(VEHICLE_SPEED_MIN, VEHICLE_SPEED_MAX)
        self.speed      = self.base_speed

        # --- الوقود (لا تعديل) ---
        self.fuel_level = random.uniform(0.3, 1.0)
        self.fuel_rate  = world_state.fuel_rate

        # --- الحالة (لا تعديل) ---
        self.state = STATE_MOVING

        # --- اللون (لا تعديل) ---
        self.color = random.choice(VEHICLE_COLORS)

        # --- مؤشر الانتظار في المحطة (لا تعديل) ---
        self.wait_timer   = 0.0
        self.service_time = random.uniform(5, 15)

        # --- هل المركبة في طابور المحطة؟ (لا تعديل) ---
        self.in_gas_queue = False

        # --- مؤقت العالق ---
        self._stuck_timer = 0.0

        # --- وضع التوجه لمحطة الوقود ---
        self._heading_to_gas = False

    # ==========================================================
    # دالة التحديث الرئيسية
    # ==========================================================

    def update(self, delta_time: float, congestion_level: float):
        """
        تحديث حالة المركبة في كل إطار.
        [لا تعديل]: منطق الوقود والازدحام والحالات.
        [جديد]: منطق الحركة الاتجاهية.
        """
        if self.world_state.paused or not self.world_state.running:
            return

        # --- الانتظار في طابور المحطة ---
        # [جديد]: عند waiting، تتحرك نحو موقع الطابور البصري
        if self.state == STATE_REFUELING:
            return
        if self.state == STATE_WAITING:
            # التحرك نحو موقع الطابور البصري (dest_x, dest_y)
            self._move_toward_dest(delta_time)
            return

        # --- تحديث الوقود (لا تعديل) ---
        self.fuel_level -= self.fuel_rate * delta_time * self.world_state.speed_factor
        self.fuel_level = max(0.0, self.fuel_level)

        # --- تعديل السرعة حسب الازدحام (لا تعديل) ---
        speed_multiplier = 1.0 - (congestion_level * 0.8)
        self.speed = self.base_speed * max(0.2, speed_multiplier)

        # --- الحركة الاتجاهية ---
        self._move_directional(delta_time)

    # ==========================================================
    # الحركة نحو الوجهة (للطابور البصري)
    # ==========================================================
    def _move_toward_dest(self, delta_time: float):
        """
        تحريك المركبة نحو dest_x/dest_y بسرعة محددة.
        يُستخدم لتحريك المركبة لموقع طابور محطة الوقود.
        لماذا؟ حتى تظهر السيارات واقفة في صف مرئي أمام المحطة.
        """
        spd  = self.base_speed * 0.5 * self.world_state.speed_factor
        dx   = self.dest_x - self.x
        dy   = self.dest_y - self.y
        dist = (dx**2 + dy**2) ** 0.5
        if dist < 3.0:
            self.x = self.dest_x
            self.y = self.dest_y
            return
        step   = min(spd * delta_time, dist)
        self.x += (dx / dist) * step
        self.y += (dy / dist) * step
        # تحديث الاتجاه البصري
        import math
        self.angle = math.degrees(math.atan2(dy, dx))

    # ==========================================================
    # منطق الحركة الاتجاهية الجديد
    # ==========================================================

    def _move_directional(self, delta_time: float):
        """
        تحريك المركبة بالاتجاه الحالي على الطرق فقط.

        خوارزمية الحركة:
        1. حساب الموقع التالي بناءً على الاتجاه الحالي والسرعة
        2. التحقق من صلاحية الموقع التالي (is_road)
        3. إذا صالح: التحرك إليه، وعند التقاطع احتمالية تغيير الاتجاه
        4. إذا غير صالح: اختيار اتجاه جديد فوراً

        كيف نمنع الاصطدام بالمباني؟
          is_road() تتحقق من أن البلاطة هي TILE_ROAD فقط.
          أي بلاطة أخرى (مبنى، مستشفى، محطة وقود) = غير صالحة للمركبة.
          المركبة لا تتحرك إلى الموقع غير الصالح أبداً.
        """
        step = self.speed * self.world_state.speed_factor * delta_time

        # --- حساب الموقع التالي ---
        next_x = self.x + self.dir_x * step
        next_y = self.y + self.dir_y * step

        # --- التحقق من صلاحية الموقع التالي ---
        # is_road: الطريق فقط = المركبات لا تدخل المباني أبداً
        if self.city_map.is_road(next_x, next_y):
            # الموقع صالح: التحرك
            self.x = next_x
            self.y = next_y
            self._stuck_timer = 0.0

            # --- تحديث الاتجاه البصري (angle) للرسم ---
            # نحسب الزاوية من الاتجاه الحالي لتجنب الاهتزاز البصري
            if self.dir_x != 0 or self.dir_y != 0:
                self.angle = math.degrees(math.atan2(self.dir_y, self.dir_x))

            # --- التحقق من التقاطع ---
            # المركبات لها احتمالية أقل من الأشخاص = مسارات أطول وأكثر واقعية
            if self.city_map.is_intersection(self.x, self.y):
                if random.random() < TURN_PROBABILITY:
                    self._choose_new_direction()
        else:
            # الموقع غير صالح: اختيار اتجاه جديد
            # لماذا نغير الاتجاه؟ لأن الاتجاه الحالي يؤدي إلى مبنى أو حدود
            self._stuck_timer += delta_time
            self._choose_new_direction(exclude_current=True)

            # إذا بقيت عالقة طويلاً: محاذاة قسرية مع أقرب طريق
            if self._stuck_timer >= MAX_STUCK_TIME:
                self._unstuck()

    def _choose_new_direction(self, exclude_current: bool = False):
        """
        اختيار اتجاه جديد صالح على الطريق من الموقع الحالي.

        كيف تعمل؟
          1. نحصل على قائمة الاتجاهات الصالحة (is_road للمركبات)
          2. إذا exclude_current=True: نستبعد الاتجاه الحالي
          3. نستبعد أيضاً الاتجاه المعاكس (لمنع الدوران المفاجئ 180 درجة)
          4. نختار اتجاهاً عشوائياً من القائمة

        لماذا نستبعد الاتجاه المعاكس؟
          لمنع المركبة من الدوران 180 درجة فجأة، مما يبدو غير واقعي.
        """
        # الاتجاهات الصالحة للمركبات (is_road فقط)
        valid_dirs = self.city_map.get_valid_directions(
            self.x, self.y, agent_type="vehicle"
        )

        if not valid_dirs:
            # لا توجد طرق: البقاء في مكانها
            return

        ts = _TILE_SIZE
        current  = (int(self.dir_x * ts), int(self.dir_y * ts))
        opposite = (int(-self.dir_x * ts), int(-self.dir_y * ts))

        if exclude_current and len(valid_dirs) > 1:
            # استبعاد الاتجاه الحالي (يؤدي إلى عائق)
            filtered = [d for d in valid_dirs
                        if (int(d[0]), int(d[1])) != current]
            if filtered:
                valid_dirs = filtered

        # استبعاد الاتجاه المعاكس إذا توفرت بدائل
        if len(valid_dirs) > 1:
            no_reverse = [d for d in valid_dirs
                          if (int(d[0]), int(d[1])) != opposite]
            if no_reverse:
                valid_dirs = no_reverse

        chosen = random.choice(valid_dirs)
        self.dir_x = chosen[0] / ts
        self.dir_y = chosen[1] / ts

    def _unstuck(self):
        """
        إخراج المركبة من حالة العالق بمحاذاتها مع أقرب بلاطة طريق.

        لماذا نحتاج هذه الدالة؟
          في حالات نادرة قد تقع المركبة بين بلاطتين.
          المحاذاة مع أقرب طريق تضمن استمرار الحركة.
        """
        nearest = self.city_map.get_nearest_road(self.x, self.y)
        self.x = float(nearest[0])
        self.y = float(nearest[1])
        self._stuck_timer = 0.0
        self._choose_new_direction()

    # ==========================================================
    # دوال الوقود ومحطة الوقود (لا تعديل في المنطق)
    # ==========================================================

    def needs_fuel(self) -> bool:
        """هل المركبة بحاجة إلى وقود؟ [لا تعديل]"""
        return self.fuel_level <= 0.15 and not self.in_gas_queue

    def go_to_gas_station(self):
        """
        توجيه المركبة نحو محطة الوقود.
        [تحديث]: تتجه نحو أقرب بلاطة طريق بجانب المحطة.
        """
        if self.city_map.gas_zone:
            gas_pos = random.choice(self.city_map.gas_zone)
            # إيجاد أقرب طريق لمنطقة المحطة
            nearest_road = self.city_map.get_nearest_road(
                float(gas_pos[0]), float(gas_pos[1])
            )
            self.dest_x = float(nearest_road[0])
            self.dest_y = float(nearest_road[1])
            self.in_gas_queue = True
            self._heading_to_gas = True
            # توجيه الاتجاه نحو المحطة
            valid = self.city_map.get_valid_directions(
                self.x, self.y, agent_type="vehicle"
            )
            if valid:
                ts = _TILE_SIZE
                # اختيار الاتجاه الذي يقرّب من الوجهة
                best = min(valid, key=lambda d: (
                    (self.x + d[0] - self.dest_x) ** 2 +
                    (self.y + d[1] - self.dest_y) ** 2
                ))
                self.dir_x = best[0] / ts
                self.dir_y = best[1] / ts

    def refuel(self):
        """تعبئة الوقود بالكامل. [لا تعديل]"""
        self.fuel_level = 1.0
        self.in_gas_queue = False
        self.state = STATE_MOVING
        self._heading_to_gas = False
        dest = self.city_map.get_random_road_tile()
        self.dest_x = float(dest[0])
        self.dest_y = float(dest[1])
        self._choose_new_direction()

    # ==========================================================
    # دالة الرسم (لا تعديل)
    # ==========================================================

    def draw(self, surface):
        """رسم المركبة كمستطيل مُدار حسب اتجاه الحركة. [لا تعديل]"""
        veh_surf = pygame.Surface((VEHICLE_WIDTH, VEHICLE_HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(veh_surf, self.color, (0, 0, VEHICLE_WIDTH, VEHICLE_HEIGHT))
        pygame.draw.rect(veh_surf, (200, 230, 255),
                         (VEHICLE_WIDTH - 4, 1, 3, VEHICLE_HEIGHT - 2))
        rotated = pygame.transform.rotate(veh_surf, -self.angle)
        rect = rotated.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(rotated, rect)
        # شريط الوقود
        bar_width  = VEHICLE_WIDTH
        bar_height = 2
        bar_x = int(self.x) - bar_width // 2
        bar_y = int(self.y) - VEHICLE_HEIGHT - 3
        pygame.draw.rect(surface, (80, 80, 80), (bar_x, bar_y, bar_width, bar_height))
        fuel_color = (0, 200, 0) if self.fuel_level > 0.3 else (255, 100, 0)
        pygame.draw.rect(surface, fuel_color,
                         (bar_x, bar_y, int(bar_width * self.fuel_level), bar_height))

    @classmethod
    def reset_counter(cls):
        """إعادة تعيين عداد المعرّفات. [لا تعديل]"""
        cls._id_counter = 0
