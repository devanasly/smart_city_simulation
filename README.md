REM Smart City Simulation System
REM طريقة التشغيل على Windows باستخدام Anaconda Prompt

REM 1. إنشاء بيئة Conda
conda create -n smartcity python=3.11 -y

REM 2. تفعيل البيئة
conda activate smartcity

REM 3. تثبيت المكتبات المطلوبة
pip install pygame numpy matplotlib pandas fastapi uvicorn

REM 4. الانتقال إلى مجلد المشروع على سطح المكتب
cd /d %USERPROFILE%\Desktop\smart_city_simulation

REM 5. تشغيل لوحة التحكم
python server.py

REM بعد تشغيل server.py افتح المتصفح على الرابط التالي:
REM http://localhost:8080

REM 6. افتح Anaconda Prompt جديد، ثم نفذ الأوامر التالية لتشغيل المحاكاة

conda activate smartcity
cd /d %USERPROFILE%\Desktop\smart_city_simulation
python main.py