"""
===============================================
املف تشغيل المحاكاة الرئيسي وفتح نافذة Pygame.
طريقة التشغيل:
    python main.py
"""
import sys
import os
import time
import pygame

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simulation.engine.world_state   import WorldState
from simulation.engine.city_map      import (CityMap, SCREEN_WIDTH, SCREEN_HEIGHT,
                                              CITY_WIDTH, CITY_HEIGHT)
from simulation.engine.ui_controls   import UIControls, SIDEBAR_WIDTH, SIDEBAR_X
from simulation.agents.person_agent  import PersonAgent
from simulation.agents.vehicle_agent import VehicleAgent
from simulation.systems.traffic_system     import TrafficSystem
from simulation.systems.gas_station_system import GasStationSystem
from simulation.systems.hospital_system    import HospitalSystem
from simulation.systems.epidemic_system    import EpidemicSystem
from simulation.systems.population_system  import PopulationSystem

# =====================================================
# ثوابت  ()
# =====================================================
FPS           = 60 # معدل الإطارات المستهدف
SAVE_INTERVAL = 2.0 # حفظ النتائج كل 2 ثانية
TITLE         = "Smart City Simulation  |  نظام محاكاة المدينة الذكية"

# =====================================================
# لوحة الألوان البصرية  (بصريات فقط)
# =====================================================
# --- خلفية النافذة ---
COLOR_BG          = ( 15,  20,  30)   # رمادي مزرق داكن جداً
COLOR_CITY_BORDER = ( 50,  70, 110)   # حد منطقة المدينة

# --- شريط العنوان العلوي ---
COLOR_TOPBAR_BG   = ( 12,  18,  30)   # رمادي داكن - خلفية الشريط
COLOR_TOPBAR_LINE = ( 40,  60, 100)   # خط فاصل سفلي
COLOR_TOPBAR_TEXT = (180, 210, 255)   # أزرق فاتح - نص العنوان
COLOR_TOPBAR_DIM  = (100, 130, 170)   # رمادي مزرق - نص ثانوي

# --- ألوان رسم الأشخاص ---
PERSON_COLOR_S    = ( 70, 130, 220)   # أزرق - قابل للإصابة
PERSON_COLOR_I    = (220,  60,  60)   # أحمر - مصاب
PERSON_COLOR_R    = ( 50, 180,  80)   # أخضر - متعافٍ
PERSON_COLOR_BODY = (200, 200, 200)   # رمادي - جسم الشخص
PERSON_GLOW_I     = (255, 100,  50)   # برتقالي - هالة المصاب

# --- ألوان رسم المركبات ---
VEHICLE_COLORS = [
    (220, 220,  80),   # أصفر
    ( 80, 180, 220),   # أزرق فاتح
    (220, 120,  60),   # برتقالي
    (180, 220,  80),   # أخضر فاتح
    (220,  80, 180),   # وردي
    (160, 200, 255),   # أزرق سماوي
]
VEHICLE_ROOF_DARKEN = 40   # تعتيم سقف المركبة

# ارتفاع شريط العنوان العلوي
TOPBAR_HEIGHT = 24


# =====================================================
# دوال تهيئة الوكلاء والأنظمة  ()
# =====================================================
#تنشيء الاشخاص والسيارات
def initialize_agents(world_state, city_map):
    """إنشاء الوكلاء الابتدائيين. [hhh]"""
    PersonAgent.reset_counter() #تصفير عداد الأشخاص إلى الصفر
    VehicleAgent.reset_counter() #تصفير عداد المركبات إلى الصفر
    persons  = [PersonAgent(city_map, world_state) #إنشاء قائمة أشخاص بعدد السكان الموجود في world_state.population
                for _ in range(world_state.population)] #كرر انشاء الاشخاص بعدد السكان
    num_vehicles = max(5, int(world_state.population * 0.3)) #تحديد عدد المركبات بناءً على نسبة من السكان (30% أو 5 مركبات كحد أدنى)
    vehicles = [VehicleAgent(city_map, world_state) #إنشاء قائمة السيارات
                for _ in range(num_vehicles)]
    return persons, vehicles # ترجع قايمة الأشخاص والمركبات

#تنشئ الأنظمة الاساسية للمحاكاة
def initialize_systems(world_state, city_map):
    """إنشاء جميع أنظمة المحاكاة. [لا تعديل في المنطق]"""
    traffic    = TrafficSystem(world_state, city_map)
    gas        = GasStationSystem(world_state, city_map)
    hospital   = HospitalSystem(world_state, city_map)
    epidemic   = EpidemicSystem(world_state) # نظام الوباء
    population = PopulationSystem(world_state, city_map)
    return traffic, gas, hospital, epidemic, population


# =====================================================
# دوال الرسم البصري  (بصريات فقط)
# =====================================================

