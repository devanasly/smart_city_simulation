/**
 * dashboard.js — لوحة التحكم الرئيسية لنظام محاكاة المدينة الذكية
 * ================================================================
 * الوظائف الرئيسية:
 * 1. تحديث تلقائي للبيانات الحية من results.json كل ثانيتين
 * 2. رسوم بيانية حية بـ Chart.js (SIR، السكان، المستشفى، الوقود، المرور، الديموغرافيا)
 * 3. نظام مقارنة جلسات متكامل مع مقاييس متعددة قابلة للتبديل
 * 4. صندوق معلومات تفاعلي عند النقر على أي نقطة في أي رسم بياني
 * 5. ميزة تحليل النطاق الزمني: اختيار نقطة بداية ونهاية بالنقر
 *    وعرض صندوق تحليل عائم يحتوي على إحصائيات مفصّلة خاصة بكل نظام
 * 6. تمييز بصري للنطاق المحدد على الرسم البياني
 */

"use strict";

// ===================================================
// الثوابت والمتغيرات العامة
// ===================================================

const REFRESH_INTERVAL = 2000;   // تحديث كل ثانيتين
const MAX_POINTS       = 150;    // أقصى عدد نقاط على الرسوم الحية

/** جميع المقاييس المدعومة مع تسمياتها العربية */
const METRIC_LABELS = {
  infected:               "المصابون",
  recovered:              "المتعافون",
  susceptible:            "غير المصابين",
  total_deaths:           "إجمالي الوفيات",
  total_births:           "إجمالي المواليد",
  total_population:       "إجمالي السكان",
  hospital_occupancy:     "إشغال المستشفى",
  hospital_rejected:      "الحالات المرفوضة",
  gas_queue_length:       "طابور الوقود",
  gas_avg_wait:           "متوسط وقت الانتظار (ث)",
  traffic_congestion:     "ازدحام المرور (%)",
  traffic_avg_delay:      "متوسط تأخير المرور (ث)",
  epidemic_deaths:        "وفيات الوباء",
  effective_birth_rate:   "معدل المواليد الفعلي",
};

/** لوحة الألوان الموحّدة */
const COLORS = {
  susceptible: "#58a6ff",
  infected:    "#f85149",
  recovered:   "#3fb950",
  population:  "#a371f7",
  births:      "#3ddc84",
  deaths:      "#e05252",
  hospital:    "#d29922",
  gas:         "#f0c040",
  traffic:     "#ff7b72",
  sessionA:    "#58a6ff",
  sessionB:    "#f85149",
  rangeHighlight: "rgba(88,166,255,0.12)",
  rangeBorder:    "rgba(88,166,255,0.7)",
};

// مراجع الرسوم البيانية
let chartSIR        = null;
let chartPop        = null;
let chartHosp       = null;
let chartGas        = null;
let chartTraffic    = null;
let chartDemography = null;
let chartCompare    = null;

// حالة الاتصال
let isConnected  = false;
let refreshTimer = null;

// حالة المقارنة
let selectedSessionA = null;
let selectedSessionB = null;
let selectedMetric   = "infected";
let sessionDataA     = null;
let sessionDataB     = null;

// مرجع صندوق المعلومات التفاعلي (نقطة واحدة)
let infoBox = null;

// ===================================================
// حالة تحليل النطاق الزمني
// ===================================================

/**
 * كل رسم بياني له حالة نطاق مستقلة:
 * - mode: "idle" | "selecting_start" | "selecting_end" | "selected"
 * - startIndex / endIndex: مؤشرا النقطتين المحددتين
 * - chartRef: مرجع كائن Chart.js
 * - metricKeys: مفاتيح البيانات المرتبطة بهذا الرسم
 * - systemType: نوع النظام لاستخراج الإحصائيات الخاصة
 */
const rangeState = {};

/** تعريف الرسوم البيانية وأنظمتها */
const CHART_DEFS = {
  chartSIR:        { systemType: "epidemic",   metricKeys: ["susceptible","infected","recovered"] },
  chartPop:        { systemType: "population", metricKeys: ["total_population"] },
  chartHosp:       { systemType: "hospital",   metricKeys: ["hospital_occupancy"] },
  chartGas:        { systemType: "gas",        metricKeys: ["gas_queue_length"] },
  chartTraffic:    { systemType: "traffic",    metricKeys: ["traffic_congestion"] },
  chartDemography: { systemType: "demography", metricKeys: ["total_births","total_deaths"] },
  chartCompare:    { systemType: "compare",    metricKeys: [] },
};

// بيانات السلسلة الزمنية الحية (للوصول إليها من دوال النطاق)
let liveTimeSeries = [];


// ===================================================
// تهيئة الرسوم البيانية
// ===================================================

/**
 * بناء خيارات Chart.js المشتركة مع دعم النقر لاختيار النطاق الزمني.
 * @param {string} chartId - معرّف الرسم البياني
 * @param {string} titleText - عنوان الرسم
 * @param {object} extraScaleY - خيارات إضافية لمحور Y
 */
function getChartOptions(chartId = "", titleText = "", extraScaleY = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 300 },
    plugins: {
      legend: {
        labels: { color: "#8b949e", font: { size: 11 } }
      },
      title: {
        display: !!titleText,
        text: titleText,
        color: "#e6edf3",
        font: { size: 13, weight: "bold" }
      },
      // إضافة إضاءة النطاق المحدد كـ plugin مخصص
      rangeHighlightPlugin: {
        id: "rangeHighlightPlugin",
      }
    },
    scales: {
      x: {
        ticks: { color: "#8b949e", maxTicksLimit: 8, font: { size: 10 } },
        grid:  { color: "#21262d" }
      },
      y: {
        ticks: { color: "#8b949e", font: { size: 10 } },
        grid:  { color: "#21262d" },
        beginAtZero: true,
        ...extraScaleY
      }
    },
    onClick: (event, elements, chart) => {
      // --- منطق اختيار النطاق الزمني ---
      // عند النقر على الرسم البياني يتم تحديد نقطة البداية أو النهاية
      handleChartClick(chartId, chart, elements, event);
    }
  };
}

/** تهيئة جميع الرسوم البيانية عند تحميل الصفحة */
function initCharts() {

  // تسجيل plugin رسم تمييز النطاق
  Chart.register(rangeHighlightPlugin);

  // --- رسم SIR ---
  chartSIR = new Chart(document.getElementById("chartSIR"), {
    type: "line",
    data: {
      labels: [],
      datasets: [
        { label: "قابل للإصابة (S)", data: [], borderColor: COLORS.susceptible, backgroundColor: "rgba(88,166,255,0.1)",  tension: 0.4, fill: true,  pointRadius: 2 },
        { label: "مصاب (I)",         data: [], borderColor: COLORS.infected,    backgroundColor: "rgba(248,81,73,0.1)",   tension: 0.4, fill: true,  pointRadius: 2 },
        { label: "متعافٍ (R)",        data: [], borderColor: COLORS.recovered,   backgroundColor: "rgba(63,185,80,0.1)",  tension: 0.4, fill: true,  pointRadius: 2 },
      ]
    },
    options: getChartOptions("chartSIR")
  });
  initRangeState("chartSIR", chartSIR);

  // --- رسم السكان ---
  chartPop = new Chart(document.getElementById("chartPop"), {
    type: "line",
    data: {
      labels: [],
      datasets: [
        { label: "إجمالي السكان", data: [], borderColor: COLORS.population, backgroundColor: "rgba(163,113,247,0.1)", tension: 0.4, fill: true, pointRadius: 2 }
      ]
    },
    options: getChartOptions("chartPop")
  });
  initRangeState("chartPop", chartPop);

  // --- رسم المستشفى ---
  chartHosp = new Chart(document.getElementById("chartHosp"), {
    type: "bar",
    data: {
      labels: [],
      datasets: [
        { label: "المرضى المقبولون", data: [], backgroundColor: "rgba(210,153,34,0.7)", borderColor: COLORS.hospital, borderWidth: 1 }
      ]
    },
    options: getChartOptions("chartHosp")
  });
  initRangeState("chartHosp", chartHosp);

  // --- رسم طابور الوقود ---
  chartGas = new Chart(document.getElementById("chartGas"), {
    type: "line",
    data: {
      labels: [],
      datasets: [
        { label: "طول الطابور", data: [], borderColor: COLORS.gas, backgroundColor: "rgba(240,192,64,0.15)", tension: 0.4, fill: true, pointRadius: 2 }
      ]
    },
    options: getChartOptions("chartGas")
  });
  initRangeState("chartGas", chartGas);

  // --- رسم الازدحام ---
  chartTraffic = new Chart(document.getElementById("chartTraffic"), {
    type: "line",
    data: {
      labels: [],
      datasets: [
        { label: "مستوى الازدحام (%)", data: [], borderColor: COLORS.traffic, backgroundColor: "rgba(255,123,114,0.1)", tension: 0.4, fill: true, pointRadius: 2 }
      ]
    },
    options: getChartOptions("chartTraffic", "", { min: 0, max: 100 })
  });
  initRangeState("chartTraffic", chartTraffic);

  // --- رسم الديموغرافيا ---
  chartDemography = new Chart(document.getElementById("chartDemography"), {
    type: "line",
    data: {
      labels: [],
      datasets: [
        { label: "المولودون التراكميون", data: [], borderColor: COLORS.births, backgroundColor: "rgba(61,220,132,0.1)", tension: 0.4, fill: true,  pointRadius: 0 },
        { label: "المتوفون التراكميون",  data: [], borderColor: COLORS.deaths, backgroundColor: "rgba(224,82,82,0.1)",  tension: 0.4, fill: true,  pointRadius: 0 },
      ]
    },
    options: getChartOptions("chartDemography")
  });
  initRangeState("chartDemography", chartDemography);
}


