"""
اختبار شامل لنظام التنبؤ المحلي
=================================
يتحقق من:
1. وجود الملفات الجديدة والمعدّلة
2. صحة دوال prediction_system.py
3. صحة نقاط API في server.py
4. صحة عناصر HTML في index.html
5. صحة دوال JS في dashboard.js
6. صحة أنماط CSS في style.css
7. التكامل الكامل: توليد تنبؤ من بيانات حقيقية
"""

import os
import sys
import json
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ألوان للطرفية
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  {GREEN}PASS{RESET}  {name}")
        passed += 1
    else:
        print(f"  {RED}FAIL{RESET}  {name}" + (f" — {detail}" if detail else ""))
        failed += 1

# ===================================================
# 1. وجود الملفات
# ===================================================
print(f"\n{BOLD}=== 1. وجود الملفات ==={RESET}")

files_to_check = [
    "simulation/systems/prediction_system.py",
    "dashboard/index.html",
    "dashboard/style.css",
    "dashboard/dashboard.js",
    "server.py",
    "data/results.json",
]
for f in files_to_check:
    path = os.path.join(BASE_DIR, f)
    test(f"ملف {f} موجود", os.path.exists(path))

# ===================================================
# 2. اختبار دوال prediction_system.py
# ===================================================
print(f"\n{BOLD}=== 2. دوال prediction_system.py ==={RESET}")

from simulation.systems.prediction_system import (
    clean_series,
    predict_linear_regression,
    predict_moving_average,
    predict_exponential_smoothing,
    detect_trend,
    apply_constraints,
    generate_prediction,
    save_prediction
)

# clean_series
test("clean_series: إزالة None", clean_series([1, None, 3]) == [1.0, 3.0])
test("clean_series: إزالة NaN", len(clean_series([1, float('nan'), 3])) == 2)
test("clean_series: إزالة inf", len(clean_series([1, float('inf'), 3])) == 2)
test("clean_series: بيانات نظيفة", clean_series([1, 2, 3]) == [1.0, 2.0, 3.0])

# predict_linear_regression
data_lr = [10, 12, 14, 16, 18, 20]
pred_lr = predict_linear_regression(data_lr, 3)
test("linear_regression: عدد النقاط صحيح", len(pred_lr) == 3)
test("linear_regression: اتجاه تصاعدي", pred_lr[0] < pred_lr[-1])
test("linear_regression: بيانات قصيرة (1 نقطة)", len(predict_linear_regression([5], 3)) == 3)

# predict_moving_average
data_ma = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30]
pred_ma = predict_moving_average(data_ma, 5, window=5)
test("moving_average: عدد النقاط صحيح", len(pred_ma) == 5)
test("moving_average: قيمة ثابتة", len(set(pred_ma)) == 1)
test("moving_average: متوسط صحيح", abs(pred_ma[0] - np.mean(data_ma[-5:])) < 0.01)

# predict_exponential_smoothing
data_es = [10, 12, 14, 16, 18, 20]
pred_es = predict_exponential_smoothing(data_es, 4, alpha=0.3)
test("exponential_smoothing: عدد النقاط صحيح", len(pred_es) == 4)
test("exponential_smoothing: قيمة ثابتة", len(set(pred_es)) == 1)

# detect_trend
test("detect_trend: تصاعدي", detect_trend([10, 12, 14, 16]) == "increasing")
test("detect_trend: تنازلي", detect_trend([16, 14, 12, 10]) == "decreasing")
test("detect_trend: مستقر", detect_trend([10, 10, 10, 10]) == "stable")
test("detect_trend: نقطة واحدة", detect_trend([5]) == "stable")

# apply_constraints
test("apply_constraints: لا قيم سالبة", all(v >= 0 for v in apply_constraints([-5, 0, 5], "infected")))
test("apply_constraints: hospital_occupancy <= 1", all(v <= 1 for v in apply_constraints([0.5, 1.5, 2.0], "hospital_occupancy")))
test("apply_constraints: traffic_congestion <= 1", all(v <= 1 for v in apply_constraints([0.3, 0.8, 1.2], "traffic_congestion")))
test("apply_constraints: infected أعداد صحيحة", all(isinstance(v, int) for v in apply_constraints([1.7, 2.3, 3.9], "infected")))
test("apply_constraints: population أعداد صحيحة", all(isinstance(v, int) for v in apply_constraints([100.5, 200.7], "total_population")))

# ===================================================
# 3. اختبار generate_prediction بالبيانات الحقيقية
# ===================================================
print(f"\n{BOLD}=== 3. التكامل: توليد تنبؤ من بيانات حقيقية ==={RESET}")