def draw_topbar(surface, world_state, font_title, font_dim):
    """
    رسم شريط العنوان العلوي الأنيق.
    [الألوان]: رمادي داكن + نص أزرق فاتح.
    يعرض: اسم النظام | معرّف الجلسة | الوقت | الحالة.
    """
    # خلفية الشريط
    pygame.draw.rect(surface, COLOR_TOPBAR_BG,
                     (0, 0, SCREEN_WIDTH, TOPBAR_HEIGHT))
    # خط فاصل سفلي
    pygame.draw.line(surface, COLOR_TOPBAR_LINE,
                     (0, TOPBAR_HEIGHT - 1),
                     (SCREEN_WIDTH, TOPBAR_HEIGHT - 1), 1)

    ws = world_state

    # --- اسم النظام (يسار) ---
    title_surf = font_title.render("Smart City Simulation", True, COLOR_TOPBAR_TEXT)
    surface.blit(title_surf, (8, 4))

    # --- معلومات الجلسة (وسط) ---
    info_text = (f"Session: {ws.session_id.replace('session_', '')}   |   "
                 f"Time: {ws.get_sim_time_display()}   |   "
                 f"Pop: {ws.metrics.get('total_population', 0)}")
    info_surf = font_dim.render(info_text, True, COLOR_TOPBAR_DIM)
    info_x = (CITY_WIDTH - info_surf.get_width()) // 2
    surface.blit(info_surf, (info_x, 5))

    # --- حالة المحاكاة (يمين) ---
    if ws.paused:
        state_text  = "[ PAUSED ]"
        state_color = (220, 160, 30)
    else:
        state_text  = "[ RUNNING ]"
        state_color = (50, 200, 80)
    state_surf = font_title.render(state_text, True, state_color)
    surface.blit(state_surf, (CITY_WIDTH - state_surf.get_width() - 10, 4))


def draw_person(surface, person):
    """
    رسم شخص بتصميم محسّن: دائرة رأس + جسم.
    [الألوان]:
      - أزرق (S): قابل للإصابة
      - أحمر (I): مصاب مع هالة برتقالية
      - أخضر (R): متعافٍ
    [المنطق]: لا يُعدَّل أي خاصية للشخص، فقط الرسم.
    """
    state = person.state
    px    = int(person.x)
    py    = int(person.y) + TOPBAR_HEIGHT   # إزاحة شريط العنوان

    # اختيار اللون حسب الحالة
    if state == "S":
        head_color = PERSON_COLOR_S
        body_color = (50, 100, 180)
    elif state == "I":
        head_color = PERSON_COLOR_I
        body_color = (160, 30, 30)
    else:   # R
        head_color = PERSON_COLOR_R
        body_color = (30, 130, 50)

    # هالة للمصابين (تنبيه بصري)
    if state == "I":
        pygame.draw.circle(surface, PERSON_GLOW_I, (px, py), 6, 1)

    # جسم الشخص (بيضاوي صغير)
    pygame.draw.ellipse(surface, body_color,
                        (px - 2, py + 2, 5, 4))

    # رأس الشخص (دائرة)
    pygame.draw.circle(surface, head_color, (px, py), 4)

    # نقطة مركزية بيضاء (تفصيل)
    pygame.draw.circle(surface, (255, 255, 255), (px, py), 1)


def draw_vehicle(surface, vehicle):
    """
    رسم مركبة بتصميم محسّن: مستطيل مع سقف أغمق وعجلات.
    [المنطق]: لا يُعدَّل أي خاصية للمركبة، فقط الرسم.
    """
    import math
    vx = int(vehicle.x)
    vy = int(vehicle.y) + TOPBAR_HEIGHT

    # أبعاد المركبة
    vw = 12
    vh = 7

    # إنشاء سطح للمركبة
    veh_surf = pygame.Surface((vw, vh), pygame.SRCALPHA)

    # جسم المركبة
    body_color = vehicle.color
    pygame.draw.rect(veh_surf, body_color, (0, 0, vw, vh), border_radius=2)

    # سقف المركبة (أغمق)
    roof_color = (max(0, body_color[0] - VEHICLE_ROOF_DARKEN),
                  max(0, body_color[1] - VEHICLE_ROOF_DARKEN),
                  max(0, body_color[2] - VEHICLE_ROOF_DARKEN))
    pygame.draw.rect(veh_surf, roof_color,
                     (2, 1, vw - 4, vh - 2), border_radius=1)

    # زجاج أمامي (أزرق فاتح)
    pygame.draw.rect(veh_surf, (150, 200, 240),
                     (vw - 3, 1, 2, vh - 2))

    # عجلات (نقاط داكنة في الزوايا)
    wheel_color = (30, 30, 30)
    pygame.draw.circle(veh_surf, wheel_color, (2, 1),     1)
    pygame.draw.circle(veh_surf, wheel_color, (2, vh - 1), 1)
    pygame.draw.circle(veh_surf, wheel_color, (vw - 2, 1),     1)
    pygame.draw.circle(veh_surf, wheel_color, (vw - 2, vh - 1), 1)

    # تدوير حسب الاتجاه
    rotated = pygame.transform.rotate(veh_surf, -vehicle.angle)
    rect    = rotated.get_rect(center=(vx, vy))
    surface.blit(rotated, rect)

    # شريط الوقود فوق المركبة
    bar_w = vw
    bar_h = 2
    bar_x = vx - bar_w // 2
    bar_y = vy - vh - 4
    pygame.draw.rect(surface, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h))
    fuel_color = (50, 200, 80) if vehicle.fuel_level > 0.3 else (220, 80, 30)
    fill_w = int(bar_w * vehicle.fuel_level)
    if fill_w > 0:
        pygame.draw.rect(surface, fuel_color, (bar_x, bar_y, fill_w, bar_h))