// ===================================================
// Plugin مخصص لرسم تمييز النطاق على الرسم البياني
// ===================================================

/**
 * plugin مخصص يرسم مستطيلاً شفافاً فوق النطاق المحدد
 * بين نقطة البداية ونقطة النهاية على محور X.
 */
const rangeHighlightPlugin = {
  id: "rangeHighlightPlugin",
  afterDraw(chart) {
    // البحث عن حالة النطاق لهذا الرسم
    const chartId = getChartIdFromRef(chart);
    if (!chartId) return;
    const state = rangeState[chartId];
    if (!state) return;

    // لا نرسم شيئاً إذا لم يتم اختيار نقطة بداية على الأقل
    if (state.startIndex === null) return;

    const { ctx, chartArea, scales } = chart;
    const xScale = scales.x;
    if (!xScale || !chartArea) return;

    const startIdx = state.startIndex;
    const endIdx   = state.endIndex !== null ? state.endIndex : startIdx;

    // حساب إحداثيات البداية والنهاية على محور X
    const x1 = xScale.getPixelForValue(Math.min(startIdx, endIdx));
    const x2 = xScale.getPixelForValue(Math.max(startIdx, endIdx));

    ctx.save();

    // رسم المستطيل الشفاف للنطاق المحدد
    ctx.fillStyle = COLORS.rangeHighlight;
    ctx.fillRect(x1, chartArea.top, x2 - x1, chartArea.bottom - chartArea.top);

    // رسم حدود النطاق
    ctx.strokeStyle = COLORS.rangeBorder;
    ctx.lineWidth   = 1.5;
    ctx.setLineDash([4, 3]);

    // خط البداية
    ctx.beginPath();
    ctx.moveTo(x1, chartArea.top);
    ctx.lineTo(x1, chartArea.bottom);
    ctx.stroke();

    // خط النهاية (فقط إذا تم تحديد نقطة النهاية)
    if (state.endIndex !== null) {
      ctx.beginPath();
      ctx.moveTo(x2, chartArea.top);
      ctx.lineTo(x2, chartArea.bottom);
      ctx.stroke();
    }

    ctx.restore();
  }
};

/** استخراج معرّف الرسم البياني من مرجع Chart.js */
function getChartIdFromRef(chartRef) {
  for (const [id, state] of Object.entries(rangeState)) {
    if (state.chartRef === chartRef) return id;
  }
  return null;
}


// ===================================================
// منطق اختيار النطاق الزمني
// ===================================================

/**
 * تهيئة حالة النطاق لرسم بياني معين.
 * @param {string} chartId - معرّف الرسم
 * @param {object} chartRef - مرجع كائن Chart.js
 */
function initRangeState(chartId, chartRef) {
  rangeState[chartId] = {
    chartRef,
    mode:       "idle",      // idle | selecting_start | selecting_end | selected
    startIndex: null,        // مؤشر نقطة البداية
    endIndex:   null,        // مؤشر نقطة النهاية
  };
}

/**
 * معالجة النقر على الرسم البياني لاختيار نطاق زمني.
 *
 * آلية الاختيار:
 * - النقر الأول: يحدد نقطة البداية (mode → selecting_end)
 * - النقر الثاني: يحدد نقطة النهاية ويعرض التحليل (mode → selected)
 * - النقر الثالث: يعيد التهيئة ويبدأ من جديد (mode → selecting_end)
 *
 * @param {string} chartId - معرّف الرسم
 * @param {object} chart - كائن Chart.js
 * @param {Array} elements - العناصر المنقورة
 * @param {object} event - حدث النقر
 */
function handleChartClick(chartId, chart, elements, event) {
  const state = rangeState[chartId];
  if (!state) return;

  // الحصول على مؤشر النقطة المنقورة
  // إذا لم تكن هناك نقطة مباشرة، نحسب أقرب نقطة من موضع النقر
  let pointIndex = null;
  if (elements && elements.length > 0) {
    pointIndex = elements[0].index;
  } else {
    // حساب أقرب نقطة من موضع X للنقر
    pointIndex = getNearestPointIndex(chart, event);
  }

  if (pointIndex === null || pointIndex < 0) return;

  if (state.mode === "idle" || state.mode === "selected") {
    // النقر الأول أو إعادة الاختيار: تحديد نقطة البداية
    state.startIndex = pointIndex;
    state.endIndex   = null;
    state.mode       = "selecting_end";
    updateRangeStatusBar(chartId, "انقر على نقطة النهاية لإكمال التحليل");
    hideRangeAnalysisBox();
    chart.update("none");

  } else if (state.mode === "selecting_end") {
    // النقر الثاني: تحديد نقطة النهاية وعرض التحليل
    state.endIndex = pointIndex;

    // التأكد من أن البداية قبل النهاية
    if (state.endIndex < state.startIndex) {
      [state.startIndex, state.endIndex] = [state.endIndex, state.startIndex];
    }

    // التحقق من وجود نقطتين على الأقل
    if (state.endIndex - state.startIndex < 1) {
      updateRangeStatusBar(chartId, "يجب اختيار نطاق يحتوي على نقطتين على الأقل. انقر مجدداً.");
      state.startIndex = null;
      state.endIndex   = null;
      state.mode       = "idle";
      chart.update("none");
      return;
    }

    state.mode = "selected";
    updateRangeStatusBar(chartId, `تم تحديد النطاق: ${chart.data.labels[state.startIndex]} → ${chart.data.labels[state.endIndex]}`);
    chart.update("none");

    // عرض صندوق التحليل
    showRangeAnalysisBox(chartId, chart, state.startIndex, state.endIndex, event);
  }
}

/**
 * حساب أقرب نقطة بيانات من موضع X للنقر على الرسم البياني.
 * يُستخدم عندما لا يكون المستخدم قد نقر على نقطة مباشرة.
 */
function getNearestPointIndex(chart, event) {
  try {
    const xScale = chart.scales.x;
    if (!xScale) return null;
    const rect    = chart.canvas.getBoundingClientRect();
    const mouseX  = event.clientX - rect.left;
    const dataLen = chart.data.labels.length;
    if (dataLen === 0) return null;

    let nearest = 0;
    let minDist = Infinity;
    for (let i = 0; i < dataLen; i++) {
      const px   = xScale.getPixelForValue(i);
      const dist = Math.abs(px - mouseX);
      if (dist < minDist) { minDist = dist; nearest = i; }
    }
    return nearest;
  } catch { return null; }
}

/**
 * تحديث شريط الحالة أسفل الرسم البياني.
 * يُظهر تعليمات الاختيار أو ملخص النطاق المحدد.
 */
function updateRangeStatusBar(chartId, message) {
  const barId = chartId + "_rangeStatus";
  const bar   = document.getElementById(barId);
  if (!bar) return;
  // إذا اكتمل التحديد، أضف زر "عرض التفاصيل" بجانب النص
  if (message && message.startsWith("تم تحديد النطاق")) {
    bar.innerHTML =
      `<span>${message}</span>` +
      `<button class="btn-range-details" onclick="openRangeDetailModal('${chartId}')">عرض التفاصيل</button>`;
  } else {
    bar.textContent = message;
  }
}

/**
 * إعادة تهيئة النطاق المحدد لرسم بياني معين.
 * يُستدعى عند الضغط على زر "مسح النطاق".
 */
function clearRange(chartId) {
  const state = rangeState[chartId];
  if (!state) return;
  state.startIndex = null;
  state.endIndex   = null;
  state.mode       = "idle";
  updateRangeStatusBar(chartId, "انقر على نقطة البداية لبدء التحليل");
  hideRangeAnalysisBox();
  closeRangeDetailModal();
  if (state.chartRef) state.chartRef.update("none");
}


// ===================================================
// صندوق التحليل العائم للنطاق الزمني
// ===================================================

let rangeAnalysisBox = null;

/**
 * عرض صندوق التحليل العائم بعد اختيار النطاق الزمني.
 *
 * يحسب ويعرض:
 * - الإحصائيات العامة (متوسط، أدنى، أقصى، تغيير، نسبة تغيير، معدل/دقيقة)
 * - الإحصائيات الخاصة بكل نظام (وباء، سكان، مستشفى، وقود، مرور)
 *
 * @param {string} chartId - معرّف الرسم البياني
 * @param {object} chart - كائن Chart.js
 * @param {number} startIdx - مؤشر نقطة البداية
 * @param {number} endIdx - مؤشر نقطة النهاية
 * @param {object} event - حدث النقر (لتحديد موضع الصندوق)
 */
