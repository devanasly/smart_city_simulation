"""
world_state.py
==============
الحالة العالمية للمحاكاة (World State)

هذا الملف يحتوي على الكائن المركزي الذي يتحكم في جميع معاملات المحاكاة.
كل الأنظمة تقرأ من هذا الكائن وتكتب إليه لضمان التنسيق بين الأنظمة المختلفة.
"""

import json
import os
import time as _time

# مسارات ملفات JSON
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BASE_DIR, "data", "config", "config.json")
RESULTS_PATH = os.path.join(BASE_DIR, "data", "results.json")
SESSIONS_DIR = os.path.join(BASE_DIR, "data", "sessions")


class WorldState:
    """
    الكائن المركزي الذي يحمل جميع معاملات المحاكاة والحالة الراهنة.
    يُقرأ من ملف config.json عند بدء كل جلسة جديدة.
    """

    def __init__(self):
        # --- معاملات الزمن ---
        self.simulation_time = 0.0       # الزمن التراكمي بالدقائق (1 ثانية حقيقية = 1 دقيقة محاكاة)
        self.speed_factor = 1            # مضاعف السرعة: 1, 2, 5, 10
        self.paused = False              # هل المحاكاة متوقفة مؤقتاً؟
        self.running = True              # هل المحاكاة تعمل؟

        # --- معاملات السكان ---
        self.population = 100
        self.birth_rate = 0.02           # معدل المواليد سنوياً
        self.death_rate = 0.01           # معدل الوفيات سنوياً

        # --- معاملات الوباء ---
        self.infection_rate = 0.3        # احتمالية انتقال العدوى عند التقارب
        self.mobility_factor = 0.8       # معامل الحركة (يؤثر على انتشار الوباء)

        # --- معاملات المستشفى ---
        self.hospital_capacity = 50      # الطاقة الاستيعابية للمستشفى

        # --- معاملات محطة الوقود ---
        self.fuel_rate = 0.05            # معدل استهلاك الوقود لكل مركبة

        # --- معاملات المرور ---
        self.traffic_density = 0.4       # كثافة المرور الابتدائية (0.0 - 1.0)

        # --- مدة المحاكاة ---
        self.simulation_duration_years = 10
        self.simulation_duration_minutes = self.simulation_duration_years * 365 * 24 * 60

        # --- معرّف الجلسة ---
        self.session_id = self._generate_session_id()
        self.session_start_time = _time.time()

        # --- مقاييس الأداء (تُحدَّث من الأنظمة) ---
        self.metrics = {
            "susceptible": 0,
            "infected": 0,
            "recovered": 0,
            "hospital_occupancy": 0,
            "hospital_rejected": 0,
            "gas_queue_length": 0,
            "gas_avg_wait": 0.0,
            "traffic_congestion": 0.0,
            "traffic_avg_delay": 0.0,
            "total_population": 0,
        }

        # --- سجل السلاسل الزمنية ---
        self.time_series = []

    def _generate_session_id(self):
        """توليد معرّف فريد للجلسة بناءً على الوقت الحالي."""
        return f"session_{int(_time.time())}"

    def load_config(self):
        """
        قراءة ملف config.json وتطبيق المعاملات على الحالة العالمية.
        يُستدعى عند بداية كل جلسة جديدة أو عند الضغط على زر Reset.
        """
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)

            if cfg.get("apply", False):
                self.infection_rate = float(cfg.get("infection_rate", self.infection_rate))
                self.hospital_capacity = int(cfg.get("hospital_capacity", self.hospital_capacity))
                self.fuel_rate = float(cfg.get("fuel_rate", self.fuel_rate))
                self.traffic_density = float(cfg.get("traffic_density", self.traffic_density))
                self.simulation_duration_years = float(cfg.get("simulation_duration_years", self.simulation_duration_years))
                self.simulation_duration_minutes = self.simulation_duration_years * 365 * 24 * 60
                self.population = int(cfg.get("population", self.population))
                self.mobility_factor = float(cfg.get("mobility_factor", self.mobility_factor))
                self.birth_rate = float(cfg.get("birth_rate", self.birth_rate))
                self.death_rate = float(cfg.get("death_rate", self.death_rate))
                self.speed_factor = int(cfg.get("speed_factor", self.speed_factor))

                # إعادة تعيين علامة apply إلى false بعد القراءة
                cfg["apply"] = False
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2, ensure_ascii=False)

                print(f"[WorldState] تم تحميل الإعدادات من config.json للجلسة: {self.session_id}")
                return True
        except Exception as e:
            print(f"[WorldState] خطأ في قراءة config.json: {e}")
        return False

    def reset(self):
        """
        إعادة تهيئة الحالة العالمية بالكامل.
        يحفظ الجلسة الحالية ثم يبدأ جلسة جديدة.
        """
        # حفظ الجلسة الحالية قبل الإعادة
        self.save_session()

        # إعادة تعيين جميع المعاملات
        self.simulation_time = 0.0
        self.paused = False
        self.running = True
        self.session_id = self._generate_session_id()
        self.session_start_time = _time.time()
        self.time_series = []
        self.metrics = {k: 0 for k in self.metrics}
        self.metrics["traffic_congestion"] = 0.0
        self.metrics["traffic_avg_delay"] = 0.0
        self.metrics["gas_avg_wait"] = 0.0

        # تحميل الإعدادات الجديدة
        self.load_config()
        print(f"[WorldState] تمت إعادة التهيئة. جلسة جديدة: {self.session_id}")

    def update_time(self, delta_time: float):
        """
        تحديث الزمن التراكمي للمحاكاة.
        delta_time: الفارق الزمني بالثواني الحقيقية منذ آخر إطار.
        """
        if not self.paused and self.running:
            # 1 ثانية حقيقية = 1 دقيقة محاكاة * مضاعف السرعة
            self.simulation_time += delta_time * self.speed_factor

    def record_snapshot(self):
        """
        تسجيل لقطة من المقاييس الحالية في السلسلة الزمنية.
        تُستدعى كل دقيقة محاكاة تقريباً.
        """
        snapshot = {
            "sim_time_minutes": round(self.simulation_time, 2),
            **self.metrics
        }
        self.time_series.append(snapshot)

    def save_results(self):
        """
        كتابة نتائج المحاكاة الحالية إلى results.json.
        تُستدعى بانتظام من الحلقة الرئيسية.
        """
        try:
            data = {
                "session_id": self.session_id,
                "sim_time_minutes": round(self.simulation_time, 2),
                "current_metrics": self.metrics,
                "time_series": self.time_series[-500:],  # آخر 500 نقطة فقط لتجنب الملفات الضخمة
            }
            with open(RESULTS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[WorldState] خطأ في حفظ results.json: {e}")

    def save_session(self):
        """
        حفظ بيانات الجلسة الكاملة في مجلد sessions.
        """
        try:
            os.makedirs(SESSIONS_DIR, exist_ok=True)
            session_file = os.path.join(SESSIONS_DIR, f"{self.session_id}.json")
            data = {
                "session_id": self.session_id,
                "parameters": {
                    "infection_rate": self.infection_rate,
                    "hospital_capacity": self.hospital_capacity,
                    "fuel_rate": self.fuel_rate,
                    "traffic_density": self.traffic_density,
                    "simulation_duration_years": self.simulation_duration_years,
                    "population": self.population,
                    "mobility_factor": self.mobility_factor,
                    "birth_rate": self.birth_rate,
                    "death_rate": self.death_rate,
                },
                "simulation_duration_minutes": round(self.simulation_time, 2),
                "time_series": self.time_series,
            }
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"[WorldState] تم حفظ الجلسة: {session_file}")
        except Exception as e:
            print(f"[WorldState] خطأ في حفظ الجلسة: {e}")

    def get_sim_time_display(self):
        """إرجاع الزمن بصيغة قابلة للعرض (أيام وساعات ودقائق)."""
        total_minutes = int(self.simulation_time)
        days = total_minutes // (24 * 60)
        hours = (total_minutes % (24 * 60)) // 60
        minutes = total_minutes % 60
        return f"يوم {days:04d} | {hours:02d}:{minutes:02d}"