def rebuild_map_surface(city_map):
    """
    إنشاء سطح الخريطة الثابت.
    يُستدعى مرة واحدة عند البدء وعند Reset.
    """
    map_surf = pygame.Surface((CITY_WIDTH, CITY_HEIGHT))
    city_map.draw(map_surf)
    return map_surf


# =====================================================
# الحلقة الرئيسية  ()
# =====================================================

def run_simulation():
    """
    الدالة الرئيسية لتشغيل المحاكاة.
    [المنطق]: لم يتغير أي شيء في منطق التحديث.
    [البصريات]: أُعيد تصميم طبقة الرسم بالكامل.
    """
    # --- تهيئة Pygame ---
    #os.environ["SDL_VIDEODRIVER"] = "dummy"   # للتشغيل بدون شاشة في البيئة الافتراضية
    pygame.init()
    pygame.font.init()

    # نافذة أوسع تشمل اللوحة الجانبية
    # SCREEN_WIDTH = CITY_WIDTH (1000) + SIDEBAR_WIDTH (250) = 1250
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    # خطوط الشريط العلوي
    try:
        font_title = pygame.font.SysFont("Arial", 12, bold=True)
        font_dim   = pygame.font.SysFont("Arial", 11)
    except Exception:
        font_title = pygame.font.Font(None, 13)
        font_dim   = pygame.font.Font(None, 12)

    # --- إنشاء الكائنات الأساسية ---
    world_state = WorldState()
    world_state.load_config()
    city_map    = CityMap()

    # --- سطح الخريطة الثابت (double buffering) ---
    map_surface = rebuild_map_surface(city_map)

    # --- إنشاء الوكلاء والأنظمة ---
    persons, vehicles = initialize_agents(world_state, city_map)
    traffic, gas, hospital, epidemic, population = initialize_systems(world_state, city_map)

    # --- واجهة التحكم ---
    ui = UIControls(world_state)

    # --- متغيرات الحلقة ---
    save_timer = 0.0
    last_time  = time.time()
    running    = True

    print(f"[Main] بدأت المحاكاة. جلسة: {world_state.session_id}")
    print(f"[Main] عدد الأشخاص: {len(persons)} | عدد المركبات: {len(vehicles)}")

    # =====================================================
    # الحلقة الرئيسية
    # =====================================================
    while running:


        current_time = time.time()
        delta_time   = min(current_time - last_time, 0.05)#-----
        last_time    = current_time

        # --- معالجة الأحداث  [لا تعديل] ---
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
                world_state.running = False

        # --- معالجة أزرار التحكم  [] ---
        action = ui.handle_events(events)
        if action == "resume":
            world_state.paused = False
            print("[Main] استئناف المحاكاة")
        elif action == "pause":
            world_state.paused = True
            print("[Main] إيقاف مؤقت")
        elif action == "reset":
            print("[Main] إعادة التهيئة...")
            world_state.reset()
            city_map    = CityMap()
            map_surface = rebuild_map_surface(city_map)
            persons, vehicles = initialize_agents(world_state, city_map)
            traffic, gas, hospital, epidemic, population = initialize_systems(world_state, city_map)
            ui = UIControls(world_state)
            save_timer = 0.0
            print(f"[Main] جلسة جديدة: {world_state.session_id}")

        # --- تحديث الزمن  [] ---
        world_state.update_time(delta_time)

        # --- تحديث الأنظمة  [لا تعديل في المنطق] ---
        if not world_state.paused and world_state.running:
            traffic.update(vehicles, delta_time)
            congestion = traffic.get_congestion_level()
            for vehicle in vehicles:
                vehicle.update(delta_time, congestion)
            gas.check_vehicles(vehicles)
            gas.update(delta_time)
            for person in persons:
                person.update(delta_time)
            epidemic.update(persons, delta_time)
            hospital.update(persons, delta_time)
            persons = population.update(persons, delta_time)
            ui.update(delta_time)

        # --- حفظ النتائج دورياً  [لا تعديل] ---
        save_timer += delta_time
        if save_timer >= SAVE_INTERVAL:
            save_timer = 0.0
            world_state.save_results()

        # --- التحقق من انتهاء المحاكاة  [لا تعديل] ---
        if (world_state.simulation_time >=
                world_state.simulation_duration_minutes):
            print("[Main] انتهت مدة المحاكاة المحددة.")
            world_state.save_results()
            world_state.save_session()
            world_state.reset()
            city_map    = CityMap()
            map_surface = rebuild_map_surface(city_map)
            persons, vehicles = initialize_agents(world_state, city_map)
            traffic, gas, hospital, epidemic, population = initialize_systems(world_state, city_map)
            ui = UIControls(world_state)

        # =====================================================
        # طبقة الرسم  (بصريات فقط - أُعيدت كتابتها بالكامل)
        # =====================================================

        # --- 1. خلفية النافذة الكاملة ---
        screen.fill(COLOR_BG)

        # --- 2. رسم الخريطة الثابتة (مع إزاحة شريط العنوان) ---
        screen.blit(map_surface, (0, TOPBAR_HEIGHT))

        # --- 3. رسم المركبات (فوق الخريطة) ---
        for vehicle in vehicles:
            draw_vehicle(screen, vehicle)

        # --- 4. رسم الأشخاص (فوق المركبات) ---
        for person in persons:
            draw_person(screen, person)

        # --- 5. رسم طابور محطة الوقود البصري ---
        # خط الانتظار: نقاط زرقاء متقطعة تُشير لمواقع الطابور
        gas_q_positions = gas.get_queue_positions()
        gas_q_vehicles  = gas.get_queue_list()
        if gas_q_positions:
            for i, (qx, qy) in enumerate(gas_q_positions[:8]):
                # رسم دائرة رمادية شفافة لموقع الانتظار
                pygame.draw.circle(screen, (180, 160, 80),
                                   (int(qx), int(qy + TOPBAR_HEIGHT)), 5, 1)
            # رسم خط متقطع أزرق يصل مواقع الطابور
            pts = [(int(p[0]), int(p[1] + TOPBAR_HEIGHT))
                   for p in gas_q_positions[:len(gas_q_vehicles)]]
            for i in range(len(pts) - 1):
                if i % 2 == 0:
                    pygame.draw.line(screen, (100, 180, 255), pts[i], pts[i+1], 1)
            # تسمية الطابور
            if gas_q_vehicles:
                lbl = font_dim.render(f"طابور: {len(gas_q_vehicles)}", True, (255, 200, 0))
                if gas_q_positions:
                    screen.blit(lbl, (int(gas_q_positions[0][0]) - 10,
                                      int(gas_q_positions[0][1] + TOPBAR_HEIGHT) - 14))

        # --- 5b. رسم طابور المستشفى البصري ---
        hosp_q_positions = hospital.get_queue_positions()
        hosp_q_persons   = hospital.get_waiting_queue()
        if hosp_q_positions:
            for i, (qx, qy) in enumerate(hosp_q_positions[:12]):
                pygame.draw.circle(screen, (255, 120, 120),
                                   (int(qx), int(qy + TOPBAR_HEIGHT)), 4, 1)
            # خط متقطع أزرق يصل مواقع الطابور
            pts = [(int(p[0]), int(p[1] + TOPBAR_HEIGHT))
                   for p in hosp_q_positions[:len(hosp_q_persons)]]
            for i in range(len(pts) - 1):
                if i % 2 == 0:
                    pygame.draw.line(screen, (100, 180, 255), pts[i], pts[i+1], 1)
            # تسمية الطابور
            if hosp_q_persons:
                lbl = font_dim.render(f"انتظار: {len(hosp_q_persons)}", True, (255, 100, 100))
                if hosp_q_positions:
                    screen.blit(lbl, (int(hosp_q_positions[0][0]) + 6,
                                      int(hosp_q_positions[0][1] + TOPBAR_HEIGHT) - 14))

        # --- 6. شريط العنوان العلوي (فوق كل شيء في منطقة المدينة) ---
        draw_topbar(screen, world_state, font_title, font_dim)

        # --- 6. اللوحة الجانبية ---
        ui.draw(screen)

        # --- 7. عرض الإطار (double buffering) ---
        pygame.display.flip()
        clock.tick(FPS)

    # =====================================================
    # إنهاء المحاكاة  [لا تعديل]
    # =====================================================
    world_state.save_results()
    world_state.save_session()
    pygame.quit()
    print("[Main] انتهت المحاكاة وتم حفظ جميع البيانات.")


if __name__ == "__main__":
    run_simulation()
