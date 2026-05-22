"""
gas_station_system.py  (v5 - VISUAL QUEUE + SYSTEM INTEGRATION)
================================================================
نظام محطة الوقود المُطوَّر مع الطابور البصري الحقيقي

الطابور البصري:
  - مواقع انتظار محددة مسبقاً على الطريق أمام المحطة
  - السيارات تتوقف فعلياً في مواقع الطابور (state=waiting)
  - كل سيارة تتحرك لموقع محدد في الصف عند الانضمام
  - عندما تُخدَم السيارة الأولى، تتقدم الباقية خطوة للأمام

التفاعل مع الأنظمة:
  - طول الطابور يُؤثر على traffic_congestion (ازدحام إضافي)
  - السيارات في الطابور لا تتحرك (mobility=0) = أقل حركة في المدينة
"""
from collections import deque
import random
import math

class GasStationSystem:
    """
    نظام محطة الوقود: طابور FIFO بصري مع مواقع انتظار محددة.
    """

    def __init__(self, world_state, city_map):
        self.world_state = world_state
        self.city_map    = city_map

        # طابور الانتظار (FIFO)
        self.queue: deque = deque()

        # المركبة التي تُخدَم حالياً
        self.current_vehicle = None
        self.service_timer   = 0.0

        # إحصاءات
        self.total_served    = 0
        self.total_wait_time = 0.0
        self._wait_times     = []
        self._entry_times    = {}

        # مواقع الطابور البصري (صف من النقاط أمام المحطة)
        self.queue_positions = []
        self._setup_queue_positions(city_map)

    def _setup_queue_positions(self, city_map):
        """
        إعداد مواقع الطابور البصري أمام مدخل محطة الوقود.
        الطابور يمتد للأسفل من مدخل المحطة على الطريق.

        لماذا على الطريق؟
          السيارات تسير على الطرق فقط، لذا مواقع الطابور
          يجب أن تكون على بلاطات طريق مجاورة للمحطة.
        """
        if not city_map.gas_rect:
            return

        gx, gy, gw, gh = city_map.gas_rect
        # مدخل المحطة: منتصف الحافة اليمينية (الطريق المجاور)
        entrance_x = gx + gw + 10
        entrance_y = gy + gh / 2

        # 8 مواقع انتظار في صف أفقي على الطريق
        for i in range(8):
            qx = entrance_x + i * 22
            qy = entrance_y
            self.queue_positions.append((qx, qy))

    # ==========================================================
    # إضافة مركبة للطابور
    # ==========================================================
    def add_to_queue(self, vehicle):
        """
        إضافة مركبة للطابور وتوجيهها لموقع انتظار محدد.
        [جديد]: المركبة تتوقف في موقع بصري محدد في الصف.
        """
        if vehicle not in self.queue and vehicle != self.current_vehicle:
            vehicle.state      = "waiting"
            vehicle.in_gas_queue = True
            self.queue.append(vehicle)
            self._entry_times[vehicle.id] = self.world_state.simulation_time

            # توجيه المركبة لموقعها في الطابور
            idx = len(self.queue) - 1
            if idx < len(self.queue_positions):
                qx, qy = self.queue_positions[idx]
                vehicle.dest_x = qx
                vehicle.dest_y = qy
            elif self.queue_positions:
                vehicle.dest_x, vehicle.dest_y = self.queue_positions[-1]

            self._update_world_state()

    # ==========================================================
    # التحديث الرئيسي
    # ==========================================================
    def update(self, delta_time: float):
        """
        تحديث نظام محطة الوقود.
        [جديد]: تحديث مواقع الطابور البصري بعد كل خدمة.
        """
        if self.world_state.paused or not self.world_state.running:
            return

        # إذا لا توجد مركبة تُخدَم، خذ التالية من الطابور
        if self.current_vehicle is None and self.queue:
            self.current_vehicle = self.queue.popleft()
            self.current_vehicle.state = "refueling"
            self.service_timer = 0.0
            self.current_vehicle.service_time = random.uniform(15, 35)

            # إعادة ترتيب مواقع الطابور بعد إزالة الأول
            self._reorder_queue_positions()

        # خدمة المركبة الحالية
        if self.current_vehicle is not None:
            self.service_timer += delta_time * self.world_state.speed_factor
            if self.service_timer >= self.current_vehicle.service_time:
                wait_time = (
                    self.world_state.simulation_time
                    - self._entry_times.get(
                        self.current_vehicle.id,
                        self.world_state.simulation_time
                    )
                )
                self._wait_times.append(wait_time)
                if len(self._wait_times) > 100:
                    self._wait_times.pop(0)
                self.total_served += 1
                self.current_vehicle.refuel()
                self.current_vehicle = None
                self.service_timer   = 0.0

        self._update_world_state()

    def _reorder_queue_positions(self):
        """
        إعادة ترتيب مواقع الطابور البصري بعد مغادرة مركبة.
        كل مركبة تتقدم خطوة للأمام في الصف.
        """
        for i, vehicle in enumerate(self.queue):
            if i < len(self.queue_positions):
                qx, qy = self.queue_positions[i]
                vehicle.dest_x = qx
                vehicle.dest_y = qy

    # ==========================================================
    # فحص المركبات
    # ==========================================================
    def check_vehicles(self, vehicles: list):
        """
        فحص المركبات التي تحتاج وقوداً وإضافتها للطابور فوراً.
        """
        for vehicle in vehicles:
            if vehicle.needs_fuel():
                self.add_to_queue(vehicle)

    # ==========================================================
    # تحديث المقاييس
    # ==========================================================
    def _update_world_state(self):
        """تحديث مقاييس محطة الوقود في الحالة العالمية."""
        queue_len = len(self.queue) + (1 if self.current_vehicle else 0)
        self.world_state.metrics["gas_queue_length"] = queue_len
        avg_wait = (
            sum(self._wait_times) / len(self._wait_times)
            if self._wait_times else 0.0
        )
        self.world_state.metrics["gas_avg_wait"]     = round(avg_wait, 2)
        self.world_state.metrics["gas_total_served"] = self.total_served

        # [الربط الحقيقي]: الطابور الطويل يُضيف ازدحاماً
        # كل 5 سيارات في الطابور = +0.05 ازدحام إضافي
        extra_congestion = min(0.3, queue_len * 0.01)
        self.world_state.metrics["gas_congestion_contribution"] = extra_congestion

    def get_queue_positions(self):
        """إرجاع مواقع الطابور البصري للرسم."""
        return self.queue_positions

    def get_queue_list(self):
        """إرجاع قائمة المركبات في الطابور للرسم."""
        return list(self.queue)

    def reset(self):
        """إعادة تهيئة النظام."""
        self.queue           = deque()
        self.current_vehicle = None
        self.service_timer   = 0.0
        self.total_served    = 0
        self._wait_times     = []
        self._entry_times    = {}
