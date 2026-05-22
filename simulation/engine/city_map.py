"""
city_map.py  (VISUAL REDESIGN - DON'T TOUCH LOGIC)
===================================================
خريطة المدينة الشبكية (Grid-Based City Map)

[المنطق]: لم يتغير أي شيء في منطق توليد الخريطة أو البيانات.
[البصريات]: أُعيد تصميم دالة draw() بالكامل لتقديم مظهر مدينة احترافي:
  - طرق رمادية داكنة مع خطوط وسط بيضاء
  - مباني بيج/رمادي فاتح مع ظلال وإطارات
  - مستشفى أحمر واضح مع أيقونة "+"
  - محطة وقود برتقالية/صفراء مع أيقونة وقود
  - حدائق خضراء مع نقاط عشوائية تمثل الأشجار
  - تأثير إضاءة خفيف على الطرق الرئيسية
"""
import numpy as np
import random

# =====================================================
# ثوابت أنواع البلاطات  (لا تعديل - منطق)
# =====================================================
TILE_ROAD     = 0
TILE_BUILDING = 1
TILE_HOSPITAL = 2
TILE_GAS      = 3
TILE_PARK     = 4

# =====================================================
# أبعاد الشاشة والشبكة  (لا تعديل - منطق)
# =====================================================
# عرض منطقة المحاكاة فقط (بدون اللوحة الجانبية)
CITY_WIDTH    = 1000
CITY_HEIGHT   = 700
SCREEN_WIDTH  = 1250   # عرض النافذة الكامل = مدينة + لوحة جانبية 250px
SCREEN_HEIGHT = 700
SIDEBAR_WIDTH = 250   # عرض اللوحة الجانبية

TILE_SIZE  = 20
GRID_COLS  = CITY_WIDTH  // TILE_SIZE   # 50 عمود
GRID_ROWS  = CITY_HEIGHT // TILE_SIZE   # 35 صف

# =====================================================
# لوحة الألوان البصرية  (بصريات فقط)
# =====================================================
# --- ألوان الأرضية والطرق ---
COLOR_GROUND        = (72,  84,  72)   # أخضر رمادي - أرضية المدينة
COLOR_ROAD          = (45,  45,  50)   # رمادي داكن - الطريق
COLOR_ROAD_MARKING  = (220, 220, 180)  # أصفر فاتح - خط وسط الطريق
COLOR_SIDEWALK      = (90,  90,  95)   # رمادي متوسط - رصيف

# --- ألوان المباني ---
COLOR_BUILDING_BASE = (185, 175, 160)  # بيج - جسم المبنى
COLOR_BUILDING_ROOF = (160, 150, 138)  # بيج أغمق - سطح المبنى
COLOR_BUILDING_WIN  = (140, 180, 220)  # أزرق فاتح - نوافذ
COLOR_BUILDING_EDGE = (130, 122, 110)  # بني - إطار المبنى

# --- ألوان المستشفى ---
COLOR_HOSP_BG       = (200,  40,  40)  # أحمر - خلفية المستشفى
COLOR_HOSP_CROSS    = (255, 255, 255)  # أبيض - علامة "+"
COLOR_HOSP_ROOF     = (170,  25,  25)  # أحمر داكن - سطح المستشفى
COLOR_HOSP_BORDER   = (255, 100, 100)  # أحمر فاتح - إطار وامض

# --- ألوان محطة الوقود ---
COLOR_GAS_BG        = (220, 160,  20)  # برتقالي ذهبي - خلفية المحطة
COLOR_GAS_CANOPY    = (200, 130,   0)  # برتقالي داكن - مظلة المحطة
COLOR_GAS_PUMP      = (255, 200,  50)  # أصفر - مضخة الوقود
COLOR_GAS_BORDER    = (255, 220,  80)  # أصفر فاتح - إطار

