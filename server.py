"""
server.py
=========
خادم HTTP محلي بسيط للوحة التحكم الويب

يُوفِّر هذا الخادم:
1. تقديم ملفات لوحة التحكم (HTML/CSS/JS)
2. API لقراءة results.json
3. API لكتابة config.json
4. API لقائمة الجلسات وبياناتها (المسارات القديمة والجديدة)
5. API للتنبؤ بالذكاء الاصطناعي المحلي (POST /api/predict)
6. API لقراءة نتائج التنبؤ (GET /api/predictions)

طريقة التشغيل:
    python server.py

ثم افتح المتصفح على: http://localhost:8080
"""

import json
import os
import glob
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import sys

# --- المسارات (يجب تعريفها أولاً قبل أي استخدام) ---
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")
DATA_DIR      = os.path.join(BASE_DIR, "data")
CONFIG_PATH   = os.path.join(DATA_DIR, "config", "config.json")
RESULTS_PATH  = os.path.join(DATA_DIR, "results.json")
SESSIONS_DIR  = os.path.join(DATA_DIR, "sessions")
PREDICTIONS_PATH = os.path.join(DATA_DIR, "predictions.json")

PORT = 8080

# --- استيراد نظام التنبؤ (بعد تعريف BASE_DIR) ---
sys.path.insert(0, BASE_DIR)
try:
    from simulation.systems.prediction_system import generate_prediction, save_prediction
    _PREDICTION_AVAILABLE = True
except ImportError as _e:
    _PREDICTION_AVAILABLE = False
    print(f"[Server] تحذير: لم يتم تحميل prediction_system: {_e}")


class DashboardHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        """تقليل مخرجات السجل."""
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path

        # --- ملفات لوحة التحكم ---
        if path == "/" or path == "/index.html":
            self._serve_file(os.path.join(DASHBOARD_DIR, "index.html"), "text/html")

        elif path == "/style.css":
            self._serve_file(os.path.join(DASHBOARD_DIR, "style.css"), "text/css")

        elif path == "/dashboard.js":
            self._serve_file(os.path.join(DASHBOARD_DIR, "dashboard.js"), "application/javascript")

        # --- API: قراءة النتائج ---
        elif path == "/results" or path.startswith("/results?"):
            self._serve_file(RESULTS_PATH, "application/json")

        # --- API: قراءة نتائج التنبؤ ---
        elif path == "/api/predictions" or path.startswith("/api/predictions?"):
            if os.path.exists(PREDICTIONS_PATH):
                self._serve_file(PREDICTIONS_PATH, "application/json")
            else:
                # إعادة JSON فارغ بدلاً من 404 لتجنب "Unexpected end of JSON input"
                self._send_json({
                    "error": "لا توجد نتائج تنبؤ بعد. قم بتوليد تنبؤ أولاً."
                })

        # --- API القديم: قائمة الجلسات (للتوافق مع الكود القديم) ---
        elif path == "/list-sessions":
            self._list_sessions_summary()

        # --- API القديم: بيانات جلسة محددة ---
        elif path.startswith("/session/"):
            session_id = path.split("/session/")[-1].rstrip("/")
            session_file = os.path.join(SESSIONS_DIR, f"{session_id}.json")
            self._serve_file(session_file, "application/json")

        # --- API الجديد: قائمة الجلسات الكاملة ---
        elif path == "/api/sessions":
            self._list_sessions_summary()

        # --- API الجديد: بيانات جلسة كاملة بما فيها time_series ---
        elif path.startswith("/api/sessions/"):
            session_id = path.split("/api/sessions/")[-1].rstrip("/")
            session_file = os.path.join(SESSIONS_DIR, f"{session_id}.json")
            self._serve_file(session_file, "application/json")

        # --- ملفات البيانات المباشرة ---
        elif path.startswith("/data/"):
            file_path = os.path.join(BASE_DIR, path.lstrip("/"))
            if os.path.exists(file_path):
                self._serve_file(file_path, "application/json")
            else:
                self._send_404()

        else:
            self._send_404()

    def do_POST(self):
        parsed = urlparse(self.path)
        path   = parsed.path

        # --- API: توليد التنبؤ ---
        if path == "/api/predict":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                # التحقق من توفر نظام التنبؤ
                if not _PREDICTION_AVAILABLE:
                    self._send_json({
                        "status": "error",
                        "message": "نظام التنبؤ غير متاح. تأكد من وجود prediction_system.py"
                    }, 503)
                    return

                # تحليل الطلب
                req     = json.loads(body.decode("utf-8"))
                metric  = req.get("metric", "infected")
                mode    = req.get("mode", "linear_regression")
                horizon = int(req.get("horizon", 60))

                # توليد التنبؤ
                result = generate_prediction(RESULTS_PATH, metric, mode, horizon)

                if "error" not in result:
                    # حفظ نتائج التنبؤ
                    os.makedirs(DATA_DIR, exist_ok=True)
                    save_prediction(result, PREDICTIONS_PATH)
                    self._send_json({
                        "status":  "ok",
                        "message": "تم توليد التنبؤ بنجاح"
                    })
                else:
                    self._send_json({
                        "status":  "error",
                        "message": result["error"]
                    }, 400)

            except json.JSONDecodeError as e:
                self._send_json({
                    "status":  "error",
                    "message": f"طلب JSON غير صالح: {e}"
                }, 400)
            except Exception as e:
                self._send_json({
                    "status":  "error",
                    "message": str(e)
                }, 500)

        # --- API: كتابة الإعدادات ---
        elif path == "/write-config":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                config = json.loads(body.decode("utf-8"))
                os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                self._send_json({"status": "ok", "message": "تم حفظ الإعدادات"})
                print(f"[Server] تم تحديث config.json")
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)}, 500)

        else:
            self._send_404()

    def do_OPTIONS(self):
        """دعم CORS للطلبات من المتصفح."""
        self.send_response(200)
        self._add_cors_headers()
        self.end_headers()

    def _serve_file(self, file_path, content_type):
        """تقديم ملف من نظام الملفات."""
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", len(content))
            self._add_cors_headers()
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self._send_404()

    def _list_sessions_summary(self):
        """
        إرجاع قائمة ملخصة بالجلسات المحفوظة.
        تُرجع: session_id، المعاملات، ومدة المحاكاة فقط (بدون time_series لتوفير الحجم).
        """
        sessions = []
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        for session_file in sorted(
            glob.glob(os.path.join(SESSIONS_DIR, "*.json")),
            reverse=True
        ):
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sessions.append({
                    "session_id":                  data.get("session_id", ""),
                    "parameters":                  data.get("parameters", {}),
                    "simulation_duration_minutes": data.get("simulation_duration_minutes", 0),
                    "time_series_length":          len(data.get("time_series", [])),
                })
            except Exception:
                pass
        self._send_json(sessions)

    def _send_json(self, data, status=200):
        """إرسال استجابة JSON مع ترويسات صحيحة."""
        content = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(content))
        self._add_cors_headers()
        self.end_headers()
        self.wfile.write(content)

    def _send_404(self):
        self._send_json({"error": "not found"}, 404)

    def _add_cors_headers(self):
        """إضافة ترويسات CORS للسماح بالطلبات من أي مصدر."""
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")


def run_server():
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

    # إنشاء results.json فارغ إذا لم يكن موجوداً
    if not os.path.exists(RESULTS_PATH):
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "session_id":       "none",
                "sim_time_minutes": 0,
                "current_metrics":  {},
                "time_series":      []
            }, f, ensure_ascii=False)

    # إنشاء predictions.json فارغ إذا لم يكن موجوداً
    # هذا يمنع خطأ "Unexpected end of JSON input" عند أول GET /api/predictions
    if not os.path.exists(PREDICTIONS_PATH):
        with open(PREDICTIONS_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "error": "لا توجد نتائج تنبؤ بعد. قم بتوليد تنبؤ أولاً."
            }, f, ensure_ascii=False)

    HTTPServer.allow_reuse_address = True
    server = HTTPServer(("0.0.0.0", PORT), DashboardHandler)
    print(f"[Server] خادم لوحة التحكم يعمل على: http://localhost:{PORT}")
    print(f"[Server] افتح المتصفح على: http://localhost:{PORT}")
    print(f"[Server] اضغط Ctrl+C للإيقاف")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Server] تم إيقاف الخادم.")
        server.server_close()


if __name__ == "__main__":
    run_server()
