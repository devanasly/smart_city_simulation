"""
hospital_system.py  (v5 - FULL SYSTEM INTEGRATION)
===================================================
نظام المستشفى المُطوَّر مع الطابور البصري الحقيقي

التفاعلات الجديدة:
  1. hospital → epidemic:  المعالجة تُسرّع التعافي (تُعلَم epidemic_system)
  2. hospital → persons:   المرضى يُوجَّهون لمواقع طابور محددة أمام المستشفى
  3. hospital → world_state: إشغال المستشفى يُؤثر على معدل الوفاة في epidemic

الطابور البصري:
  - مواقع انتظار محددة مسبقاً أمام المستشفى (صف من النقاط)
  - كل مريض في الطابور يُوجَّه لموقع محدد في الصف
  - عندما يُقبل مريض، يتقدم الباقون خطوة للأمام
"""
import math
from collections import deque

class HospitalSystem:
    """
    نظام المستشفى المُطوَّر: طابور بصري حقيقي + تفاعل مع epidemic_system.
    """

    def __init__(self, world_state, city_map):
        self.world_state = world_state
        self.city_map    = city_map

        # الطاقة الاستيعابية
        self.capacity = world_state.hospital_capacity

        # المرضى المقبولون داخل المستشفى
        self.admitted_patients = []

        # طابور الانتظار (FIFO) - الأشخاص ينتظرون خارج المستشفى
        self.waiting_queue: deque = deque()

        # عداد الحالات المرفوضة
        self.rejected_count = 0

        # مسافة الاستقبال (بالبكسل)
        self.admission_radius = 80.0

        # موقع مركز المستشفى
        self.center_x = 0.0
        self.center_y = 0.0

        # موقع مدخل المستشفى (أسفل المستشفى = نقطة الطابور)
        self.entrance_x = 0.0
        self.entrance_y = 0.0

        # مواقع الطابور البصري (صف من النقاط أمام المدخل)
        self.queue_positions = []

        self._setup_positions(city_map)

        # مؤقت للتحديث الدوري
        self._update_interval = 1.0
        self._timer = 0.0

    def _setup_positions(self, city_map):
        """
        إعداد مواقع الطابور البصري أمام مدخل المستشفى.
        الطابور يمتد للأسفل من مدخل المستشفى بخطوات 18px.
        """
        if not city_map.hospital_rect:
            return

        hx, hy, hw, hh = city_map.hospital_rect
        self.center_x   = hx + hw / 2
        self.center_y   = hy + hh / 2

        # المدخل: منتصف الحافة السفلية للمستشفى
        self.entrance_x = hx + hw / 2
        self.entrance_y = hy + hh + 10  # 10px أسفل المستشفى

        # 12 موقع انتظار في صف عمودي أمام المدخل
        for i in range(12):
            qx = self.entrance_x
            qy = self.entrance_y + i * 18
            self.queue_positions.append((qx, qy))

    # ==========================================================
    # التحديث الرئيسي
    # ==========================================================
    def update(self, persons: list, delta_time: float):
        """
        تحديث نظام المستشفى.
        [جديد]: المصابون يُضافون لطابور الانتظار أولاً ثم يُقبلون تدريجياً.
        [جديد]: المرضى في الطابور يتوجهون لمواقع محددة (طابور بصري).
        """
        if self.world_state.paused or not self.world_state.running:
            return

        self.capacity = self.world_state.hospital_capacity

        # --- إزالة المتعافين من قائمة المقبولين ---
        recovered = [p for p in self.admitted_patients if p.state != "I"]
        for p in recovered:
            p.in_hospital = False
            p.mobility_factor = self.world_state.mobility_factor
        self.admitted_patients = [p for p in self.admitted_patients if p.state == "I"]

        # --- إزالة المتعافين من الطابور ---
        new_queue = deque()
        for p in self.waiting_queue:
            if p.state == "I":
                new_queue.append(p)
            else:
                p.in_hospital_queue = False
                p.mobility_factor = self.world_state.mobility_factor
        self.waiting_queue = new_queue

        # --- إضافة المصابين الجدد للطابور ---
        for person in persons:
            if person.state != "I":
                continue
            if person.in_hospital:
                continue
            if getattr(person, 'in_hospital_queue', False):
                continue

            # التحقق من القرب من المستشفى
            dist = math.hypot(person.x - self.center_x,
                              person.y - self.center_y)
            if dist <= self.admission_radius:
                # إضافة للطابور
                person.in_hospital_queue = True
                person.mobility_factor   = 0.0  # يقف في مكانه
                self.waiting_queue.append(person)

        # --- قبول المرضى من الطابور ---
        while (self.waiting_queue and
               len(self.admitted_patients) < self.capacity):
            patient = self.waiting_queue.popleft()
            patient.in_hospital       = True
            patient.in_hospital_queue = False
            patient.mobility_factor   = 0.1
            # توجيه المريض لداخل المستشفى
            patient.dest_x = self.center_x + (len(self.admitted_patients) % 4) * 15 - 30
            patient.dest_y = self.center_y + (len(self.admitted_patients) // 4) * 15 - 15
            self.admitted_patients.append(patient)

        # --- تحديث مواقع الطابور البصري ---
        # كل شخص في الطابور يُوجَّه لموقع محدد في الصف
        for i, person in enumerate(self.waiting_queue):
            if i < len(self.queue_positions):
                qx, qy = self.queue_positions[i]
                person.dest_x = qx
                person.dest_y = qy
            else:
                # إذا امتلأت المواقع، يقف في آخر موقع
                if self.queue_positions:
                    person.dest_x, person.dest_y = self.queue_positions[-1]

        self._update_world_state()

    # ==========================================================
    # تحديث الحالة العالمية
    # ==========================================================
    def _update_world_state(self):
        """تحديث مقاييس المستشفى في الحالة العالمية."""
        occupancy  = len(self.admitted_patients)
        queue_len  = len(self.waiting_queue)

        self.world_state.metrics["hospital_occupancy"] = occupancy
        self.world_state.metrics["hospital_queue"]     = queue_len
        self.world_state.metrics["hospital_rejected"]  = self.rejected_count
        self.world_state.metrics["hospital_queue_len"] = queue_len

    def get_occupancy_rate(self) -> float:
        """إرجاع نسبة الإشغال (0.0 - 1.0) - تُستخدم من epidemic_system."""
        if self.capacity == 0:
            return 0.0
        return len(self.admitted_patients) / self.capacity

    def get_queue_positions(self):
        """إرجاع مواقع الطابور البصري للرسم في main.py."""
        return self.queue_positions

    def get_waiting_queue(self):
        """إرجاع قائمة المنتظرين للرسم."""
        return list(self.waiting_queue)

    def reset(self):
        """إعادة تهيئة النظام."""
        self.admitted_patients = []
        self.waiting_queue     = deque()
        self.rejected_count    = 0
        self.capacity          = self.world_state.hospital_capacity
        for p in self.admitted_patients:
            p.in_hospital = False
