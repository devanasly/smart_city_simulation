"""
person_agent.py  (v5 - FULL SYSTEM INTEGRATION)
================================================
وكيل الشخص المُطوَّر مع دعم الطابور البصري

التغييرات الجديدة (بدون المساس بمنطق الوباء):
  - in_hospital_queue: الشخص في طابور انتظار المستشفى
  - عند in_hospital_queue=True: الشخص يتحرك نحو dest_x/dest_y (موقع الطابور)
  - عند in_hospital=True: الشخص يتحرك ببطء داخل المستشفى
  - عند الحالة الطبيعية: الحركة الاتجاهية المعتادة
"""
import random
import math
import pygame

# --- ثوابت حالات الوباء (لا تعديل) ---
STATE_SUSCEPTIBLE = "S"
STATE_INFECTED    = "I"
STATE_RECOVERED   = "R"

# --- ألوان الحالات ---
STATE_COLORS = {
    STATE_SUSCEPTIBLE: (0,   180, 255),
    STATE_INFECTED:    (255,  50,  50),
    STATE_RECOVERED:   (50,  200,  50),
}

PERSON_RADIUS      = 4
INFECTION_DISTANCE = 25.0
BASE_RECOVERY_RATE = 0.001

# ثوابت الحركة
_TILE_SIZE       = 20
PERSON_SPEED_MIN = 25.0
PERSON_SPEED_MAX = 55.0
TURN_PROBABILITY = 0.55
MAX_STUCK_TIME   = 1.5