function showRangeAnalysisBox(chartId, chart, startIdx, endIdx, event) {
  const def        = CHART_DEFS[chartId] || {};
  const systemType = def.systemType || "generic";
  const dataset    = chart.data.datasets[0];
  const labels     = chart.data.labels;

  if (!dataset || !labels || labels.length === 0) {
    showRangeError("لا توجد بيانات متاحة في هذا الرسم البياني.");
    return;
  }

  // --- استخراج بيانات النطاق ---
  // getRangeData تُعيد مصفوفة القيم بين مؤشري البداية والنهاية
  const rangeData = getRangeData(dataset.data, startIdx, endIdx);
  if (!rangeData || rangeData.length < 2) {
    showRangeError("النطاق المحدد لا يحتوي على بيانات كافية (يجب نقطتان على الأقل).");
    return;
  }

  // --- الإحصائيات العامة ---
  const startLabel   = labels[startIdx]  || String(startIdx);
  const endLabel     = labels[endIdx]    || String(endIdx);
  const startValue   = rangeData[0];
  const endValue     = rangeData[rangeData.length - 1];
  const avgVal       = calculateAverage(rangeData);
  const minVal       = calculateMin(rangeData);
  const maxVal       = calculateMax(rangeData);
  const totalChange  = calculateTotalChange(startValue, endValue);
  const pctChange    = calculatePercentageChange(startValue, endValue);
  const duration     = endIdx - startIdx;  // عدد النقاط = الفارق الزمني التقريبي
  const ratePerMin   = calculateRatePerMinute(startValue, endValue, duration);

  // --- اسم المقياس ---
  const metricName   = dataset.label || METRIC_LABELS[def.metricKeys?.[0]] || "مقياس";
  const chartTitle   = chart.options.plugins?.title?.text || metricName;

  // --- معرّف الجلسة ---
  const sessionIdEl  = document.getElementById("sessionId");
  const sessionLabel = sessionIdEl?.textContent || "الجلسة الحالية";

  // --- الإحصائيات الخاصة بالنظام ---
  // getSystemSpecificStats تُعيد HTML لإحصائيات إضافية حسب نوع النظام
  const specificHTML = getSystemSpecificStats(systemType, chartId, chart, startIdx, endIdx);

  // --- بناء محتوى الصندوق ---
  const html = `
    <div class="ra-header">
      <div class="ra-title-group">
        <span class="ra-icon">&#9741;</span>
        <div>
          <div class="ra-title">تحليل النطاق الزمني</div>
          <div class="ra-subtitle">${metricName}</div>
        </div>
      </div>
      <button class="ra-close" onclick="hideRangeAnalysisBox()" title="إغلاق">&#x2715;</button>
    </div>

    <div class="ra-body">

      <!-- معلومات النطاق -->
      <div class="ra-section">
        <div class="ra-section-title">معلومات النطاق</div>
        <div class="ra-grid">
          <div class="ra-row"><span class="ra-key">الرسم البياني</span><span class="ra-val">${metricName}</span></div>
          <div class="ra-row"><span class="ra-key">معرّف الجلسة</span><span class="ra-val">${sessionLabel}</span></div>
          <div class="ra-row"><span class="ra-key">زمن البداية</span><span class="ra-val ra-time">${startLabel}</span></div>
          <div class="ra-row"><span class="ra-key">زمن النهاية</span><span class="ra-val ra-time">${endLabel}</span></div>
          <div class="ra-row"><span class="ra-key">المدة</span><span class="ra-val">${duration} نقطة</span></div>
        </div>
      </div>

      <!-- الإحصائيات الأساسية -->
      <div class="ra-section">
        <div class="ra-section-title">الإحصائيات الأساسية</div>
        <div class="ra-grid">
          <div class="ra-row"><span class="ra-key">قيمة البداية</span><span class="ra-val">${fmtNum(startValue)}</span></div>
          <div class="ra-row"><span class="ra-key">قيمة النهاية</span><span class="ra-val">${fmtNum(endValue)}</span></div>
          <div class="ra-row"><span class="ra-key">الحد الأدنى</span><span class="ra-val ra-min">${fmtNum(minVal)}</span></div>
          <div class="ra-row"><span class="ra-key">الحد الأقصى</span><span class="ra-val ra-max">${fmtNum(maxVal)}</span></div>
          <div class="ra-row"><span class="ra-key">المتوسط</span><span class="ra-val ra-avg">${fmtNum(avgVal)}</span></div>
        </div>
      </div>

      <!-- إحصائيات التغيير -->
      <div class="ra-section">
        <div class="ra-section-title">إحصائيات التغيير</div>
        <div class="ra-grid">
          <div class="ra-row">
            <span class="ra-key">إجمالي التغيير</span>
            <span class="ra-val ${totalChange >= 0 ? "ra-positive" : "ra-negative"}">
              ${totalChange >= 0 ? "+" : ""}${fmtNum(totalChange)}
            </span>
          </div>
          <div class="ra-row">
            <span class="ra-key">نسبة التغيير</span>
            <span class="ra-val ${pctChange === null ? "" : pctChange >= 0 ? "ra-positive" : "ra-negative"}">
              ${pctChange === null ? "N/A" : (pctChange >= 0 ? "+" : "") + pctChange.toFixed(2) + "%"}
            </span>
          </div>
          <div class="ra-row">
            <span class="ra-key">معدل التغيير/نقطة</span>
            <span class="ra-val ${ratePerMin >= 0 ? "ra-positive" : "ra-negative"}">
              ${ratePerMin >= 0 ? "+" : ""}${fmtNum(ratePerMin)}
            </span>
          </div>
        </div>
      </div>

      ${specificHTML ? `
      <!-- الإحصائيات الخاصة بالنظام -->
      <div class="ra-section ra-specific">
        <div class="ra-section-title">إحصائيات ${getSystemLabel(systemType)}</div>
        <div class="ra-grid">${specificHTML}</div>
      </div>` : ""}

    </div>

    <div class="ra-footer">
      <button class="ra-btn-clear" onclick="clearRange('${chartId}')">مسح النطاق</button>
      <span class="ra-hint">انقر خارج الصندوق للإغلاق</span>
    </div>
  `;

  // إنشاء الصندوق إذا لم يكن موجوداً
  if (!rangeAnalysisBox) {
    rangeAnalysisBox = document.createElement("div");
    rangeAnalysisBox.id        = "rangeAnalysisBox";
    rangeAnalysisBox.className = "range-analysis-box";
    document.body.appendChild(rangeAnalysisBox);
  }

  rangeAnalysisBox.innerHTML     = html;
  rangeAnalysisBox.style.display = "flex";

  // تحديد موضع الصندوق بجانب موضع النقر
  positionRangeBox(event);
}

/** تحديد موضع صندوق التحليل بجانب موضع النقر مع تجنب الخروج عن الشاشة */
function positionRangeBox(event) {
  if (!rangeAnalysisBox) return;
  const margin = 20;
  let left = event.pageX + margin;
  let top  = event.pageY - 60;

  rangeAnalysisBox.style.left = `${left}px`;
  rangeAnalysisBox.style.top  = `${top}px`;

  requestAnimationFrame(() => {
    if (!rangeAnalysisBox) return;
    const r = rangeAnalysisBox.getBoundingClientRect();
    if (r.right  > window.innerWidth  - margin) left = event.pageX - r.width  - margin;
    if (r.bottom > window.innerHeight - margin) top  = event.pageY - r.height + 40;
    if (top < margin) top = margin;
    rangeAnalysisBox.style.left = `${left}px`;
    rangeAnalysisBox.style.top  = `${top}px`;
  });
}

function hideRangeAnalysisBox() {
  if (rangeAnalysisBox) rangeAnalysisBox.style.display = "none";
}

function showRangeError(message) {
  if (!rangeAnalysisBox) {
    rangeAnalysisBox = document.createElement("div");
    rangeAnalysisBox.id        = "rangeAnalysisBox";
    rangeAnalysisBox.className = "range-analysis-box";
    document.body.appendChild(rangeAnalysisBox);
  }
  rangeAnalysisBox.innerHTML = `
    <div class="ra-header">
      <span class="ra-title">تنبيه</span>
      <button class="ra-close" onclick="hideRangeAnalysisBox()">&#x2715;</button>
    </div>
    <div class="ra-body">
      <div class="ra-error-msg">${message}</div>
    </div>`;
  rangeAnalysisBox.style.display = "flex";
}

/** إغلاق الصندوق عند النقر خارجه */
document.addEventListener("click", e => {
  if (rangeAnalysisBox && rangeAnalysisBox.style.display === "flex") {
    if (!rangeAnalysisBox.contains(e.target) && !e.target.closest("canvas")) {
      hideRangeAnalysisBox();
    }
  }
  if (infoBox && infoBox.style.display === "block") {
    if (!infoBox.contains(e.target) && !e.target.closest("canvas")) hideInfoBox();
  }
});


// ===================================================
// دوال الحساب المساعدة للنطاق الزمني
// ===================================================

/**
 * استخراج بيانات النطاق بين مؤشري البداية والنهاية.
 * @param {Array} data - مصفوفة البيانات الكاملة
 * @param {number} startIndex - مؤشر البداية (شامل)
 * @param {number} endIndex - مؤشر النهاية (شامل)
 * @returns {Array} مصفوفة القيم في النطاق المحدد
 */
function getRangeData(data, startIndex, endIndex) {
  if (!data || data.length === 0) return [];
  const s = Math.max(0, Math.min(startIndex, endIndex));
  const e = Math.min(data.length - 1, Math.max(startIndex, endIndex));
  return data.slice(s, e + 1).filter(v => v != null);
}

/**
 * حساب متوسط قيم النطاق.
 * @param {Array} rangeData - مصفوفة القيم
 * @returns {number} المتوسط الحسابي
 */
function calculateAverage(rangeData) {
  if (!rangeData || rangeData.length === 0) return 0;
  return rangeData.reduce((a, b) => a + b, 0) / rangeData.length;
}

/**
 * حساب الحد الأدنى في النطاق.
 * @param {Array} rangeData - مصفوفة القيم
 * @returns {number} القيمة الدنيا
 */
function calculateMin(rangeData) {
  if (!rangeData || rangeData.length === 0) return 0;
  return Math.min(...rangeData);
}

/**
 * حساب الحد الأقصى في النطاق.
 * @param {Array} rangeData - مصفوفة القيم
 * @returns {number} القيمة القصوى
 */
function calculateMax(rangeData) {
  if (!rangeData || rangeData.length === 0) return 0;
  return Math.max(...rangeData);
}

/**
 * حساب إجمالي التغيير (النهاية - البداية).
 * @param {number} startValue - قيمة البداية
 * @param {number} endValue - قيمة النهاية
 * @returns {number} إجمالي التغيير
 */
function calculateTotalChange(startValue, endValue) {
  return (endValue ?? 0) - (startValue ?? 0);
}

/**
 * حساب نسبة التغيير المئوية.
 * إذا كانت قيمة البداية صفراً يُعيد null لتجنب القسمة على صفر.
 * @param {number} startValue - قيمة البداية
 * @param {number} endValue - قيمة النهاية
 * @returns {number|null} نسبة التغيير أو null
 */
