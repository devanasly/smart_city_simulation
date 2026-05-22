"""
نظام التنبؤ المحلي بالذكاء الاصطناعي
===================================
يقوم هذا النظام بقراءة البيانات التاريخية للمحاكاة وتوقع القيم المستقبلية
باستخدام خوارزميات إحصائية بسيطة تعتمد على مكتبة NumPy فقط.
"""

import numpy as np
import json
import os
import logging

# إعداد السجل
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def clean_series(data):
    """
    تنظيف سلسلة البيانات: إزالة القيم الفارغة أو غير الصالحة.
    
    المعاملات:
        data (list): قائمة من القيم العددية.
        
    تُرجع:
        list: قائمة نظيفة تحتوي على أرقام فقط.
    """
    cleaned = []
    for val in data:
        if val is not None and not np.isnan(val) and not np.isinf(val):
            cleaned.append(float(val))
    return cleaned

def predict_linear_regression(data, horizon):
    """
    توقع القيم المستقبلية باستخدام الانحدار الخطي (Linear Regression).
    يعتمد على دالة polyfit من NumPy لإنشاء خط اتجاه بناءً على البيانات السابقة.
    
    المعاملات:
        data (list): البيانات التاريخية.
        horizon (int): عدد النقاط المستقبلية المطلوب توقعها.
        
    تُرجع:
        list: قائمة بالقيم المتوقعة.
    """
    n = len(data)
    if n < 2:
        return [data[-1]] * horizon if n == 1 else []
        
    x = np.arange(n)
    y = np.array(data)
    
    # حساب معاملات الانحدار الخطي (من الدرجة الأولى)
    coefficients = np.polyfit(x, y, 1)
    poly = np.poly1d(coefficients)
    
    # توقع القيم المستقبلية
    future_x = np.arange(n, n + horizon)
    predictions = poly(future_x).tolist()
    
    return predictions

def predict_moving_average(data, horizon, window=10):
    """
    توقع القيم المستقبلية باستخدام المتوسط المتحرك (Moving Average).
    يستخدم متوسط آخر (window) نقطة كقيمة ثابتة للمستقبل.
    
    المعاملات:
        data (list): البيانات التاريخية.
        horizon (int): عدد النقاط المستقبلية المطلوب توقعها.
        window (int): حجم نافذة المتوسط المتحرك.
        
    تُرجع:
        list: قائمة بالقيم المتوقعة.
    """
    n = len(data)
    if n == 0:
        return []
        
    # تحديد حجم النافذة الفعلي
    actual_window = min(window, n)
    
    # حساب متوسط آخر (actual_window) نقطة
    recent_data = data[-actual_window:]
    avg_val = float(np.mean(recent_data))
    
    # المتوسط المتحرك البسيط يعطي قيمة ثابتة للمستقبل
    predictions = [avg_val] * horizon
    
    return predictions

def predict_exponential_smoothing(data, horizon, alpha=0.3):
    """
    توقع القيم المستقبلية باستخدام التمهيد الأسي (Exponential Smoothing).
    يعطي وزناً أكبر للقيم الأحدث في السلسلة الزمنية.
    
    المعاملات:
        data (list): البيانات التاريخية.
        horizon (int): عدد النقاط المستقبلية المطلوب توقعها.
        alpha (float): معامل التمهيد (بين 0 و 1).
        
    تُرجع:
        list: قائمة بالقيم المتوقعة.
    """
    n = len(data)
    if n == 0:
        return []
        
    # حساب القيمة الممهدة
    smoothed = data[0]
    for i in range(1, n):
        smoothed = alpha * data[i] + (1 - alpha) * smoothed
        
    # التمهيد الأسي البسيط يعطي قيمة ثابتة للمستقبل
    predictions = [smoothed] * horizon
    
    return predictions

def detect_trend(predicted_values):
    """
    تحديد اتجاه التنبؤ (متزايد، متناقص، مستقر).
    
    المعاملات:
        predicted_values (list): قائمة القيم المتوقعة.
        
    تُرجع:
        str: الاتجاه ('increasing', 'decreasing', 'stable').
    """
    if len(predicted_values) < 2:
        return "stable"
        
    first_val = predicted_values[0]
    last_val = predicted_values[-1]
    
    diff = last_val - first_val
    
    # تحديد عتبة الاستقرار (تغيير أقل من 1%)
    threshold = abs(first_val) * 0.01 if first_val != 0 else 0.01
    
    if diff > threshold:
        return "increasing"
    elif diff < -threshold:
        return "decreasing"
    else:
        return "stable"