class PersonAgent:
    """
    وكيل الشخص: يتحرك اتجاهياً ويدعم الطابور البصري أمام المستشفى.
    """
    _id_counter = 0

    def __init__(self, city_map, world_state):
        PersonAgent._id_counter += 1
        self.id = PersonAgent._id_counter
        self.city_map    = city_map
        self.world_state = world_state

        start    = city_map.get_random_road_tile()
        self.x   = float(start[0])
        self.y   = float(start[1])

        self.speed           = random.uniform(PERSON_SPEED_MIN, PERSON_SPEED_MAX)
        self.mobility_factor = world_state.mobility_factor

        self.dir_x = 0.0
        self.dir_y = 0.0
        self._choose_new_direction()
        self._stuck_timer = 0.0

        # --- الحالة الوبائية (لا تعديل) ---
        if random.random() < 0.05:
            self.state = STATE_INFECTED
            self.infection_timer = 0.0
        else:
            self.state = STATE_SUSCEPTIBLE
            self.infection_timer = 0.0

        self.infection_duration = random.uniform(2000, 8000)

        # --- حالة المستشفى ---
        self.in_hospital       = False
        self.in_hospital_queue = False   # [جديد]: في طابور الانتظار

        # --- الوجهة (تُستخدم من hospital_system لتوجيه الطابور) ---
        self.dest_x = self.x
        self.dest_y = self.y

    # ==========================================================
    # التحديث الرئيسي
    # ==========================================================
    def update(self, delta_time: float):
        """
        تحديث الشخص في كل إطار.
        منطق الحركة:
          1. إذا in_hospital_queue: يتحرك نحو dest_x/dest_y (موقع الطابور)
          2. إذا in_hospital: يتحرك ببطء داخل المستشفى
          3. غير ذلك: الحركة الاتجاهية الحرة
        """
        if self.world_state.paused or not self.world_state.running:
            return

        # --- تحديث حالة الإصابة (لا تعديل) ---
        if self.state == STATE_INFECTED:
            self.infection_timer += delta_time * self.world_state.speed_factor
            if self.infection_timer >= self.infection_duration:
                self.state             = STATE_RECOVERED
                self.in_hospital       = False
                self.in_hospital_queue = False

        # --- الحركة حسب الحالة ---
        if self.in_hospital_queue:
            # [جديد]: التحرك نحو موقع الطابور
            self._move_toward_dest(delta_time, speed_override=30.0)
        elif self.in_hospital:
            # داخل المستشفى: حركة بطيئة جداً
            self._move_toward_dest(delta_time, speed_override=10.0)
        else:
            # الحركة الاتجاهية الحرة
            self._move_directional(delta_time)

    # ==========================================================
    # الحركة نحو الوجهة (للطابور والمستشفى)
    # ==========================================================
    def _move_toward_dest(self, delta_time: float, speed_override: float = None):
        """
        التحرك نحو dest_x/dest_y بسرعة محددة.
        يُستخدم لتحريك الشخص لموقع طابور المستشفى.
        """
        spd = (speed_override or self.speed) * self.world_state.speed_factor
        dx  = self.dest_x - self.x
        dy  = self.dest_y - self.y
        dist = math.hypot(dx, dy)

        if dist < 2.0:
            # وصل للوجهة: يقف
            self.x = self.dest_x
            self.y = self.dest_y
            return

        step = min(spd * delta_time, dist)
        self.x += (dx / dist) * step
        self.y += (dy / dist) * step

    # ==========================================================
    # الحركة الاتجاهية الحرة
    # ==========================================================
    def _move_directional(self, delta_time: float):
        """
        تحريك الشخص بالاتجاه الحالي مع التحقق المسبق من الصلاحية.
        """
        effective_speed = (self.speed
                           * self.mobility_factor
                           * self.world_state.speed_factor)
        step   = effective_speed * delta_time
        next_x = self.x + self.dir_x * step
        next_y = self.y + self.dir_y * step

        if self.city_map.is_walkable(next_x, next_y):
            self.x = next_x
            self.y = next_y
            self._stuck_timer = 0.0
            if self.city_map.is_intersection(self.x, self.y):
                if random.random() < TURN_PROBABILITY:
                    self._choose_new_direction()
        else:
            self._stuck_timer += delta_time
            self._choose_new_direction(exclude_current=True)
            if self._stuck_timer >= MAX_STUCK_TIME:
                self._unstuck()

    def _choose_new_direction(self, exclude_current: bool = False):
        valid_dirs = self.city_map.get_valid_directions(
            self.x, self.y, agent_type="person"
        )
        if not valid_dirs:
            return
        if exclude_current and len(valid_dirs) > 1:
            ts      = _TILE_SIZE
            current = (int(self.dir_x * ts), int(self.dir_y * ts))
            filtered = [d for d in valid_dirs
                        if (int(d[0]), int(d[1])) != current]
            if filtered:
                valid_dirs = filtered
        chosen     = random.choice(valid_dirs)
        ts         = _TILE_SIZE
        self.dir_x = chosen[0] / ts
        self.dir_y = chosen[1] / ts

    def _unstuck(self):
        nearest    = self.city_map.get_nearest_road(self.x, self.y)
        self.x     = float(nearest[0])
        self.y     = float(nearest[1])
        self._stuck_timer = 0.0
        self._choose_new_direction()

    # ==========================================================
    # التفاعل الوبائي (لا تعديل)
    # ==========================================================
    def try_infect(self, other: 'PersonAgent', infection_rate: float):
        if self.state != STATE_INFECTED:
            return
        if other.state != STATE_SUSCEPTIBLE:
            return
        dist = math.hypot(self.x - other.x, self.y - other.y)
        if dist <= INFECTION_DISTANCE:
            effective_rate = infection_rate * other.mobility_factor
            if random.random() < effective_rate * 0.01:
                other.state              = STATE_INFECTED
                other.infection_timer    = 0.0
                other.infection_duration = random.uniform(2000, 8000)

    # ==========================================================
    # الرسم
    # ==========================================================
    def draw(self, surface):
        """رسم الشخص كدائرة ملونة حسب حالته."""
        color = STATE_COLORS.get(self.state, (200, 200, 200))
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), PERSON_RADIUS)
        if self.state == STATE_INFECTED:
            pygame.draw.circle(surface, (255, 150, 0),
                               (int(self.x), int(self.y)), PERSON_RADIUS + 2, 1)

    @classmethod
    def reset_counter(cls):
        cls._id_counter = 0