function calculatePercentageChange(startValue, endValue) {
  if (startValue === 0 || startValue == null) return null;
  return (((endValue ?? 0) - startValue) / Math.abs(startValue)) * 100;
}

/**
 * حساب معدل التغيير لكل نقطة زمنية.
 * @param {number} startValue - قيمة البداية
 * @param {number} endValue - قيمة النهاية
 * @param {number} duration - عدد النقاط (الفارق الزمني)
 * @returns {number} معدل التغيير لكل نقطة
 */
function calculateRatePerMinute(startValue, endValue, duration) {
  if (!duration || duration === 0) return 0;
  return ((endValue ?? 0) - (startValue ?? 0)) / duration;
}

/**
 * حساب مجموع قيم النطاق.
 * @param {Array} data - مصفوفة البيانات الكاملة
 * @param {number} startIndex - مؤشر البداية
 * @param {number} endIndex - مؤشر النهاية
 * @returns {number} مجموع القيم في النطاق
 */
function calculateRangeSum(data, startIndex, endIndex) {
  const rangeData = getRangeData(data, startIndex, endIndex);
  return rangeData.reduce((a, b) => a + b, 0);
}

/**
 * استخراج الإحصائيات الخاصة بكل نظام.
 *
 * تُعيد HTML يحتوي على صفوف إحصائيات إضافية حسب نوع النظام:
 * - epidemic: متوسط المصابين، المتعافين، الإصابات الجديدة، الوفيات
 * - population: المواليد، الوفيات، صافي التغيير، المتوسط
 * - hospital: متوسط الإشغال، الأقصى، المرفوضون، معدل النمو
 * - gas: متوسط الطابور، الأقصى، متوسط الانتظار، معدل النمو
 * - traffic: متوسط الازدحام، الأقصى، متوسط التأخير، معدل النمو
 *
 * @param {string} systemType - نوع النظام
 * @param {string} chartId - معرّف الرسم البياني
 * @param {object} chart - كائن Chart.js
 * @param {number} startIdx - مؤشر البداية
 * @param {number} endIdx - مؤشر النهاية
 * @returns {string} HTML للإحصائيات الخاصة
 */
function getSystemSpecificStats(systemType, chartId, chart, startIdx, endIdx) {
  // استخراج بيانات السلسلة الزمنية الحية للنطاق المحدد
  const ts = liveTimeSeries;
  const s  = Math.max(0, Math.min(startIdx, endIdx));
  const e  = Math.min((ts.length || 0) - 1, Math.max(startIdx, endIdx));
  const slice = ts.length > 0 ? ts.slice(s, e + 1) : [];

  // دالة مساعدة لاستخراج مصفوفة مقياس من السلسلة الزمنية
  const extract = (key) => slice.map(p => p[key] ?? 0);
  const avg     = (arr)  => arr.length ? arr.reduce((a,b) => a+b, 0) / arr.length : 0;
  const sum     = (arr)  => arr.reduce((a,b) => a+b, 0);
  const max     = (arr)  => arr.length ? Math.max(...arr) : 0;
  const row     = (k, v) => `<div class="ra-row"><span class="ra-key">${k}</span><span class="ra-val">${v}</span></div>`;

  switch (systemType) {

    case "epidemic": {
      // --- إحصائيات الوباء ---
      const infArr  = extract("infected");
      const recArr  = extract("recovered");
      const dthArr  = extract("epidemic_deaths");
      const avgInf  = avg(infArr);
      const avgRec  = avg(recArr);
      // الإصابات الجديدة = الفرق بين أول وآخر قيمة للمصابين
      const newInf  = slice.length >= 2 ? (slice[slice.length-1].infected ?? 0) - (slice[0].infected ?? 0) : "N/A";
      const newRec  = slice.length >= 2 ? (slice[slice.length-1].recovered ?? 0) - (slice[0].recovered ?? 0) : "N/A";
      const deaths  = slice.length >= 2 ? sum(dthArr.slice(1).map((v,i) => Math.max(0, v - dthArr[i]))) : "N/A";
      return [
        row("متوسط المصابين",          fmtNum(avgInf)),
        row("متوسط المتعافين",         fmtNum(avgRec)),
        row("إصابات جديدة في النطاق",  typeof newInf === "number" ? (newInf >= 0 ? "+" : "") + fmtNum(newInf) : newInf),
        row("تعافيات جديدة في النطاق", typeof newRec === "number" ? (newRec >= 0 ? "+" : "") + fmtNum(newRec) : newRec),
        row("وفيات الوباء في النطاق",  typeof deaths === "number" ? fmtNum(deaths) : deaths),
      ].join("");
    }

    case "population": {
      // --- إحصائيات السكان ---
      const popArr    = extract("total_population");
      const birthArr  = extract("total_births");
      const deathArr  = extract("total_deaths");
      const avgPop    = avg(popArr);
      const births    = slice.length >= 2 ? (slice[slice.length-1].total_births ?? 0) - (slice[0].total_births ?? 0) : "N/A";
      const deaths2   = slice.length >= 2 ? (slice[slice.length-1].total_deaths ?? 0) - (slice[0].total_deaths ?? 0) : "N/A";
      const netChange = (typeof births === "number" && typeof deaths2 === "number") ? births - deaths2 : "N/A";
      return [
        row("متوسط عدد السكان",   fmtNum(avgPop)),
        row("مواليد في النطاق",   typeof births   === "number" ? "+" + fmtNum(births)  : births),
        row("وفيات في النطاق",    typeof deaths2  === "number" ? fmtNum(deaths2)        : deaths2),
        row("صافي التغيير السكاني", typeof netChange === "number" ? (netChange >= 0 ? "+" : "") + fmtNum(netChange) : netChange),
      ].join("");
    }

    case "hospital": {
      // --- إحصائيات المستشفى ---
      const occArr  = extract("hospital_occupancy");
      const rejArr  = extract("hospital_rejected");
      const avgOcc  = avg(occArr);
      const maxOcc  = max(occArr);
      const rejSum  = slice.length >= 2 ? (slice[slice.length-1].hospital_rejected ?? 0) - (slice[0].hospital_rejected ?? 0) : "N/A";
      const growthRate = occArr.length >= 2 ? calculateRatePerMinute(occArr[0], occArr[occArr.length-1], occArr.length-1) : 0;
      return [
        row("متوسط الإشغال",           fmtNum(avgOcc)),
        row("أقصى إشغال",              fmtNum(maxOcc)),
        row("حالات مرفوضة في النطاق",  typeof rejSum === "number" ? fmtNum(rejSum) : rejSum),
        row("معدل نمو الإشغال/نقطة",   (growthRate >= 0 ? "+" : "") + fmtNum(growthRate)),
      ].join("");
    }

    case "gas": {
      // --- إحصائيات محطة الوقود ---
      const qArr    = extract("gas_queue_length");
      const wArr    = extract("gas_avg_wait");
      const avgQ    = avg(qArr);
      const maxQ    = max(qArr);
      const avgW    = avg(wArr);
      const growthRate = qArr.length >= 2 ? calculateRatePerMinute(qArr[0], qArr[qArr.length-1], qArr.length-1) : 0;
      return [
        row("متوسط طول الطابور",       fmtNum(avgQ)),
        row("أقصى طول للطابور",        fmtNum(maxQ)),
        row("متوسط وقت الانتظار (ث)",  fmtNum(avgW)),
        row("معدل نمو الطابور/نقطة",   (growthRate >= 0 ? "+" : "") + fmtNum(growthRate)),
      ].join("");
    }

    case "traffic": {
      // --- إحصائيات المرور ---
      const congArr  = extract("traffic_congestion").map(v => v * 100);
      const delayArr = extract("traffic_avg_delay");
      const avgCong  = avg(congArr);
      const maxCong  = max(congArr);
      const avgDelay = avg(delayArr);
      const growthRate = congArr.length >= 2 ? calculateRatePerMinute(congArr[0], congArr[congArr.length-1], congArr.length-1) : 0;
      return [
        row("متوسط الازدحام",          fmtNum(avgCong) + "%"),
        row("أقصى ازدحام",             fmtNum(maxCong) + "%"),
        row("متوسط التأخير (ث)",       fmtNum(avgDelay)),
        row("معدل نمو الازدحام/نقطة",  (growthRate >= 0 ? "+" : "") + fmtNum(growthRate) + "%"),
      ].join("");
    }

    case "demography": {
      // --- إحصائيات الديموغرافيا ---
      const bArr = extract("total_births");
      const dArr = extract("total_deaths");
      const newB = slice.length >= 2 ? (slice[slice.length-1].total_births ?? 0) - (slice[0].total_births ?? 0) : "N/A";
      const newD = slice.length >= 2 ? (slice[slice.length-1].total_deaths ?? 0) - (slice[0].total_deaths ?? 0) : "N/A";
      const ratio = (typeof newB === "number" && typeof newD === "number" && newD > 0)
        ? (newB / newD).toFixed(2) : "N/A";
      return [
        row("مواليد جديدة في النطاق",  typeof newB === "number" ? "+" + fmtNum(newB) : newB),
        row("وفيات جديدة في النطاق",   typeof newD === "number" ? fmtNum(newD)        : newD),
        row("نسبة المواليد/الوفيات",   ratio !== "N/A" ? ratio + "×" : ratio),
      ].join("");
    }

    default:
      return "";
  }
}

/** الحصول على التسمية العربية لنوع النظام */
function getSystemLabel(systemType) {
  const labels = {
    epidemic:   "الوباء",
    population: "السكان",
    hospital:   "المستشفى",
    gas:        "محطة الوقود",
    traffic:    "المرور",
    demography: "الديموغرافيا",
    compare:    "المقارنة",
    generic:    "النظام",
  };
  return labels[systemType] || "النظام";
}


