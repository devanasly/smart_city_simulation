"""
population_system.py
====================
نظام السكان (Population System)

يُتابع إجمالي السكان ديناميكياً مع معدلات المواليد والوفيات.
يُضيف أشخاصاً جدداً أو يُزيل المتوفين من قائمة الوكلاء.

[الإصلاح الجذري - سبب المشكلة القديمة]
========================================
المشكلة الأصلية:
    birth_prob = birth_rate / (365 * 24 * 60 / 60) = 0.02 / 525600 ≈ 0.0000023
    births = int(100 * 0.0000023) = int(0.00023) = 0  ← دائماً صفر!

    الكود القديم كان يحوّل الاحتمالية لعدد صحيح بـ int()،
    وبما أن الاحتمالية أصغر بكثير من 1، النتيجة دائماً صفر.

الإصلاح:
    نستخدم الاحتمالية مباشرة مع random.random() لكل شخص:
        if random.random() < birth_prob_per_person → يُضاف مولود
    هذا يضمن إضافة مواليد بشكل احتمالي حتى عند معدلات صغيرة.

    أو نستخدم random.random() < total_expected_births:
        expected = population * birth_prob
        births = int(expected) + (1 if random.random() < (expected % 1) else 0)
    هذا يضمن دائماً إضافة مولود واحد على الأقل كل عدة دورات.

[معدل المواليد الديناميكي - مرتبط بالوباء]
============================================
المعادلة:
    effective_birth_rate = base_birth_rate * birth_multiplier

    إذا infection_ratio < HEALTH_BONUS_THRESHOLD (مجتمع صحي):
        birth_multiplier = 1.0 + (HEALTH_BONUS_MULTIPLIER - 1.0) * health_level
        (يرتفع المعدل فوق الطبيعي = baby boom)

    إذا infection_ratio >= HEALTH_BONUS_THRESHOLD (وجود وباء):
        birth_multiplier = 1.0 - (infection_ratio * EPIDEMIC_SUPPRESSION)
        (ينخفض المعدل بنسبة تتناسب مع شدة الوباء)

[المقاييس الجديدة]
    effective_birth_rate : معدل المواليد الفعلي (%)
    epidemic_suppression : نسبة القمع (%)
    total_births         : إجمالي المواليد
    total_deaths         : إجمالي الوفيات
"""

import random
from simulation.agents.person_agent import PersonAgent, STATE_SUSCEPTIBLE

# =====================================================
# ثوابت المنطق الديناميكي
# =====================================================

# معامل قمع الوباء للمواليد (0.9 = عند 100% إصابة يبقى 10% من المعدل)
EPIDEMIC_SUPPRESSION = 0.9

# مضاعف المواليد عند انعدام المرض (baby boom)
HEALTH_BONUS_MULTIPLIER = 1.5

# الحد الأدنى لنسبة المصابين لتفعيل مكافأة الصحة
HEALTH_BONUS_THRESHOLD = 0.02

# الحد الأدنى لمعدل المواليد (لا يصل للصفر أبداً)
MIN_BIRTH_RATE_FACTOR = 0.05


