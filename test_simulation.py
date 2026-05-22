"""
test_simulation.py
==================
اختبار شامل لجميع وحدات المحاكاة بدون واجهة Pygame

يُشغِّل المحاكاة لعدة إطارات ويتحقق من صحة جميع الأنظمة.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# --- تعطيل Pygame للاختبار ---
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_mode((100, 100))

from simulation.engine.world_state import WorldState
from simulation.engine.city_map    import CityMap
from simulation.agents.person_agent  import PersonAgent
from simulation.agents.vehicle_agent import VehicleAgent
from simulation.systems.traffic_system     import TrafficSystem
from simulation.systems.gas_station_system import GasStationSystem
from simulation.systems.hospital_system    import HospitalSystem
from simulation.systems.epidemic_system    import EpidemicSystem
from simulation.systems.population_system  import PopulationSystem


def test_all():
    print("=" * 60)
    print("اختبار نظام محاكاة المدينة الذكية")
    print("=" * 60)

    # --- 1. WorldState ---
    print("\n[1] اختبار WorldState...")
    ws = WorldState()
    ws.load_config()
    assert ws.session_id.startswith("session_"), "خطأ في session_id"
    assert ws.infection_rate > 0, "خطأ في infection_rate"
    print(f"    session_id: {ws.session_id}")
    print(f"    infection_rate: {ws.infection_rate}")
    print(f"    hospital_capacity: {ws.hospital_capacity}")
    print("    [PASS] WorldState")

    # --- 2. CityMap ---
    print("\n[2] اختبار CityMap...")
    cm = CityMap()
    assert len(cm.road_tiles) > 100, "عدد بلاطات الطريق قليل جداً"
    assert cm.hospital_rect is not None, "لم يتم تحديد منطقة المستشفى"
    assert cm.gas_rect is not None, "لم يتم تحديد محطة الوقود"
    road = cm.get_random_road_tile()
    assert cm.is_road(road[0], road[1]), "الموقع العشوائي ليس على طريق"
    print(f"    بلاطات الطريق: {len(cm.road_tiles)}")
    print(f"    المستشفى: {cm.hospital_rect}")
    print(f"    محطة الوقود: {cm.gas_rect}")
    print("    [PASS] CityMap")

    # --- 3. PersonAgent ---
    print("\n[3] اختبار PersonAgent...")
    PersonAgent.reset_counter()
    persons = [PersonAgent(cm, ws) for _ in range(20)]
    assert len(persons) == 20, "خطأ في إنشاء الأشخاص"
    infected_count = sum(1 for p in persons if p.state == "I")
    print(f"    عدد الأشخاص: {len(persons)}")
    print(f"    المصابون ابتداءً: {infected_count}")
    # تحديث الأشخاص لعدة إطارات
    for _ in range(10):
        for p in persons:
            p.update(0.016)
    print("    [PASS] PersonAgent")

    # --- 4. VehicleAgent ---
    print("\n[4] اختبار VehicleAgent...")
    VehicleAgent.reset_counter()
    vehicles = [VehicleAgent(cm, ws) for _ in range(10)]
    assert len(vehicles) == 10, "خطأ في إنشاء المركبات"
    print(f"    عدد المركبات: {len(vehicles)}")
    for _ in range(10):
        for v in vehicles:
            v.update(0.016, 0.3)
    print("    [PASS] VehicleAgent")

    # --- 5. TrafficSystem ---
    print("\n[5] اختبار TrafficSystem...")
    traffic = TrafficSystem(ws, cm)
    traffic.update(vehicles, 0.016)
    cong = traffic.get_congestion_level()
    assert 0 <= cong <= 1, "مستوى الازدحام خارج النطاق"
    print(f"    مستوى الازدحام: {cong:.3f}")
    print("    [PASS] TrafficSystem")

    # --- 6. GasStationSystem ---
    print("\n[6] اختبار GasStationSystem...")
    gas = GasStationSystem(ws, cm)
    # تقليل وقود مركبة لاختبار الطابور
    vehicles[0].fuel_level = 0.1
    gas.check_vehicles(vehicles)
    gas.update(0.016)
    print(f"    طول الطابور: {len(gas.queue)}")
    print("    [PASS] GasStationSystem")

    # --- 7. HospitalSystem ---
    print("\n[7] اختبار HospitalSystem...")
    hospital = HospitalSystem(ws, cm)
    hospital.update(persons, 0.016)
    occ = hospital.get_occupancy_rate()
    assert 0 <= occ <= 1, "نسبة الإشغال خارج النطاق"
    print(f"    نسبة الإشغال: {occ:.3f}")
    print(f"    الحالات المرفوضة: {hospital.rejected_count}")
    print("    [PASS] HospitalSystem")

    # --- 8. EpidemicSystem ---
    print("\n[8] اختبار EpidemicSystem...")
    epidemic = EpidemicSystem(ws)
    # تشغيل لفترة كافية لتجاوز الفاصل الزمني
    for _ in range(40):
        epidemic.update(persons, 0.016)
    sir = epidemic.get_sir_counts(persons)
    print(f"    SIR: S={sir['S']}, I={sir['I']}, R={sir['R']}")
    assert sir['S'] + sir['I'] + sir['R'] == len(persons), "مجموع SIR لا يساوي عدد السكان"
    print("    [PASS] EpidemicSystem")

    # --- 9. PopulationSystem ---
    print("\n[9] اختبار PopulationSystem...")
    pop_system = PopulationSystem(ws, cm)
    initial_count = len(persons)
    persons = pop_system.update(persons, 0.016)
    print(f"    السكان الأوليون: {initial_count}")
    print(f"    السكان بعد التحديث: {len(persons)}")
    print("    [PASS] PopulationSystem")

    # --- 10. حفظ النتائج ---
    print("\n[10] اختبار حفظ النتائج...")
    ws.update_time(1.0)
    ws.record_snapshot()
    ws.save_results()
    results_path = os.path.join(os.path.dirname(__file__), "data", "results.json")
    assert os.path.exists(results_path), "لم يتم إنشاء results.json"
    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)
    assert "session_id" in results, "results.json لا يحتوي على session_id"
    print(f"    results.json: {results_path}")
    print(f"    session_id: {results['session_id']}")
    print("    [PASS] حفظ النتائج")

    # --- 11. حفظ الجلسة ---
    print("\n[11] اختبار حفظ الجلسة...")
    ws.save_session()
    sessions_dir = os.path.join(os.path.dirname(__file__), "data", "sessions")
    sessions = [f for f in os.listdir(sessions_dir) if f.endswith(".json")]
    assert len(sessions) > 0, "لم يتم حفظ أي جلسة"
    print(f"    عدد الجلسات المحفوظة: {len(sessions)}")
    print("    [PASS] حفظ الجلسة")

    print("\n" + "=" * 60)
    print("جميع الاختبارات اجتازت بنجاح!")
    print("=" * 60)

    pygame.quit()


if __name__ == "__main__":
    test_all()