// ===================================================
// التحديث التلقائي للبيانات الحية
// ===================================================

function startAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  fetchResults();
  refreshTimer = setInterval(fetchResults, REFRESH_INTERVAL);
}

function stopAutoRefresh() {
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
}

async function fetchResults() {
  try {
    const resp = await fetch("/results?t=" + Date.now());
    if (!resp.ok) throw new Error("فشل الجلب");
    const data = await resp.json();
    setConnected(true);
    updateDashboard(data);
  } catch (err) {
    setConnected(false);
  }
}

function updateDashboard(data) {
  const m  = data.current_metrics || {};
  const ts = data.time_series     || [];

  // حفظ السلسلة الزمنية الحية للوصول إليها من دوال النطاق
  liveTimeSeries = ts;

  // --- تحديث بطاقات المقاييس ---
  setText("mPop",     m.total_population   ?? "-");
  setText("mBirths",  m.total_births        ?? "-");
  setText("mDeaths",  m.total_deaths        ?? "-");
  setText("mInf",     m.infected            ?? "-");
  setText("mRec",     m.recovered           ?? "-");
  setText("mHosp",    m.hospital_occupancy  ?? "-");
  setText("mGas",     m.gas_queue_length    ?? "-");
  setText("mTraffic", m.traffic_congestion != null
    ? (m.traffic_congestion * 100).toFixed(0) + "%" : "-");

  if (ts.length === 0) return;

  const slice  = ts.slice(-MAX_POINTS);
  const labels = slice.map(s => formatSimTime(s.sim_time_minutes));

  // SIR
  updateChart(chartSIR, labels, [
    slice.map(s => s.susceptible ?? 0),
    slice.map(s => s.infected    ?? 0),
    slice.map(s => s.recovered   ?? 0),
  ]);

  // السكان
  updateChart(chartPop, labels, [slice.map(s => s.total_population ?? 0)]);

  // المستشفى
  updateChart(chartHosp, labels, [slice.map(s => s.hospital_occupancy ?? 0)]);

  // الوقود
  updateChart(chartGas, labels, [slice.map(s => s.gas_queue_length ?? 0)]);

  // الازدحام (تحويل إلى نسبة مئوية)
  updateChart(chartTraffic, labels, [
    slice.map(s => s.traffic_congestion != null ? +(s.traffic_congestion * 100).toFixed(2) : 0)
  ]);

  // الديموغرافيا
  updateChart(chartDemography, labels, [
    slice.map(s => s.total_births ?? 0),
    slice.map(s => s.total_deaths ?? 0),
  ]);
}

function updateChart(chart, labels, datasetsData) {
  chart.data.labels = labels;
  datasetsData.forEach((d, i) => {
    if (chart.data.datasets[i]) chart.data.datasets[i].data = d;
  });
  chart.update("none");
}


// ===================================================
// نظام المقارنة المتكامل
// ===================================================

async function loadSessionsList() {
  const selA = document.getElementById("selectSessionA");
  const selB = document.getElementById("selectSessionB");
  if (!selA || !selB) return;

  selA.innerHTML = '<option value="">-- اختر الجلسة A --</option>';
  selB.innerHTML = '<option value="">-- اختر الجلسة B --</option>';

  try {
    const resp = await fetch("/api/sessions");
    if (!resp.ok) throw new Error("API غير متاح");
    const sessions = await resp.json();

    if (!sessions || sessions.length === 0) {
      selA.innerHTML = '<option value="">لا توجد جلسات محفوظة</option>';
      selB.innerHTML = '<option value="">لا توجد جلسات محفوظة</option>';
      renderSessionsLegacy([]);
      return;
    }

    sessions.forEach(s => {
      const params = s.parameters || {};
      const label  = `${s.session_id}  |  سكان: ${params.population ?? "-"}  |  عدوى: ${params.infection_rate ?? "-"}  |  ${formatSimTime(s.simulation_duration_minutes ?? 0)}`;
      selA.appendChild(new Option(label, s.session_id));
      selB.appendChild(new Option(label, s.session_id));
    });

    renderSessionsLegacy(sessions);

  } catch (err) {
    selA.innerHTML = '<option value="">تعذّر تحميل الجلسات</option>';
    selB.innerHTML = '<option value="">تعذّر تحميل الجلسات</option>';
  }
}

async function loadSessions() { await loadSessionsList(); }

async function onSessionAChange() {
  const id = document.getElementById("selectSessionA")?.value;
  if (!id) { sessionDataA = null; return; }
  selectedSessionA = id;
  showCompareLoading(true);
  try {
    const resp = await fetch(`/api/sessions/${id}`);
    sessionDataA = await resp.json();
  } catch { sessionDataA = null; }
  showCompareLoading(false);
  renderCompareChart();
}

async function onSessionBChange() {
  const id = document.getElementById("selectSessionB")?.value;
  if (!id) { sessionDataB = null; return; }
  selectedSessionB = id;
  showCompareLoading(true);
  try {
    const resp = await fetch(`/api/sessions/${id}`);
    sessionDataB = await resp.json();
  } catch { sessionDataB = null; }
  showCompareLoading(false);
  renderCompareChart();
}

function onMetricChange() {
  const sel = document.getElementById("selectMetric");
  if (sel) selectedMetric = sel.value;
  renderCompareChart();
}

function renderCompareChart() {
  const emptyState = document.getElementById("compareEmptyState");
  const container  = document.getElementById("compareChartContainer");
  const title      = document.getElementById("compareChartTitle");

  if (!sessionDataA || !sessionDataB) {
    if (emptyState) emptyState.style.display = "flex";
    if (container)  container.style.display  = "none";
    return;
  }

  if (emptyState) emptyState.style.display = "none";
  if (container)  container.style.display  = "block";

  const tsA = normalizeSessionData(sessionDataA);
  const tsB = normalizeSessionData(sessionDataB);

  const labelsA = tsA.map(p => formatSimTime(p.sim_time_minutes));
  const labelsB = tsB.map(p => formatSimTime(p.sim_time_minutes));
  const labels  = labelsA.length >= labelsB.length ? labelsA : labelsB;

  const metricLabel = METRIC_LABELS[selectedMetric] || selectedMetric;
  if (title) title.textContent = `مقارنة: ${metricLabel}`;

  const extractMetric = (ts, key) => ts.map(p => {
    const v = p[key];
    return v != null ? (key === "traffic_congestion" ? +(v * 100).toFixed(2) : v) : null;
  });

  const dataA = extractMetric(tsA, selectedMetric);
  const dataB = extractMetric(tsB, selectedMetric);

  if (chartCompare) {
    chartCompare.data.labels = labels;
    chartCompare.data.datasets[0].data  = dataA;
    chartCompare.data.datasets[0].label = `A: ${selectedSessionA}`;
    chartCompare.data.datasets[1].data  = dataB;
    chartCompare.data.datasets[1].label = `B: ${selectedSessionB}`;
    chartCompare.update("none");
  } else {
    chartCompare = new Chart(document.getElementById("chartCompare"), {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: `A: ${selectedSessionA}`, data: dataA, borderColor: COLORS.sessionA, backgroundColor: "rgba(88,166,255,0.08)", tension: 0.4, fill: false, pointRadius: 1, borderWidth: 2 },
          { label: `B: ${selectedSessionB}`, data: dataB, borderColor: COLORS.sessionB, backgroundColor: "rgba(248,81,73,0.08)",  tension: 0.4, fill: false, pointRadius: 1, borderWidth: 2, borderDash: [5,3] },
        ]
      },
      options: getChartOptions("chartCompare", metricLabel)
    });
    initRangeState("chartCompare", chartCompare);
  }
}

function normalizeSessionData(sessionData) {
  if (!sessionData) return [];
  if (Array.isArray(sessionData)) return sessionData;
  if (sessionData.time_series && Array.isArray(sessionData.time_series)) return sessionData.time_series;
  if (sessionData.data && Array.isArray(sessionData.data)) return sessionData.data;
  return [];
}

function showCompareLoading(show) {
  const el = document.getElementById("compareLoading");
  if (el) el.style.display = show ? "flex" : "none";
}

function renderSessionsLegacy(sessions) {
  const container = document.getElementById("sessionsContainer");
  if (!container) return;
  container.innerHTML = "";
  if (!sessions || sessions.length === 0) {
    container.innerHTML = '<p class="no-sessions">لا توجد جلسات محفوظة بعد. شغّل المحاكاة لإنشاء جلسة.</p>';
    return;
  }
  sessions.slice(0, 20).forEach(s => {
    const params = s.parameters || {};
    const card   = document.createElement("div");
    card.className = "session-card";
    card.innerHTML = `
      <div class="session-id">${s.session_id}</div>
      <div class="session-params">
        معدل العدوى: ${params.infection_rate ?? "-"} &nbsp;|&nbsp;
        السكان: ${params.population ?? "-"} &nbsp;|&nbsp;
        مدة التشغيل: ${formatSimTime(s.simulation_duration_minutes ?? 0)}
      </div>`;
    container.appendChild(card);
  });
}


// ===================================================
// صندوق المعلومات التفاعلي (نقطة واحدة — موجود مسبقاً)
// ===================================================