results_path = os.path.join(BASE_DIR, "data", "results.json")
metrics_to_test = ["infected", "total_population", "hospital_occupancy", "traffic_congestion", "gas_queue_length"]
modes_to_test   = ["linear_regression", "moving_average", "exponential_smoothing"]

for metric in metrics_to_test:
    for mode in modes_to_test:
        result = generate_prediction(results_path, metric, mode, 30)
        has_error = "error" in result
        if has_error and result["error"] == "Not enough data for prediction":
            test(f"generate_prediction({metric}, {mode}): رسالة بيانات قليلة", True)
        else:
            test(f"generate_prediction({metric}, {mode}): نجح", not has_error, result.get("error", ""))
            if not has_error:
                pred_vals = result["predictions"][metric]["values"]
                test(f"  — لا قيم سالبة ({metric})", all(v >= 0 for v in pred_vals))
                if metric in ["hospital_occupancy", "traffic_congestion"]:
                    test(f"  — قيود النسبة ({metric})", all(v <= 1 for v in pred_vals))
                if metric in ["infected", "total_population", "gas_queue_length"]:
                    test(f"  — أعداد صحيحة ({metric})", all(isinstance(v, int) for v in pred_vals))

# اختبار البيانات القليلة: توليد تنبؤ ببيانات قصيرة مصطنعة
import tempfile, json as _json
_short_data = {"session_id": "test", "time_series": [
    {"sim_time_minutes": i, "infected": i*2} for i in range(3)
]}
with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as _tf:
    _json.dump(_short_data, _tf)
    _tf_path = _tf.name
_short_result = generate_prediction(_tf_path, "infected", "linear_regression", 10)
os.unlink(_tf_path)
test("generate_prediction: أقل من 5 نقاط → رسالة خطأ",
     _short_result.get("error") == "Not enough data for prediction")

# ===================================================
# 4. اختبار save_prediction
# ===================================================
print(f"\n{BOLD}=== 4. حفظ نتائج التنبؤ ==={RESET}")

import tempfile
result_sample = generate_prediction(results_path, "infected", "linear_regression", 30)
if "error" not in result_sample:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode='w') as tmp:
        tmp_path = tmp.name
    saved = save_prediction(result_sample, tmp_path)
    test("save_prediction: حفظ ناجح", saved)
    if saved:
        with open(tmp_path) as f:
            loaded = json.load(f)
        test("save_prediction: session_id محفوظ", "session_id" in loaded)
        test("save_prediction: mode محفوظ", "mode" in loaded)
        test("save_prediction: predictions محفوظة", "predictions" in loaded)
        test("save_prediction: trend محفوظ", "trend" in loaded)
        test("save_prediction: data_points_used محفوظ", "data_points_used" in loaded)
    os.unlink(tmp_path)
else:
    print(f"  {YELLOW}SKIP{RESET}  save_prediction (بيانات غير كافية)")

# ===================================================
# 5. اختبار server.py
# ===================================================
print(f"\n{BOLD}=== 5. server.py ==={RESET}")

with open(os.path.join(BASE_DIR, "server.py"), encoding="utf-8") as f:
    server_content = f.read()

test("server.py: مسار PREDICTIONS_PATH موجود", "PREDICTIONS_PATH" in server_content)
test("server.py: GET /api/predictions موجود", "/api/predictions" in server_content)
test("server.py: POST /api/predict موجود", "/api/predict" in server_content)
test("server.py: استيراد generate_prediction", "generate_prediction" in server_content)
test("server.py: استيراد save_prediction", "save_prediction" in server_content)
test("server.py: معالجة metric", '"metric"' in server_content or "'metric'" in server_content)
test("server.py: معالجة mode", '"mode"' in server_content or "'mode'" in server_content)
test("server.py: معالجة horizon", '"horizon"' in server_content or "'horizon'" in server_content)

# ===================================================
# 6. اختبار index.html
# ===================================================
print(f"\n{BOLD}=== 6. index.html ==={RESET}")

with open(os.path.join(BASE_DIR, "dashboard", "index.html"), encoding="utf-8") as f:
    html_content = f.read()