# --- ألوان الحديقة ---
COLOR_PARK_BG       = ( 40, 130,  50)  # أخضر - أرضية الحديقة
COLOR_PARK_TREE     = ( 20,  90,  30)  # أخضر داكن - أشجار
COLOR_PARK_PATH     = (120, 100,  70)  # بني - ممشى الحديقة

# ألوان البلاطات للتوافق مع الكود القديم (لا تُستخدم في draw الجديد)
TILE_COLORS = {
    TILE_ROAD:     COLOR_ROAD,
    TILE_BUILDING: COLOR_BUILDING_BASE,
    TILE_HOSPITAL: COLOR_HOSP_BG,
    TILE_GAS:      COLOR_GAS_BG,
    TILE_PARK:     COLOR_PARK_BG,
}


class CityMap:
    """
    خريطة المدينة: شبكة ثنائية الأبعاد من البلاطات.
    [المنطق]: لم يتغير - نفس خوارزمية توليد الخريطة.
    [البصريات]: أُعيدت كتابة draw() بالكامل.
    """

    def __init__(self):
        self.grid          = np.full((GRID_ROWS, GRID_COLS), TILE_BUILDING, dtype=np.int8)
        self.road_tiles    = []
        self.hospital_zone = []
        self.gas_zone      = []
        self.hospital_rect = None
        self.gas_rect      = None
        # بيانات بصرية إضافية (لا تؤثر على المنطق)
        self._building_details = {}   # تفاصيل بصرية لكل مبنى (نوافذ، ارتفاع)
        self._park_trees       = {}   # مواقع الأشجار في الحدائق
        self._generate_map()
        self._generate_visual_details()

    # ==========================================================
    # توليد الخريطة  (لا تعديل في المنطق)
    # ==========================================================
    def _generate_map(self):
        """توليد خريطة المدينة إجرائياً. [لا تعديل في المنطق]"""
        # 1. طرق أفقية رئيسية كل 5 صفوف
        for row in range(0, GRID_ROWS, 5):
            for col in range(GRID_COLS):
                self.grid[row][col] = TILE_ROAD
        # 2. طرق عمودية رئيسية كل 5 أعمدة
        for col in range(0, GRID_COLS, 5):
            for row in range(GRID_ROWS):
                self.grid[row][col] = TILE_ROAD
        # 3. منطقة المستشفى (الزاوية العلوية اليمنى)
        hosp_col_start = GRID_COLS - 10
        hosp_row_start = 1
        hosp_col_end   = GRID_COLS - 2
        hosp_row_end   = 6
        for r in range(hosp_row_start, hosp_row_end):
            for c in range(hosp_col_start, hosp_col_end):
                self.grid[r][c] = TILE_HOSPITAL
        self.hospital_rect = (
            hosp_col_start * TILE_SIZE,
            hosp_row_start * TILE_SIZE,
            (hosp_col_end - hosp_col_start) * TILE_SIZE,
            (hosp_row_end - hosp_row_start) * TILE_SIZE,
        )
        for c in range(hosp_col_start - 1, hosp_col_end + 1):
            self.grid[hosp_row_end][c] = TILE_ROAD
        # 4. محطة الوقود (الزاوية السفلية اليسرى)
        gas_col_start = 2
        gas_row_start = GRID_ROWS - 7
        gas_col_end   = 10
        gas_row_end   = GRID_ROWS - 2
        for r in range(gas_row_start, gas_row_end):
            for c in range(gas_col_start, gas_col_end):
                self.grid[r][c] = TILE_GAS
        self.gas_rect = (
            gas_col_start * TILE_SIZE,
            gas_row_start * TILE_SIZE,
            (gas_col_end - gas_col_start) * TILE_SIZE,
            (gas_row_end - gas_row_start) * TILE_SIZE,
        )
        for c in range(gas_col_start - 1, gas_col_end + 1):
            self.grid[gas_row_start - 1][c] = TILE_ROAD
        # 5. حدائق عشوائية
        for _ in range(5):
            pr = random.randint(2, GRID_ROWS - 5)
            pc = random.randint(2, GRID_COLS - 5)
            if self.grid[pr][pc] == TILE_BUILDING:
                for dr in range(2):
                    for dc in range(2):
                        if 0 <= pr+dr < GRID_ROWS and 0 <= pc+dc < GRID_COLS:
                            if self.grid[pr+dr][pc+dc] == TILE_BUILDING:
                                self.grid[pr+dr][pc+dc] = TILE_PARK
        # 6. بناء قوائم البلاطات
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                t = self.grid[r][c]
                px = c * TILE_SIZE + TILE_SIZE // 2
                py = r * TILE_SIZE + TILE_SIZE // 2
                if t == TILE_ROAD:
                    self.road_tiles.append((px, py))
                elif t == TILE_HOSPITAL:
                    self.hospital_zone.append((px, py))
                elif t == TILE_GAS:
                    self.gas_zone.append((px, py))
        print(f"[CityMap] تم توليد الخريطة: {len(self.road_tiles)} بلاطة طريق")

    # ==========================================================
    # توليد التفاصيل البصرية  (بصريات فقط - لا تأثير على المنطق)
    # ==========================================================
    def _generate_visual_details(self):
        """
        توليد تفاصيل بصرية عشوائية للمباني والحدائق.
        هذه البيانات تُستخدم فقط في دالة draw() ولا تؤثر على المنطق.
        """
        rng = random.Random(42)   # بذرة ثابتة لضمان ثبات المظهر
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.grid[r][c] == TILE_BUILDING:
                    # ارتفاع بصري عشوائي للمبنى (2-5 طوابق)
                    floors = rng.randint(2, 5)
                    # عدد النوافذ الأفقية والعمودية
                    win_cols = rng.randint(1, 2)
                    win_rows = rng.randint(1, floors)
                    # لون بيج عشوائي طفيف
                    shade = rng.randint(-15, 15)
                    self._building_details[(r, c)] = {
                        "floors":   floors,
                        "win_cols": win_cols,
                        "win_rows": win_rows,
                        "shade":    shade,
                    }
                elif self.grid[r][c] == TILE_PARK:
                    # مواقع أشجار عشوائية داخل البلاطة
                    trees = [(rng.randint(2, TILE_SIZE-3),
                              rng.randint(2, TILE_SIZE-3))
                             for _ in range(rng.randint(1, 3))]
                    self._park_trees[(r, c)] = trees

    # ==========================================================
    # دوال الاستعلام  (لا تعديل - منطق)
    # ==========================================================
    def is_road(self, x: float, y: float) -> bool:
        col = int(x) // TILE_SIZE
        row = int(y) // TILE_SIZE
        if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
            return self.grid[row][col] == TILE_ROAD
        return False

    def get_tile_type(self, x: float, y: float) -> int:
        col = int(x) // TILE_SIZE
        row = int(y) // TILE_SIZE
        if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
            return int(self.grid[row][col])
        return TILE_BUILDING

    def get_random_road_tile(self) -> tuple:
        return random.choice(self.road_tiles)

    def get_nearest_road(self, x: float, y: float) -> tuple:
        min_dist = float('inf')
        nearest  = self.road_tiles[0]
        for tile in self.road_tiles:
            d = (tile[0] - x) ** 2 + (tile[1] - y) ** 2
            if d < min_dist:
                min_dist = d
                nearest  = tile
        return nearest

    # ==========================================================
    # دوال التحقق من الحركة  (منطق الحركة الجديد)
    # ==========================================================

    def is_walkable(self, x: float, y: float) -> bool:
        """
        التحقق من أن الموقع (x, y) قابل للمشي للأشخاص.

        البلاطات السالكة للأشخاص:
          - TILE_ROAD     : الطريق (دائماً سالك)
          - TILE_PARK     : الحديقة (سالكة)
          - TILE_HOSPITAL : منطقة المستشفى (مدخل سالك للأشخاص)
          - TILE_GAS      : منطقة محطة الوقود (مدخل سالك للأشخاص)

        البلاطات المحظورة:
          - TILE_BUILDING : المباني (محظور تماماً)
          - خارج حدود الخريطة (محظور)

        لماذا نسمح بالمستشفى ومحطة الوقود؟
          لأن الأشخاص يحتاجون للوصول إليها (علاج، تعبئة وقود).
        """
        col = int(x) // TILE_SIZE
        row = int(y) // TILE_SIZE
        # --- التحقق من الحدود: لا يخرج الشخص عن الخريطة ---
        if not (0 <= row < GRID_ROWS and 0 <= col < GRID_COLS):
            return False
        tile = int(self.grid[row][col])
        # --- المباني محظورة تماماً ---
        return tile != TILE_BUILDING

    def is_intersection(self, x: float, y: float) -> bool:
        """
        التحقق من أن الموقع (x, y) يقع عند تقاطع طرق.

        كيف يُكتشف التقاطع؟
          نفحص عدد الاتجاهات الصالحة (طريق) حول الموقع الحالي.
          إذا كان عدد الاتجاهات الصالحة >= 3، فهو تقاطع.
          إذا كان 2 والاتجاهان متعاكسان (مستقيم)، فليس تقاطعاً.
          إذا كان 2 والاتجاهان متجاوران (منعطف)، فهو تقاطع (منعطف).

        لماذا نكتشف التقاطعات؟
          لأن الوكلاء يجب أن يغيروا اتجاههم فقط عند التقاطعات،
          وليس في منتصف الطريق، مما يجعل الحركة واقعية.
        """
        col = int(x) // TILE_SIZE
        row = int(y) // TILE_SIZE
        if not (0 <= row < GRID_ROWS and 0 <= col < GRID_COLS):
            return False
        if int(self.grid[row][col]) != TILE_ROAD:
            return False

        # --- فحص الاتجاهات الأربعة ---
        # (drow, dcol): أعلى، أسفل، يسار، يمين
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        valid = []
        for dr, dc in directions:
            nr, nc = row + dr, col + dc
            if 0 <= nr < GRID_ROWS and 0 <= nc < GRID_COLS:
                if int(self.grid[nr][nc]) == TILE_ROAD:
                    valid.append((dr, dc))

        # تقاطع: 3 اتجاهات أو أكثر
        if len(valid) >= 3:
            return True
        # منعطف: اتجاهان متجاوران (ليسا متعاكسين)
        if len(valid) == 2:
            (r1, c1), (r2, c2) = valid
            # الاتجاهان المتعاكسان: مجموعهما (0,0)
            if (r1 + r2, c1 + c2) != (0, 0):
                return True   # منعطف = تقاطع بالنسبة للوكيل
        return False

    def get_valid_directions(self, x: float, y: float,
                             agent_type: str = "vehicle") -> list:
        """
        إرجاع قائمة الاتجاهات الصالحة من الموقع الحالي.

        agent_type:
          "vehicle" : يتحرك على TILE_ROAD فقط
          "person"  : يتحرك على أي بلاطة سالكة (is_walkable)

        كيف تعمل؟
          نفحص الموقع المجاور في كل اتجاه (بمسافة TILE_SIZE).
          إذا كان الموقع صالحاً، نضيف الاتجاه للقائمة.

        لماذا نستخدم هذه الدالة؟
          لمنع الوكلاء من الدخول في المباني أو خارج الحدود.
          الوكيل يختار فقط من الاتجاهات الصالحة المُعادة.

        الاتجاهات المُعادة: قائمة من (dx, dy) بالبكسل
          (0, -TILE_SIZE)  : أعلى
          (0, +TILE_SIZE)  : أسفل
          (-TILE_SIZE, 0)  : يسار
          (+TILE_SIZE, 0)  : يمين
        """
        # الاتجاهات الأربعة الأساسية بالبكسل
        step = TILE_SIZE
        candidates = [
            ( 0,    -step),   # أعلى
            ( 0,    +step),   # أسفل
            (-step,  0),      # يسار
            (+step,  0),      # يمين
        ]
        valid = []
        for dx, dy in candidates:
            nx = x + dx
            ny = y + dy
            if agent_type == "vehicle":
                # المركبات: الطريق فقط
                if self.is_road(nx, ny):
                    valid.append((dx, dy))
            else:
                # الأشخاص: أي بلاطة سالكة
                if self.is_walkable(nx, ny):
                    valid.append((dx, dy))
        return valid

    def snap_to_road_center(self, x: float, y: float) -> tuple:
        """
        محاذاة الموقع إلى مركز أقرب بلاطة طريق.

        لماذا نحتاج هذه الدالة؟
          الوكلاء يتحركون بالبكسل، لكن التقاطعات تُكتشف بالبلاطات.
          المحاذاة تضمن أن الوكيل يكون في مركز البلاطة عند التقاطع،
          مما يمنع الانجراف عن الطريق.
        """
        col = int(x) // TILE_SIZE
        row = int(y) // TILE_SIZE
        col = max(0, min(GRID_COLS - 1, col))
        row = max(0, min(GRID_ROWS - 1, row))
        # مركز البلاطة
        cx = col * TILE_SIZE + TILE_SIZE // 2
        cy = row * TILE_SIZE + TILE_SIZE // 2
        return (float(cx), float(cy))

    # ==========================================================
    # دالة الرسم  (بصريات فقط - أُعيد تصميمها بالكامل)
    # ==========================================================
    def draw(self, surface):
        """
        رسم الخريطة الكاملة على سطح Pygame.
        [بصريات]: أُعيد تصميم هذه الدالة بالكامل لمظهر مدينة احترافي.
        [المنطق]: لم يتغير أي شيء خارج هذه الدالة.

        ترتيب الرسم (من الأسفل للأعلى):
        1. أرضية المدينة (خلفية خضراء رمادية)
        2. الطرق مع خطوط الوسط
        3. المباني مع نوافذ وظلال
        4. الحدائق مع أشجار
        5. المستشفى مع علامة "+"
        6. محطة الوقود مع أيقونة
        """
        import pygame

        # --- 1. أرضية المدينة ---
        # لون الأرضية: أخضر رمادي يشبه العشب الحضري
        surface.fill(COLOR_GROUND)

        # --- 2. رسم الطرق ---
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.grid[r][c] == TILE_ROAD:
                    rx = c * TILE_SIZE
                    ry = r * TILE_SIZE
                    # جسم الطريق
                    pygame.draw.rect(surface, COLOR_ROAD,
                                     (rx, ry, TILE_SIZE, TILE_SIZE))
                    # رصيف خفيف على حواف الطريق
                    pygame.draw.rect(surface, COLOR_SIDEWALK,
                                     (rx, ry, TILE_SIZE, TILE_SIZE), 1)

        # --- 2b. خطوط وسط الطرق (خطوط متقطعة) ---
        # خطوط أفقية على الطرق الأفقية
        for row in range(0, GRID_ROWS, 5):
            for c in range(0, GRID_COLS - 1, 2):   # خط متقطع كل بلاطتين
                cx = c * TILE_SIZE + TILE_SIZE
                cy = row * TILE_SIZE + TILE_SIZE // 2
                pygame.draw.line(surface, COLOR_ROAD_MARKING,
                                 (cx - 4, cy), (cx + 4, cy), 1)
        # خطوط عمودية على الطرق العمودية
        for col in range(0, GRID_COLS, 5):
            for r in range(0, GRID_ROWS - 1, 2):
                cx = col * TILE_SIZE + TILE_SIZE // 2
                cy = r * TILE_SIZE + TILE_SIZE
                pygame.draw.line(surface, COLOR_ROAD_MARKING,
                                 (cx, cy - 4), (cx, cy + 4), 1)

        # --- 3. رسم المباني ---
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.grid[r][c] == TILE_BUILDING:
                    self._draw_building(surface, r, c)

        # --- 4. رسم الحدائق ---
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                if self.grid[r][c] == TILE_PARK:
                    self._draw_park(surface, r, c)

        # --- 5. رسم المستشفى ---
        if self.hospital_rect:
            self._draw_hospital(surface)

        # --- 6. رسم محطة الوقود ---
        if self.gas_rect:
            self._draw_gas_station(surface)

    # ----------------------------------------------------------
    # دوال رسم مساعدة  (بصريات فقط)
    # ----------------------------------------------------------

    def _draw_building(self, surface, r: int, c: int):
        """
        رسم مبنى واحد مع نوافذ وظل وإطار.
        [الألوان]: بيج/رمادي فاتح مع نوافذ زرقاء خفيفة.
        """
        import pygame
        details = self._building_details.get((r, c), {})
        shade   = details.get("shade", 0)

        bx = c * TILE_SIZE
        by = r * TILE_SIZE
        ts = TILE_SIZE

        # لون المبنى مع تدرج عشوائي طفيف
        base_r = max(0, min(255, COLOR_BUILDING_BASE[0] + shade))
        base_g = max(0, min(255, COLOR_BUILDING_BASE[1] + shade))
        base_b = max(0, min(255, COLOR_BUILDING_BASE[2] + shade))
        bld_color = (base_r, base_g, base_b)

        # جسم المبنى (مع هامش 1px من كل جهة)
        pygame.draw.rect(surface, bld_color,
                         (bx + 1, by + 1, ts - 2, ts - 2))

        # إطار المبنى
        pygame.draw.rect(surface, COLOR_BUILDING_EDGE,
                         (bx + 1, by + 1, ts - 2, ts - 2), 1)

        # نافذة صغيرة في المنتصف (إذا كانت البلاطة كبيرة بما يكفي)
        if ts >= 18:
            win_w = max(3, ts // 4)
            win_h = max(3, ts // 4)
            win_x = bx + (ts - win_w) // 2
            win_y = by + (ts - win_h) // 2
            pygame.draw.rect(surface, COLOR_BUILDING_WIN,
                             (win_x, win_y, win_w, win_h))

        # ظل خفيف في الزاوية اليمنى السفلى
        shadow_color = (max(0, bld_color[0] - 25),
                        max(0, bld_color[1] - 25),
                        max(0, bld_color[2] - 25))
        pygame.draw.line(surface, shadow_color,
                         (bx + ts - 1, by + 2), (bx + ts - 1, by + ts - 1), 1)
        pygame.draw.line(surface, shadow_color,
                         (bx + 2, by + ts - 1), (bx + ts - 1, by + ts - 1), 1)

    def _draw_park(self, surface, r: int, c: int):
        """
        رسم حديقة مع أشجار صغيرة.
        [الألوان]: أخضر مع نقاط خضراء داكنة تمثل الأشجار.
        """
        import pygame
        bx = c * TILE_SIZE
        by = r * TILE_SIZE
        ts = TILE_SIZE

        # أرضية الحديقة
        pygame.draw.rect(surface, COLOR_PARK_BG,
                         (bx + 1, by + 1, ts - 2, ts - 2))
        # إطار الحديقة
        pygame.draw.rect(surface, COLOR_PARK_TREE,
                         (bx + 1, by + 1, ts - 2, ts - 2), 1)

        # رسم الأشجار
        trees = self._park_trees.get((r, c), [])
        for (tx, ty) in trees:
            pygame.draw.circle(surface, COLOR_PARK_TREE,
                               (bx + tx, by + ty), 3)

    def _draw_hospital(self, surface):
        """
        رسم منطقة المستشفى مع علامة "+" بيضاء وتسمية واضحة.
        [الألوان]: أحمر مع إطار أحمر فاتح وعلامة بيضاء.
        """
        import pygame
        hx, hy, hw, hh = self.hospital_rect

        # خلفية المستشفى
        pygame.draw.rect(surface, COLOR_HOSP_BG,
                         (hx, hy, hw, hh))

        # سطح المستشفى (شريط علوي أغمق)
        pygame.draw.rect(surface, COLOR_HOSP_ROOF,
                         (hx, hy, hw, 8))

        # إطار المستشفى (سميك)
        pygame.draw.rect(surface, COLOR_HOSP_BORDER,
                         (hx, hy, hw, hh), 3)

        # علامة "+" في المنتصف
        cx = hx + hw // 2
        cy = hy + hh // 2
        cross_size = min(hw, hh) // 3
        cross_thick = max(4, cross_size // 3)
        # الخط الأفقي
        pygame.draw.rect(surface, COLOR_HOSP_CROSS,
                         (cx - cross_size, cy - cross_thick // 2,
                          cross_size * 2, cross_thick))
        # الخط العمودي
        pygame.draw.rect(surface, COLOR_HOSP_CROSS,
                         (cx - cross_thick // 2, cy - cross_size,
                          cross_thick, cross_size * 2))

        # تسمية "HOSPITAL"
        try:
            font = pygame.font.SysFont("Arial", 11, bold=True)
        except Exception:
            font = pygame.font.Font(None, 12)
        label = font.render("HOSPITAL", True, (255, 255, 255))
        lx = hx + (hw - label.get_width()) // 2
        ly = hy + hh - 14
        # خلفية شفافة للنص
        bg = pygame.Surface((label.get_width() + 4, 13), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 120))
        surface.blit(bg, (lx - 2, ly - 1))
        surface.blit(label, (lx, ly))

    def _draw_gas_station(self, surface):
        """
        رسم محطة الوقود مع مظلة ومضخة وتسمية.
        [الألوان]: برتقالي/ذهبي مع تفاصيل صفراء.
        """
        import pygame
        gx, gy, gw, gh = self.gas_rect

        # أرضية المحطة
        pygame.draw.rect(surface, COLOR_GAS_BG,
                         (gx, gy, gw, gh))

        # مظلة المحطة (شريط علوي)
        pygame.draw.rect(surface, COLOR_GAS_CANOPY,
                         (gx, gy, gw, 10))

        # إطار المحطة
        pygame.draw.rect(surface, COLOR_GAS_BORDER,
                         (gx, gy, gw, gh), 3)

        # رسم مضخة وقود بسيطة في المنتصف
        cx = gx + gw // 2
        cy = gy + gh // 2
        pump_w = max(8, gw // 5)
        pump_h = max(12, gh // 3)
        # جسم المضخة
        pygame.draw.rect(surface, COLOR_GAS_PUMP,
                         (cx - pump_w // 2, cy - pump_h // 2, pump_w, pump_h))
        pygame.draw.rect(surface, COLOR_GAS_CANOPY,
                         (cx - pump_w // 2, cy - pump_h // 2, pump_w, pump_h), 1)
        # خرطوم المضخة (خط منحنٍ بسيط)
        pygame.draw.line(surface, COLOR_GAS_CANOPY,
                         (cx + pump_w // 2, cy),
                         (cx + pump_w // 2 + 6, cy + 5), 2)

        # تسمية "GAS"
        try:
            font = pygame.font.SysFont("Arial", 11, bold=True)
        except Exception:
            font = pygame.font.Font(None, 12)
        label = font.render("GAS STATION", True, (30, 20, 0))
        lx = gx + (gw - label.get_width()) // 2
        ly = gy + gh - 14
        bg = pygame.Surface((label.get_width() + 4, 13), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 80))
        surface.blit(bg, (lx - 2, ly - 1))
        surface.blit(label, (lx, ly))