function showPointInfoBox(chart, elements, event) {
  if (!elements || elements.length === 0) { hideInfoBox(); return; }

  const el           = elements[0];
  const datasetIndex = el.datasetIndex;
  const pointIndex   = el.index;
  const dataset      = chart.data.datasets[datasetIndex];
  const data         = dataset.data;
  const label        = chart.data.labels[pointIndex] || String(pointIndex);
  const value        = data[pointIndex];

  const avg    = calcAvgUntil(data, pointIndex);
  const minVal = calcMin(data);
  const maxVal = calcMax(data);
  const rateCh = calcRateOfChange(data, pointIndex);
  const pctCh  = calcPctChange(data, pointIndex);

  const sessionLabel = dataset.label || "الجلسة الحالية";

  const content = `
    <div class="info-box-header">
      <span class="info-box-title">تفاصيل النقطة</span>
      <button class="info-box-close" onclick="hideInfoBox()">&#x2715;</button>
    </div>
    <div class="info-box-body">
      <div class="info-row"><span class="info-key">المقياس</span><span class="info-val">${sessionLabel}</span></div>
      <div class="info-row"><span class="info-key">الزمن</span><span class="info-val">${label}</span></div>
      <div class="info-row highlight"><span class="info-key">القيمة</span><span class="info-val">${fmtNum(value)}</span></div>
      <div class="info-divider"></div>
      <div class="info-row"><span class="info-key">المتوسط حتى الآن</span><span class="info-val">${fmtNum(avg)}</span></div>
      <div class="info-row"><span class="info-key">الحد الأدنى</span><span class="info-val">${fmtNum(minVal)}</span></div>
      <div class="info-row"><span class="info-key">الحد الأقصى</span><span class="info-val">${fmtNum(maxVal)}</span></div>
      <div class="info-divider"></div>
      <div class="info-row">
        <span class="info-key">التغيير</span>
        <span class="info-val ${rateCh >= 0 ? "positive" : "negative"}">${rateCh >= 0 ? "+" : ""}${fmtNum(rateCh)}</span>
      </div>
      <div class="info-row">
        <span class="info-key">نسبة التغيير</span>
        <span class="info-val ${pctCh === null ? "" : pctCh >= 0 ? "positive" : "negative"}">
          ${pctCh === null ? "N/A" : (pctCh >= 0 ? "+" : "") + pctCh.toFixed(2) + "%"}
        </span>
      </div>
    </div>`;

  if (!infoBox) {
    infoBox = document.createElement("div");
    infoBox.id        = "pointInfoBox";
    infoBox.className = "point-info-box";
    document.body.appendChild(infoBox);
  }

  infoBox.innerHTML     = content;
  infoBox.style.display = "block";
  infoBox.style.left    = `${event.pageX + 15}px`;
  infoBox.style.top     = `${event.pageY - 10}px`;

  requestAnimationFrame(() => {
    if (!infoBox) return;
    const r = infoBox.getBoundingClientRect();
    if (r.right  > window.innerWidth  - 10) infoBox.style.left = `${event.pageX - r.width  - 15}px`;
    if (r.bottom > window.innerHeight - 10) infoBox.style.top  = `${event.pageY - r.height - 10}px`;
  });
}

function hideInfoBox() {
  if (infoBox) infoBox.style.display = "none";
}


// ===================================================
// دوال الحسابات الإحصائية (للصندوق القديم — نقطة واحدة)
// ===================================================

function calcAvgUntil(data, index) {
  if (!data || data.length === 0) return 0;
  const slice = data.slice(0, index + 1).filter(v => v != null);
  return slice.length ? slice.reduce((a, b) => a + b, 0) / slice.length : 0;
}

function calcMin(data) {
  if (!data || data.length === 0) return 0;
  const v = data.filter(x => x != null);
  return v.length ? Math.min(...v) : 0;
}

function calcMax(data) {
  if (!data || data.length === 0) return 0;
  const v = data.filter(x => x != null);
  return v.length ? Math.max(...v) : 0;
}

function calcRateOfChange(data, index) {
  if (!data || index <= 0 || index >= data.length) return 0;
  return (data[index] ?? 0) - (data[index - 1] ?? 0);
}

function calcPctChange(data, index) {
  if (!data || index <= 0 || index >= data.length) return null;
  const prev = data[index - 1] ?? 0;
  if (prev === 0) return null;
  return (((data[index] ?? 0) - prev) / Math.abs(prev)) * 100;
}


// ===================================================
// الإعدادات
// ===================================================

