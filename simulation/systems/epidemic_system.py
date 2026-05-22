"""
epidemic_system.py  (v5 - FULL SYSTEM INTEGRATION)
===================================================
نظام الوباء المُطوَّر مع التفاعلات الحقيقية:
  - وفيات الوباء تُزيل الأشخاص من القائمة فعلياً
  - المستشفى يُسرّع التعافي (4x) ويُقلل الوفاة (0.2x)
  - إشغال المستشفى يرفع معدل الوفاة (إرهاق طبي)
"""
import random
import math
from simulation.agents.person_agent import (
    STATE_SUSCEPTIBLE, STATE_INFECTED, STATE_RECOVERED,
    INFECTION_DISTANCE
)

class EpidemicSystem:
    def __init__(self, world_state):
        self.world_state = world_state
        self._update_interval = 0.5
        self._timer = 0.0
        self.total_infections  = 0
        self.total_recoveries  = 0
        self.total_deaths      = 0
        self.newly_dead        = []
        # معدل الوفاة الأساسي: ~0.16% يومياً
        self.base_death_rate   = 0.0008
        # تسريع التعافي داخل المستشفى
        self.hospital_recovery_boost = 4.0

    def update(self, persons: list, delta_time: float, hospital=None) -> list:
        """
        تحديث نظام الوباء.
        [جديد]: يُعيد قائمة الأشخاص بعد إزالة المتوفين.
        [جديد]: يقبل hospital للتفاعل المتبادل.
        """
        if self.world_state.paused or not self.world_state.running:
            return persons

        self._timer += delta_time
        if self._timer < self._update_interval:
            return persons
        self._timer = 0.0

        self.newly_dead = []
        infection_rate  = self.world_state.infection_rate

        # --- معدل الوفاة الفعلي (يتأثر بإشغال المستشفى) ---
        # [الربط الحقيقي]: كلما امتلأ المستشفى، ارتفع معدل الوفاة
        hospital_pressure = 0.0
        if hospital is not None:
            hospital_pressure = hospital.get_occupancy_rate()
        effective_death_rate = (self.base_death_rate
                                * (1.0 + hospital_pressure * 4.0)
                                * self.world_state.speed_factor)

        # --- انتشار العدوى ---
        infected_persons    = [p for p in persons if p.state == STATE_INFECTED]
        susceptible_persons = [p for p in persons if p.state == STATE_SUSCEPTIBLE]

        for infected in infected_persons:
            for susceptible in susceptible_persons:
                dist = math.hypot(infected.x - susceptible.x,
                                  infected.y - susceptible.y)
                if dist <= INFECTION_DISTANCE:
                    effective_rate = (infection_rate
                                      * susceptible.mobility_factor
                                      * self._update_interval)
                    if random.random() < effective_rate * 0.1:
                        susceptible.state = STATE_INFECTED
                        susceptible.infection_timer    = 0.0
                        susceptible.infection_duration = random.uniform(2000, 8000)
                        self.total_infections += 1

        # --- التعافي والوفيات ---
        survivors = []
        for person in persons:
            if person.state != STATE_INFECTED:
                survivors.append(person)
                continue

            # التعافي: المستشفى يُسرّع بـ 4x
            if person.in_hospital:
                recovery_prob = (0.001 * self._update_interval
                                 * self.world_state.speed_factor
                                 * self.hospital_recovery_boost)
            else:
                recovery_prob = (0.001 * self._update_interval
                                 * self.world_state.speed_factor)

            if random.random() < recovery_prob:
                person.state       = STATE_RECOVERED
                person.in_hospital = False
                person.mobility_factor = self.world_state.mobility_factor
                self.total_recoveries += 1
                survivors.append(person)
                continue

            # الوفاة: المستشفى يُقلل الاحتمالية بـ 0.2x
            death_prob = effective_death_rate * (0.2 if person.in_hospital else 1.0)
            if random.random() < death_prob:
                self.newly_dead.append(person)
                self.total_deaths += 1
                self.world_state.metrics["total_deaths"] = (
                    self.world_state.metrics.get("total_deaths", 0) + 1
                )
                self.world_state.metrics["total_population"] = max(
                    0, self.world_state.metrics.get("total_population", 1) - 1
                )
            else:
                survivors.append(person)

        self._update_world_state(survivors)
        return survivors

    def _update_world_state(self, persons: list):
        s = sum(1 for p in persons if p.state == STATE_SUSCEPTIBLE)
        i = sum(1 for p in persons if p.state == STATE_INFECTED)
        r = sum(1 for p in persons if p.state == STATE_RECOVERED)
        self.world_state.metrics["susceptible"]      = s
        self.world_state.metrics["infected"]         = i
        self.world_state.metrics["recovered"]        = r
        self.world_state.metrics["epidemic_deaths"]  = self.total_deaths
        self.world_state.metrics["total_infections"] = self.total_infections

    def get_sir_counts(self, persons: list) -> dict:
        return {
            "S": sum(1 for p in persons if p.state == STATE_SUSCEPTIBLE),
            "I": sum(1 for p in persons if p.state == STATE_INFECTED),
            "R": sum(1 for p in persons if p.state == STATE_RECOVERED),
        }

    def reset(self):
        self.total_infections = 0
        self.total_recoveries = 0
        self.total_deaths     = 0
        self.newly_dead       = []
        self._timer           = 0.0