test("index.html: قسم predictionSection موجود", 'id="predictionSection"' in html_content)
test("index.html: checkbox predictionEnabled موجود", 'id="predictionEnabled"' in html_content)
test("index.html: select predMetric موجود", 'id="predMetric"' in html_content)
test("index.html: select predMode موجود", 'id="predMode"' in html_content)
test("index.html: select predHorizon موجود", 'id="predHorizon"' in html_content)
test("index.html: custom horizon input موجود", 'id="predCustomHorizon"' in html_content)
test("index.html: زر btnGeneratePrediction موجود", 'id="btnGeneratePrediction"' in html_content)
test("index.html: canvas chartPrediction موجود", 'id="chartPrediction"' in html_content)
test("index.html: predictionExplanation موجود", 'id="predictionExplanation"' in html_content)
test("index.html: predictionLoading موجود", 'id="predictionLoading"' in html_content)
test("index.html: خيار infected موجود", 'value="infected"' in html_content)
test("index.html: خيار linear_regression موجود", 'value="linear_regression"' in html_content)
test("index.html: خيار moving_average موجود", 'value="moving_average"' in html_content)
test("index.html: خيار exponential_smoothing موجود", 'value="exponential_smoothing"' in html_content)
test("index.html: خيار 30 دقيقة موجود", 'value="30"' in html_content)
test("index.html: خيار 60 دقيقة موجود", 'value="60"' in html_content)
test("index.html: خيار 120 دقيقة موجود", 'value="120"' in html_content)
test("index.html: خيار custom موجود", 'value="custom"' in html_content)
test("index.html: onchange=onPredictionToggle", "onPredictionToggle" in html_content)
test("index.html: onchange=onHorizonChange", "onHorizonChange" in html_content)
test("index.html: onclick=generatePrediction", "generatePrediction" in html_content)

# ===================================================
# 7. اختبار dashboard.js
# ===================================================
print(f"\n{BOLD}=== 7. dashboard.js ==={RESET}")

with open(os.path.join(BASE_DIR, "dashboard", "dashboard.js"), encoding="utf-8") as f:
    js_content = f.read()

test("dashboard.js: دالة onPredictionToggle موجودة", "function onPredictionToggle" in js_content)
test("dashboard.js: دالة onHorizonChange موجودة", "function onHorizonChange" in js_content)
test("dashboard.js: دالة generatePrediction موجودة", "async function generatePrediction" in js_content)
test("dashboard.js: دالة _renderPredictionChart موجودة", "function _renderPredictionChart" in js_content)
test("dashboard.js: دالة _renderPredictionExplanation موجودة", "function _renderPredictionExplanation" in js_content)
test("dashboard.js: دالة _getHistoricalDataForMetric موجودة", "function _getHistoricalDataForMetric" in js_content)
test("dashboard.js: دالة _showPredictionError موجودة", "function _showPredictionError" in js_content)
test("dashboard.js: دالة _getPredictionHorizon موجودة", "function _getPredictionHorizon" in js_content)
test("dashboard.js: POST /api/predict موجود", '"/api/predict"' in js_content)
test("dashboard.js: GET /api/predictions موجود", '"/api/predictions' in js_content)
test("dashboard.js: شرح عربي للاتجاه", "تزايد تدريجي" in js_content)
test("dashboard.js: شرح عربي للتمهيد الأسي", "التمهيد الأسي" in js_content)
test("dashboard.js: خط متقطع للتنبؤ", "borderDash" in js_content)
test("dashboard.js: لون الخط الفعلي أزرق", "#58a6ff" in js_content)
test("dashboard.js: لون الخط المتوقع برتقالي", "#f0883e" in js_content)
test("dashboard.js: chartPrediction مرجع", "let chartPrediction" in js_content)
test("dashboard.js: تدمير الرسم القديم", "chartPrediction.destroy" in js_content)

# ===================================================
# 8. اختبار style.css
# ===================================================
print(f"\n{BOLD}=== 8. style.css ==={RESET}")

with open(os.path.join(BASE_DIR, "dashboard", "style.css"), encoding="utf-8") as f:
    css_content = f.read()

test("style.css: .prediction-panel موجود", ".prediction-panel" in css_content)
test("style.css: .prediction-controls موجود", ".prediction-controls" in css_content)
test("style.css: .prediction-control-group موجود", ".prediction-control-group" in css_content)
test("style.css: .prediction-label موجود", ".prediction-label" in css_content)
test("style.css: .prediction-select موجود", ".prediction-select" in css_content)
test("style.css: .prediction-toggle موجود", ".prediction-toggle" in css_content)
test("style.css: .prediction-chart-container موجود", ".prediction-chart-container" in css_content)
test("style.css: .prediction-explanation موجود", ".prediction-explanation" in css_content)
test("style.css: .prediction-loading موجود", ".prediction-loading" in css_content)

# ===================================================
# النتيجة النهائية
# ===================================================
print(f"\n{'='*50}")
total = passed + failed
print(f"النتيجة: {passed}/{total} اختبار نجح")
if failed == 0:
    print(f"{GREEN}جميع الاختبارات نجحت!{RESET}")
else:
    print(f"{RED}{failed} اختبار فشل.{RESET}")
    sys.exit(1)