async function startSimulation() {
  const g = id => document.getElementById(id);
  const config = {
    apply:                     true,
    infection_rate:            parseFloat(g("infectionRate")?.value    ?? 0.3),
    hospital_capacity:         parseInt(g("hospitalCapacity")?.value   ?? 50),
    fuel_rate:                 parseFloat(g("fuelRate")?.value          ?? 0.05),
    traffic_density:           parseFloat(g("trafficDensity")?.value    ?? 0.4),
    population:                parseInt(g("population")?.value          ?? 100),
    mobility_factor:           parseFloat(g("mobilityFactor")?.value    ?? 0.8),
    simulation_duration_years: parseInt(g("simDuration")?.value         ?? 10),
    speed_factor:              parseInt(g("speedFactor")?.value          ?? 1),
    birth_rate:                0.02,
    death_rate:                0.01,
  };

  try {
    const resp = await fetch("/write-config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    const result = await resp.json();
    showConfigStatus(result.status === "ok"
      ? "تم حفظ الإعدادات. اضغط Reset في المحاكاة لتطبيقها."
      : "خطأ: " + result.message,
      result.status === "ok" ? "success" : "warning"
    );
  } catch (err) {
    showConfigStatus("تعذّر الاتصال بالخادم.", "warning");
  }

  startAutoRefresh();
}


// ===================================================
// الدوال المساعدة العامة
// ===================================================

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function showConfigStatus(msg, type = "success") {
  const el = document.getElementById("configStatus");
  if (el) { el.textContent = msg; el.style.color = type === "warning" ? "#d29922" : "#3fb950"; }
}

function formatSimTime(minutes) {
  if (minutes == null || isNaN(minutes)) return "-";
  const days  = Math.floor(minutes / 1440);
  const hours = Math.floor((minutes % 1440) / 60);
  return `ي${days} س${hours}`;
}

function fmtNum(val) {
  if (val == null || isNaN(val)) return "-";
  return Number.isInteger(val) ? val.toString() : val.toFixed(2);
}

function setConnected(status) {
  isConnected = status;
  const badge = document.getElementById("statusBadge");
  if (!badge) return;
  if (status) { badge.textContent = "متصل";     badge.classList.add("connected"); }
  else        { badge.textContent = "غير متصل"; badge.classList.remove("connected"); }
}


// ===================================================
// التهيئة عند تحميل الصفحة
// ===================================================

document.addEventListener("DOMContentLoaded", () => {
  initCharts();
  startAutoRefresh();
  loadSessionsList();

  // تهيئة أشرطة الحالة لكل رسم بياني
  Object.keys(CHART_DEFS).forEach(chartId => {
    const bar = document.getElementById(chartId + "_rangeStatus");
    if (bar) bar.textContent = "انقر على نقطة البداية لبدء تحليل النطاق الزمني";
  });
});

// ===== Aliases للتوافق مع الاختبارات =====
function calculateStats(data) {
  const avg = data.reduce((a, b) => a + b, 0) / data.length;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const variance = data.reduce((a, b) => a + Math.pow(b - avg, 2), 0) / data.length;
  const stdDev = Math.sqrt(variance);
  return { avg, min, max, stdDev, variance };
}
function buildRangeBox(chartId, stats, specificStats) {
  return showRangeAnalysisBox ? showRangeAnalysisBox : null;
}

// ============================================================
// نافذة تفاصيل تحليل النطاق الزمني (Range Detail Modal)
// ============================================================

/** متغير عالمي يحفظ بيانات آخر تحليل نطاق لاستخدامه في المودال */
let _lastRangeData = null;

/**
 * فتح نافذة المودال المركزية لعرض تفاصيل النطاق الزمني.
 * يُستدعى من زر "عرض التفاصيل" في شريط الحالة.
 * @param {string} chartId - معرّف الرسم البياني
 */
function openRangeDetailModal(chartId) {
  const state = rangeState[chartId];
  if (!state || state.startIndex === null || state.endIndex === null) return;

  const chart      = state.chartRef;
  const startIdx   = state.startIndex;
  const endIdx     = state.endIndex;
  const labels     = chart.data.labels || [];
  const startLabel = labels[startIdx] || startIdx;
  const endLabel   = labels[endIdx]   || endIdx;
  const duration   = endIdx - startIdx + 1;

  // تحديد نوع النظام من معرّف الرسم البياني
  const systemType = _detectSystemType(chartId);
  const metricName = _getMetricDisplayName(chartId);

  // جمع بيانات جميع مجموعات البيانات في النطاق
  const allDatasets = (chart.data.datasets || []).map(ds => ({
    label : ds.label || "",
    color : ds.borderColor || ds.backgroundColor || "#58a6ff",
    values: (ds.data || []).slice(startIdx, endIdx + 1).map(v => (typeof v === "number" ? v : 0))
  }));

  // حساب الإحصائيات للمجموعة الأولى (المرجعية)
  const primaryData = allDatasets.length > 0 ? allDatasets[0].values : [];
  const stats       = _calcStats(primaryData);

  // حساب الإحصائيات الخاصة بالنظام
  // ملاحظة: getSystemSpecificStats تُعيد HTML string، لذا نمررها مباشرة
  const specificHTML = getSystemSpecificStats(systemType, chartId, chart, startIdx, endIdx);

  // تحديث رأس المودال
  const subtitle = document.getElementById("rdModalSubtitle");
  if (subtitle) subtitle.textContent = metricName;

  // تحديث شريط النطاق
  const rdRangeInfo = document.getElementById("rdRangeInfo");
  if (rdRangeInfo) {
    rdRangeInfo.innerHTML =
      `من <strong>${startLabel}</strong> إلى <strong>${endLabel}</strong> — <strong>${duration}</strong> نقطة`;
  }

  // ربط زر المسح بالرسم البياني الصحيح
  const rdClearBtn = document.getElementById("rdClearBtn");
  if (rdClearBtn) rdClearBtn.setAttribute("onclick", `clearRange('${chartId}'); closeRangeDetailModal();`);

  // بناء محتوى جسم المودال
  const body = document.getElementById("rdModalBody");
  if (body) body.innerHTML = _buildModalBody(allDatasets, stats, specificHTML, systemType, startLabel, endLabel, duration);

  // حفظ البيانات وفتح المودال
  _lastRangeData = { chartId, startIdx, endIdx, stats, specificHTML };
  const overlay = document.getElementById("rangeDetailModal");
  if (overlay) overlay.classList.add("active");
}

/**
 * إغلاق نافذة المودال.
 * @param {Event} [event] - حدث النقر (للتحقق من النقر خارج النافذة)
 */
function closeRangeDetailModal(event) {
  if (event && event.target !== event.currentTarget) return;
  const overlay = document.getElementById("rangeDetailModal");
  if (overlay) overlay.classList.remove("active");
}

/**
 * بناء HTML لجسم المودال مع جميع الأقسام والإحصائيات.
 */
function _buildModalBody(allDatasets, stats, specificStats, systemType, startLabel, endLabel, duration) {
  const fmt = v => (typeof v === "number" ? (Number.isInteger(v) ? v.toLocaleString() : v.toFixed(2)) : v);
  const sign = v => (v >= 0 ? "+" : "") + fmt(v);
  const cls  = v => v > 0 ? "rd-positive" : v < 0 ? "rd-negative" : "rd-neutral";

  // --- قسم معلومات النطاق ---
  const rangeSection = `
  <div class="rd-sections-grid">
    <div class="rd-section rd-highlight">
      <div class="rd-section-header">
        <div class="rd-section-dot" style="background:#58a6ff"></div>
        <span class="rd-section-title">معلومات النطاق</span>
      </div>
      <div class="rd-rows">
        <div class="rd-row"><span class="rd-key">نقطة البداية</span><span class="rd-val rd-blue">${startLabel}</span></div>
        <div class="rd-row"><span class="rd-key">نقطة النهاية</span><span class="rd-val rd-blue">${endLabel}</span></div>
        <div class="rd-row"><span class="rd-key">عدد النقاط</span><span class="rd-val">${duration}</span></div>
        <div class="rd-row"><span class="rd-key">عدد المجموعات</span><span class="rd-val">${allDatasets.length}</span></div>
      </div>
    </div>
    <div class="rd-section rd-highlight">
      <div class="rd-section-header">
        <div class="rd-section-dot" style="background:#3fb950"></div>
        <span class="rd-section-title">الإحصائيات الأساسية</span>
      </div>
      <div class="rd-rows">
        <div class="rd-row"><span class="rd-key">الحد الأدنى</span><span class="rd-val rd-red">${fmt(stats.min)}</span></div>
        <div class="rd-row"><span class="rd-key">الحد الأقصى</span><span class="rd-val rd-green">${fmt(stats.max)}</span></div>
        <div class="rd-row"><span class="rd-key">المتوسط</span><span class="rd-val rd-blue">${fmt(stats.avg)}</span></div>
        <div class="rd-row"><span class="rd-key">الانحراف المعياري</span><span class="rd-val rd-yellow">${fmt(stats.stdDev)}</span></div>
      </div>
    </div>
  </div>`;

  // --- قسم التغيير ---
  const changeSection = `
  <div class="rd-sections-grid">
    <div class="rd-section">
      <div class="rd-section-header">
        <div class="rd-section-dot" style="background:#d29922"></div>
        <span class="rd-section-title">إحصائيات التغيير</span>
      </div>
      <div class="rd-rows">
        <div class="rd-row"><span class="rd-key">قيمة البداية</span><span class="rd-val">${fmt(stats.first)}</span></div>
        <div class="rd-row"><span class="rd-key">قيمة النهاية</span><span class="rd-val">${fmt(stats.last)}</span></div>
        <div class="rd-row">
          <span class="rd-key">إجمالي التغيير</span>
          <span class="rd-val ${cls(stats.totalChange)}">${sign(stats.totalChange)}</span>
        </div>
        <div class="rd-row">
          <span class="rd-key">نسبة التغيير</span>
          <span class="rd-val ${cls(stats.pctChange)}">
            ${stats.pctChange === null ? "N/A" : sign(stats.pctChange) + "%"}
          </span>
        </div>
        <div class="rd-row">
          <span class="rd-key">معدل التغيير/نقطة</span>
          <span class="rd-val ${cls(stats.ratePerPoint)}">${sign(stats.ratePerPoint)}</span>
        </div>
      </div>
    </div>
    ${allDatasets.length > 1 ? _buildDatasetsSection(allDatasets, fmt) : ""}
  </div>`;

  // --- قسم الإحصائيات الخاصة بالنظام ---
  // specificStats هنا هو HTML string مُعاد من getSystemSpecificStats
  let specificSection = "";
  if (specificStats && typeof specificStats === "string" && specificStats.trim().length > 0) {
    specificSection = `
    <div class="rd-section rd-specific">
      <div class="rd-section-header">
        <div class="rd-section-dot" style="background:#a371f7"></div>
        <span class="rd-section-title">إحصائيات ${getSystemLabel(systemType)} المتخصصة</span>
      </div>
      <div class="rd-rows">${specificStats}</div>
    </div>`;
  }

  return rangeSection + changeSection + specificSection;
}

/** بناء قسم مجموعات البيانات المتعددة */
function _buildDatasetsSection(allDatasets, fmt) {
  const rows = allDatasets.map(ds => {
    const s = _calcStats(ds.values);
    return `<div class="rd-row">
      <span class="rd-key" style="color:${ds.color}">${ds.label}</span>
      <span class="rd-val">متوسط: ${fmt(s.avg)} | أقصى: ${fmt(s.max)}</span>
    </div>`;
  }).join("");
  return `
  <div class="rd-section">
    <div class="rd-section-header">
      <div class="rd-section-dot" style="background:#58a6ff"></div>
      <span class="rd-section-title">مجموعات البيانات</span>
    </div>
    <div class="rd-rows">${rows}</div>
  </div>`;
}

/** حساب إحصائيات مجموعة بيانات */
function _calcStats(data) {
  if (!data || data.length === 0) return { min:0, max:0, avg:0, stdDev:0, first:0, last:0, totalChange:0, pctChange:null, ratePerPoint:0 };
  const n     = data.length;
  const first = data[0];
  const last  = data[n - 1];
  const min   = Math.min(...data);
  const max   = Math.max(...data);
  const avg   = data.reduce((a, b) => a + b, 0) / n;
  const variance  = data.reduce((a, b) => a + Math.pow(b - avg, 2), 0) / n;
  const stdDev    = Math.sqrt(variance);
  const totalChange = last - first;
  const pctChange   = first !== 0 ? (totalChange / Math.abs(first)) * 100 : null;
  const ratePerPoint = n > 1 ? totalChange / (n - 1) : 0;
  return { min, max, avg, stdDev, first, last, totalChange, pctChange, ratePerPoint };
}

/** اكتشاف نوع النظام من معرّف الرسم البياني */
function _detectSystemType(chartId) {
  if (chartId.toLowerCase().includes("sir"))        return "epidemic";
  if (chartId.toLowerCase().includes("pop"))        return "population";
  if (chartId.toLowerCase().includes("demo"))       return "demography";
  if (chartId.toLowerCase().includes("hosp"))       return "hospital";
  if (chartId.toLowerCase().includes("gas"))        return "gas";
  if (chartId.toLowerCase().includes("traffic"))    return "traffic";
  if (chartId.toLowerCase().includes("compare"))    return "comparison";
  return "general";
}

/** الحصول على الاسم العربي للرسم البياني */
function _getMetricDisplayName(chartId) {
  const map = {
    chartSIR       : "نموذج SIR — انتشار الوباء",
    chartPop       : "التطور السكاني",
    chartDemography: "الديموغرافيا — المواليد والوفيات",
    chartHosp      : "إشغال المستشفى",
    chartGas       : "طابور محطة الوقود",
    chartTraffic   : "الازدحام المروري",
    chartCompare   : "مقارنة الجلسات"
  };
  return map[chartId] || chartId;
}

// ربط مفتاح Escape لإغلاق المودال
document.addEventListener("keydown", e => {
  if (e.key === "Escape") closeRangeDetailModal();
});

// ===================================================
// نظام التنبؤ بالذكاء الاصطناعي المحلي
// ===================================================

/**
 * مرجع رسم التنبؤ
 * يُخزّن كائن Chart.js لرسم التنبؤ حتى يمكن تدميره وإعادة إنشائه
 */
let chartPrediction = null;

/**
 * آخر بيانات تنبؤ تم توليدها
 */
let _lastPredictionData = null;

/**
 * تفعيل / تعطيل لوحة التنبؤ عند تغيير حالة checkbox
 */
function onPredictionToggle() {
  const enabled = document.getElementById("predictionEnabled").checked;
  const controls = ["predMetric", "predMode", "predHorizon", "predCustomHorizon", "btnGeneratePrediction"];
  controls.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.disabled = !enabled;
  });
  if (!enabled) {
    document.getElementById("predictionChartContainer").style.display = "none";
    document.getElementById("predictionExplanation").style.display = "none";
    _lastPredictionData = null;
  }
}

/**
 * إظهار / إخفاء حقل الأفق المخصص
 */
function onHorizonChange() {
  const horizonSelect = document.getElementById("predHorizon");
  const customGroup   = document.getElementById("customHorizonGroup");
  const customInput   = document.getElementById("predCustomHorizon");
  if (horizonSelect.value === "custom") {
    customGroup.style.display = "flex";
    const enabled = document.getElementById("predictionEnabled").checked;
    if (customInput) customInput.disabled = !enabled;
  } else {
    customGroup.style.display = "none";
  }
}

/**
 * الحصول على الأفق الزمني المحدد
 */