class PopulationSystem:
    """
    نظام السكان: يُدير التغيرات الديموغرافية خلال المحاكاة.

    [مُصلَح]: يستخدم الاحتمالية العشوائية بدلاً من int()
    لضمان إضافة مواليد حتى عند معدلات صغيرة.

    [جديد]: معدل المواليد يتأثر ديناميكياً بنسبة المصابين.
    """

    def __init__(self, world_state, city_map):
        self.world_state = world_state
        self.city_map    = city_map

        # مؤقت للتحديث الدوري
        # [مُصلَح]: خُفِّض من 60 إلى 10 ثوانٍ لتسريع ظهور التغيير
        self._update_interval = 10.0   # ثانية حقيقية
        self._timer = 0.0

        # عداد المواليد والوفيات
        self.total_births  = 0
        self.total_deaths  = 0

        # معدل المواليد الفعلي الحالي
        self.effective_birth_rate = world_state.birth_rate

        # نسبة قمع الوباء الحالية
        self.current_suppression = 0.0

    # ==========================================================
    # دالة التحديث الرئيسية
    # ==========================================================

    def update(self, persons: list, delta_time: float) -> list:
        """
        تحديث نظام السكان في كل إطار.
        يُعيد قائمة الأشخاص المحدَّثة.
        """
        if self.world_state.paused or not self.world_state.running:
            return persons

        self._timer += delta_time * self.world_state.speed_factor
        if self._timer < self._update_interval:
            self._update_world_state(persons)
            return persons

        self._timer = 0.0
        total = max(1, len(persons))

        # ============================================================
        # [جديد] حساب معدل المواليد الديناميكي بناءً على الوباء
        # ============================================================

        infected_count  = self.world_state.metrics.get("infected", 0)
        infection_ratio = infected_count / total

        if infection_ratio < HEALTH_BONUS_THRESHOLD:
            # مجتمع صحي: مكافأة المواليد (baby boom)
            health_level     = 1.0 - (infection_ratio / HEALTH_BONUS_THRESHOLD)
            birth_multiplier = 1.0 + (HEALTH_BONUS_MULTIPLIER - 1.0) * health_level
            self.current_suppression = 0.0
        else:
            # وجود وباء: تقليل المواليد تدريجياً
            suppression_factor   = infection_ratio * EPIDEMIC_SUPPRESSION
            birth_multiplier     = max(MIN_BIRTH_RATE_FACTOR, 1.0 - suppression_factor)
            self.current_suppression = suppression_factor

        self.effective_birth_rate = self.world_state.birth_rate * birth_multiplier

        # ============================================================
        # [الإصلاح الجذري] المواليد باستخدام الاحتمالية العشوائية
        # ============================================================
        # المشكلة القديمة: int(population * birth_prob) = 0 دائماً
        # الحل: نحسب العدد المتوقع ونستخدم الجزء العشري كاحتمالية
        #
        # مثال: birth_prob = 0.00023
        #   expected = 100 * 0.00023 = 0.023
        #   int(0.023) = 0
        #   random.random() < 0.023 → 2.3% احتمال إضافة مولود هذه الدورة
        #   كل 10 دورات تقريباً يُضاف مولود واحد

        # تحويل المعدل السنوي لاحتمالية لكل دورة تحديث
        # المعادلة: birth_prob = birth_rate * (update_interval / 60)
        # هذا يعني: birth_rate=0.1 يعطي ~1.7 مولود لكل 100 شخص في كل دورة
        # ويظهر التغيير بشكل مرئي خلال دقيقة واحدة من المحاكاة
        birth_prob = self.effective_birth_rate * (self._update_interval / 60.0)
        expected_births = total * birth_prob

        # الجزء الصحيح: مواليد مضمونة
        guaranteed = int(expected_births)
        # الجزء العشري: احتمالية مولود إضافي
        fractional = expected_births - guaranteed

        births = guaranteed + (1 if random.random() < fractional else 0)

        for _ in range(births):
            new_person = PersonAgent(self.city_map, self.world_state)
            new_person.state = STATE_SUSCEPTIBLE
            persons.append(new_person)
            self.total_births += 1

        # ============================================================
        # [الإصلاح الجذري] الوفيات باستخدام الاحتمالية العشوائية
        # ============================================================
        death_prob = self.world_state.death_rate * (self._update_interval / 60.0)
        expected_deaths = total * death_prob

        guaranteed_d = int(expected_deaths)
        fractional_d = expected_deaths - guaranteed_d
        deaths_count = guaranteed_d + (1 if random.random() < fractional_d else 0)

        if deaths_count > 0 and len(persons) > deaths_count + 10:
            # إزالة عشوائية من غير المصابين أولاً
            non_infected = [p for p in persons if p.state != "I"]
            to_remove = random.sample(non_infected,
                                      min(deaths_count, len(non_infected)))
            for p in to_remove:
                persons.remove(p)
                self.total_deaths += 1

        self._update_world_state(persons)
        return persons

    # ==========================================================
    # تحديث المقاييس في الحالة العالمية
    # ==========================================================

    def _update_world_state(self, persons: list):
        """
        تحديث مقاييس السكان في الحالة العالمية.
        """
        self.world_state.metrics["total_population"]     = len(persons)
        self.world_state.population                      = len(persons)

        self.world_state.metrics["effective_birth_rate"] = round(
            self.effective_birth_rate * 100, 4)
        self.world_state.metrics["epidemic_suppression"] = round(
            self.current_suppression * 100, 2)
        self.world_state.metrics["total_births"]         = self.total_births
        self.world_state.metrics["total_deaths"]         = self.total_deaths