def apply_constraints(predictions, metric):
    """
    تطبيق القيود على القيم المتوقعة بناءً على نوع المقياس.
    - لا توجد قيم سالبة (تُقيّد إلى 0).
    - النسب المئوية تُقيّد بين 0 و 1.
    - الأعداد تُقرّب إلى أعداد صحيحة.
    
    المعاملات:
        predictions (list): القيم المتوقعة.
        metric (str): اسم المقياس.
        
    تُرجع:
        list: القيم بعد تطبيق القيود.
    """
    percentage_metrics = ['hospital_occupancy', 'traffic_congestion']
    count_metrics = ['infected', 'recovered', 'deaths', 'total_deaths', 'epidemic_deaths', 
                     'births', 'total_births', 'population', 'total_population', 
                     'gas_queue_length', 'hospital_rejected']
                     
    constrained = []
    for val in predictions:
        # منع القيم السالبة
        val = max(0.0, val)
        
        # قيود النسب المئوية
        if metric in percentage_metrics:
            val = min(1.0, val)
            
        # تقريب الأعداد الصحيحة
        if metric in count_metrics:
            val = round(val)
            
        constrained.append(val)
        
    return constrained

def generate_prediction(data_file_path, metric, mode, horizon):
    """
    توليد تنبؤ بناءً على البيانات التاريخية وحفظه في ملف JSON.
    
    المعاملات:
        data_file_path (str): مسار ملف البيانات التاريخية (results.json أو ملف جلسة).
        metric (str): المقياس المطلوب توقعه.
        mode (str): وضع التنبؤ ('linear_regression', 'moving_average', 'exponential_smoothing').
        horizon (int): الأفق الزمني (عدد النقاط المستقبلية).
        
    تُرجع:
        dict: نتيجة التنبؤ أو رسالة خطأ.
    """
    try:
        # قراءة البيانات
        if not os.path.exists(data_file_path):
            return {"error": "ملف البيانات غير موجود"}
            
        with open(data_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        session_id = data.get("session_id", "unknown")
        time_series = data.get("time_series", [])
        
        if not time_series:
            return {"error": "لا توجد بيانات زمنية في الملف"}
            
        # استخراج القيم التاريخية
        historical_time = []
        historical_values = []
        
        for entry in time_series:
            if metric in entry and 'sim_time_minutes' in entry:
                historical_time.append(entry['sim_time_minutes'])
                historical_values.append(entry[metric])
                
        # تنظيف البيانات
        historical_values = clean_series(historical_values)
        
        # التحقق من وجود بيانات كافية (الحد الأدنى 5 نقاط)
        if len(historical_values) < 5:
            return {"error": "Not enough data for prediction"}
            
        # اختيار طريقة التنبؤ
        if mode == "linear_regression":
            predictions = predict_linear_regression(historical_values, horizon)
        elif mode == "moving_average":
            predictions = predict_moving_average(historical_values, horizon)
        elif mode == "exponential_smoothing":
            predictions = predict_exponential_smoothing(historical_values, horizon)
        else:
            return {"error": f"وضع التنبؤ غير معروف: {mode}"}
            
        # تطبيق القيود (لا قيم سالبة، تقريب، إلخ)
        predictions = apply_constraints(predictions, metric)
        
        # تحديد الاتجاه
        trend = detect_trend(predictions)
        
        # إنشاء محور الزمن المستقبلي
        last_time = historical_time[-1]
        time_step = 1.0 # افتراض أن الخطوة الزمنية هي 1 دقيقة محاكاة
        if len(historical_time) > 1:
            time_step = historical_time[-1] - historical_time[-2]
            
        future_time = [last_time + (i + 1) * time_step for i in range(horizon)]
        
        # بناء النتيجة
        result = {
            "session_id": session_id,
            "mode": mode,
            "horizon": horizon,
            "metric": metric,
            "trend": trend,
            "data_points_used": len(historical_values),
            "predictions": {
                metric: {
                    "future_time": future_time,
                    "values": predictions
                }
            }
        }
        
        return result
        
    except Exception as e:
        logging.error(f"خطأ أثناء التنبؤ: {e}")
        return {"error": str(e)}

def save_prediction(result, output_path):
    """
    حفظ نتيجة التنبؤ في ملف JSON.
    
    المعاملات:
        result (dict): نتيجة التنبؤ.
        output_path (str): مسار ملف الحفظ.
    """
    if "error" in result:
        logging.warning(f"لم يتم حفظ التنبؤ بسبب خطأ: {result['error']}")
        return False
        
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"خطأ أثناء حفظ التنبؤ: {e}")
        return False