function _getPredictionHorizon() {
  const horizonSelect = document.getElementById("predHorizon");
  if (horizonSelect.value === "custom") {
    const customVal = parseInt(document.getElementById("predCustomHorizon").value, 10);
    return isNaN(customVal) || customVal < 5 ? 60 : customVal;
  }
  return parseInt(horizonSelect.value, 10);
}

/**
 * الحصول على الاسم العربي للمقياس
 */
function _getMetricArabicName(metric) {
  const names = {
    infected:           "المصابون",
    recovered:          "المتعافون",
    total_deaths:       "إجمالي الوفيات",
    total_births:       "إجمالي المواليد",
    total_population:   "إجمالي السكان",
    hospital_occupancy: "إشغال المستشفى",
    gas_queue_length:   "طابور الوقود",
    traffic_congestion: "ازدحام المرور"
  };
  return names[metric] || metric;
}

/**
 * الحصول على الاسم العربي لوضع التنبؤ
 */
function _getModeArabicName(mode) {
  const names = {
    linear_regression:     "الانحدار الخطي",
    moving_average:        "المتوسط المتحرك",
    exponential_smoothing: "التمهيد الأسي"
  };
  return names[mode] || mode;
}

/**
 * الحصول على الاسم العربي لاتجاه التنبؤ
 */
function _getTrendArabicName(trend) {
  const names = {
    increasing: "تزايد تدريجي",
    decreasing: "تناقص تدريجي",
    stable:     "استقرار نسبي"
  };
  return names[trend] || trend;
}

/**
 * توليد التنبؤ: يُرسل طلب POST إلى /api/predict ثم يقرأ النتيجة
 * ويعرضها على الرسم البياني مع شرح عربي
 */
async function generatePrediction() {
  const metric  = document.getElementById("predMetric").value;
  const mode    = document.getElementById("predMode").value;
  const horizon = _getPredictionHorizon();

  document.getElementById("predictionLoading").style.display = "flex";
  document.getElementById("predictionChartContainer").style.display = "none";
  document.getElementById("predictionExplanation").style.display = "none";
  document.getElementById("btnGeneratePrediction").disabled = true;

  try {
    // --- الخطوة 1: إرسال طلب توليد التنبؤ ---
    let response;
    try {
      response = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ metric, mode, horizon })
      });
    } catch (networkErr) {
      _showPredictionError("تعذّر الاتصال بالخادم. تأكد من تشغيل server.py: " + networkErr.message);
      return;
    }

    // --- تحليل استجابة POST بأمان ---
    let result;
    const rawText = await response.text();
    if (!rawText || rawText.trim() === "") {
      _showPredictionError("الخادم أعاد استجابة فارغة. تأكد من صحة server.py.");
      return;
    }
    try {
      result = JSON.parse(rawText);
    } catch (parseErr) {
      _showPredictionError("استجابة غير صالحة من الخادم: " + rawText.substring(0, 100));
      return;
    }

    if (result.status === "error") {
      _showPredictionError(result.message);
      return;
    }

    // --- الخطوة 2: جلب نتائج التنبؤ المحفوظة ---
    let predResponse;
    try {
      predResponse = await fetch("/api/predictions?t=" + Date.now());
    } catch (networkErr) {
      _showPredictionError("تعذّر جلب نتائج التنبؤ: " + networkErr.message);
      return;
    }

    // --- تحليل استجابة GET بأمان ---
    let predData;
    const predRawText = await predResponse.text();
    if (!predRawText || predRawText.trim() === "") {
      _showPredictionError("ملف التنبؤ فارغ. حاول مرة أخرى.");
      return;
    }
    try {
      predData = JSON.parse(predRawText);
    } catch (parseErr) {
      _showPredictionError("بيانات التنبؤ غير صالحة: " + predRawText.substring(0, 100));
      return;
    }

    if (predData.error) {
      _showPredictionError(predData.error);
      return;
    }

    // --- عرض النتائج ---
    _lastPredictionData = predData;
    _renderPredictionChart(predData, metric);
    _renderPredictionExplanation(predData, metric, mode, horizon);

  } catch (err) {
    _showPredictionError("خطأ غير متوقع: " + err.message);
  } finally {
    document.getElementById("predictionLoading").style.display = "none";
    document.getElementById("btnGeneratePrediction").disabled = false;
  }
}

/**
 * عرض رسالة خطأ في لوحة التنبؤ
 */
function _showPredictionError(message) {
  document.getElementById("predictionLoading").style.display = "none";
  document.getElementById("predictionExplanation").style.display = "block";
  document.getElementById("predictionExplanation").innerHTML =
    `<strong>تنبيه:</strong> ${message}`;
}

/**
 * رسم الرسم البياني للتنبؤ
 * يعرض البيانات الفعلية (خط صلب) والمتوقعة (خط متقطع)
 */
function _renderPredictionChart(predData, metric) {
  const container = document.getElementById("predictionChartContainer");
  const titleEl   = document.getElementById("predictionChartTitle");

  const metricPred = predData.predictions && predData.predictions[metric];
  if (!metricPred) {
    _showPredictionError("لا توجد بيانات تنبؤ لهذا المقياس");
    return;
  }

  const historicalData = _getHistoricalDataForMetric(metric);
  const futureTime = metricPred.future_time || [];
  const futureVals = metricPred.values || [];
  const metricName = _getMetricArabicName(metric);
  titleEl.textContent = "تنبؤ: " + metricName;

  if (chartPrediction) {
    chartPrediction.destroy();
    chartPrediction = null;
  }

  const ctx = document.getElementById("chartPrediction").getContext("2d");
  const datasets = [];

  // البيانات الفعلية (خط صلب أزرق)
  if (historicalData.labels.length > 0) {
    datasets.push({
      label: metricName + " — فعلي",
      data: historicalData.values,
      borderColor: "#58a6ff",
      backgroundColor: "rgba(88,166,255,0.08)",
      borderWidth: 2,
      pointRadius: 0,
      tension: 0.3,
      borderDash: []
    });
  }

  // البيانات المتوقعة (خط متقطع برتقالي)
  if (futureVals.length > 0) {
    datasets.push({
      label: metricName + " — متوقع",
      data: futureVals,
      borderColor: "#f0883e",
      backgroundColor: "rgba(240,136,62,0.08)",
      borderWidth: 2,
      pointRadius: 0,
      tension: 0.3,
      borderDash: [6, 4]
    });
  }

  const allLabels = [
    ...historicalData.labels,
    ...futureTime.map(t => Math.round(t))
  ];

  chartPrediction = new Chart(ctx, {
    type: "line",
    data: { labels: allLabels, datasets: datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { labels: { color: "#c9d1d9", font: { size: 13 } } },
        tooltip: {
          backgroundColor: "#161b22",
          titleColor: "#58a6ff",
          bodyColor: "#c9d1d9"
        }
      },
      scales: {
        x: {
          ticks: { color: "#8b949e", maxTicksLimit: 10 },
          grid:  { color: "rgba(255,255,255,0.05)" },
          title: { display: true, text: "الزمن (دقيقة محاكاة)", color: "#8b949e" }
        },
        y: {
          ticks: { color: "#8b949e" },
          grid:  { color: "rgba(255,255,255,0.05)" },
          title: { display: true, text: metricName, color: "#8b949e" }
        }
      }
    }
  });

  container.style.display = "block";
}

/**
 * استخراج البيانات التاريخية للمقياس من الرسوم البيانية الحية
 */
function _getHistoricalDataForMetric(metric) {
  const metricToChart = {
    infected:           chartSIR,
    recovered:          chartSIR,
    total_deaths:       chartDemography,
    total_births:       chartDemography,
    total_population:   chartPop,
    hospital_occupancy: chartHosp,
    gas_queue_length:   chartGas,
    traffic_congestion: chartTraffic
  };

  const metricToDatasetIndex = {
    infected:           1,
    recovered:          2,
    total_deaths:       1,
    total_births:       0,
    total_population:   0,
    hospital_occupancy: 0,
    gas_queue_length:   0,
    traffic_congestion: 0
  };

  const chart = metricToChart[metric];
  if (!chart || !chart.data) return { labels: [], values: [] };

  const dsIndex = metricToDatasetIndex[metric] || 0;
  const ds = chart.data.datasets[dsIndex];
  if (!ds) return { labels: [], values: [] };

  return {
    labels: [...(chart.data.labels || [])],
    values: [...(ds.data || [])]
  };
}

/**
 * عرض صندوق الشرح بالعربية تحت الرسم البياني
 */
function _renderPredictionExplanation(predData, metric, mode, horizon) {
  const explanationEl = document.getElementById("predictionExplanation");
  const metricName    = _getMetricArabicName(metric);
  const modeName      = _getModeArabicName(mode);
  const trend         = predData.trend || "stable";
  const trendName     = _getTrendArabicName(trend);
  const dataPoints    = predData.data_points_used || 0;

  const trendColor = trend === "increasing" ? "#3fb950"
                   : trend === "decreasing" ? "#f85149"
                   : "#d29922";

  explanationEl.innerHTML =
    "<strong>شرح نتيجة التنبؤ:</strong><br><br>" +
    "اعتمد النظام على آخر <strong>" + dataPoints + "</strong> نقطة زمنية من بيانات " +
    "<strong>" + metricName + "</strong>، واستخدم طريقة <strong>" + modeName + "</strong> " +
    "لتوقع القيم القادمة لمدة <strong>" + horizon + "</strong> دقيقة محاكاة.<br><br>" +
    "الاتجاه الحالي يشير إلى: <strong style=\"color:" + trendColor + "\">" + trendName + "</strong> " +
    "في قيم " + metricName + ".<br><br>" +
    "<em>ملاحظة: الخط الصلب يمثل البيانات الفعلية، والخط المتقطع يمثل القيم المتوقعة المستقبلية.</em>";

  explanationEl.style.display = "block";
}
