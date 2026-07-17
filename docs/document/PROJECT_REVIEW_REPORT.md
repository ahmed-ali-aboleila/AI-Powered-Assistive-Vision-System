# 📋 تقرير المراجعة الفنية وفحص مشروع Assistive Vision System

تمت مراجعة وفحص ملفات المشروع بالكامل واختبار استدعاء المكتبات والاعتمادات البرمجية (Dependencies) ونموذج الذكاء الاصطناعي بنجاح. يوضح هذا التقرير الأخطاء والمشاكل البرمجية والمنطقية المكتشفة مع الحلول البرمجية المقترحة لكل منها.

---

## 1. مشكلة ترميز الحروف على ويندوز (Unicode Encode Error)
* **درجة الخطورة:** 🔴 حرجة جداً (تؤدي لانهيار التطبيق فوراً عند التشغيل)
* **المشكلة:** 
  عند تشغيل المشروع على نظام ويندوز من خلال موجه الأوامر (CMD) الافتراضي، ينهار البرنامج فوراً عند محاولة طباعة الرموز التعبيرية (Emojis) مثل `✅` و `⚠️` أو النصوص العربية مثل `فيجن`. الترميز الافتراضي للـ CMD على ويندوز (`cp1252`) لا يدعم هذه الأحرف والرموز مما يسبب استثناء `UnicodeEncodeError`.
* **سجل الخطأ (Traceback):**
  ```text
  File "D:\Final Project\Logic_System\emotion & face recognition final_v6\face\face_processor.py", line 33, in <module>
      print("[FaceProc] \u2705 DeepFace loaded")
  UnicodeEncodeError: 'charmap' codec can't encode character '\u2705' in position 11: character maps to <undefined>
  ```
* **الحل البرمجي المقترح:**
  إجبار لغة بايثون على تهيئة قنوات الإخراج القياسية (`sys.stdout` و `sys.stderr`) باستخدام ترميز `UTF-8` برمجياً في بداية ملف [main.py](file:///d:/Final%20Project/Logic_System/emotion%20&%20face%20recognition%20final_v6/main.py):
  ```python
  import sys
  if sys.platform == 'win32':
      sys.stdout.reconfigure(encoding='utf-8')
      sys.stderr.reconfigure(encoding='utf-8')
  ```
  أو تعديل ملف البدء [run.bat](file:///d:/Final%20Project/Logic_System/emotion%20&%20face%20recognition%20final_v6/run.bat) ليقوم بتحديد متغير البيئة `PYTHONUTF8` قبل تشغيل السكربت:
  ```bat
  @echo off
  set PYTHONUTF8=1
  py -3.12 main.py
  pause
  ```

---

## 2. خطأ منطقي في تسمية الأشخاص المحظورين (Blocked Faces Bug)
* **درجة الخطورة:** 🟠 متوسطة (سلوك منطقي خاطئ عند وجود أكثر من شخص محظور)
* **المشكلة:** 
  في ملف [main.py](file:///d:/Final%20Project/Logic_System/emotion%20&%20face%20recognition%20final_v6/main.py#L375)، عند رصد وجه محظور، يستدعي النظام الدالة `identify_blocked` للتحقق مما إذا كان الوجه محظوراً أم لا، وهي تعيد حالياً قيمة منطقية (`True`/`False`) فقط. لكن الكود يحاول تسمية هذا الشخص بأخذ **أول اسم محظور** يجده في قاعدة البيانات عشوائياً بدلاً من مطابقة الشخص الفعلي:
  ```python
  block_label = next(
      (b for b in db if b.startswith("__blocked__")),
      "__blocked__unknown"
  )
  ```
  هذا يعني أنه لو تم حظر شخصين (مثلاً: `__blocked__stranger1` و `__blocked__stranger2`)، فسيقوم النظام دائماً بتسمية أي شخص محظور يدخل الكاميرا بالاسم الأول فقط.
* **الحل البرمجي المقترح:**
  تعديل دالة `identify_blocked` في [face_processor.py](file:///d:/Final%20Project/Logic_System/emotion%20&%20face%20recognition%20final_v6/face/face_processor.py#L206) لتعيد **الاسم الفعلي للشخص المحظور المتطابق** (أو `None` إن لم يتطابق):
  ```python
  def identify_blocked(self, emb: np.ndarray, db: dict) -> Optional[str]:
      ...
      for name, rec in db.items():
          if not name.startswith("__blocked__"): continue
          ...
          if avg <= BLOCK_THRESHOLD:
              return name # يعيد الاسم الفعلي بدلاً من True
      return None
  ```
  ثم تحديث كود الاستقبال في [main.py](file:///d:/Final%20Project/Logic_System/emotion%20&%20face%20recognition%20final_v6/main.py#L375):
  ```python
  matched_block = self._face_proc.identify_blocked(emb, db)
  if matched_block:
      self._face_proc.threshold = original_thresh
      results.append((
          self._face_proc._grid_key(box),
          matched_block, 1.0, "N/A", 0.0, box, area
      ))
      continue
  ```

---

## 3. كود مهمل وغير مستخدم (Dead Code)
* **درجة الخطورة:** 🟢 منخفضة (تنظيف وتخفيف الكود)
* **المشكلة:**
  يحتوي ملف [main.py](file:///d:/Final%20Project/Logic_System/emotion%20&%20face%20recognition%20final_v6/main.py#L77) على كلاس كامل لـ الكاش المؤقت لملفات الصوت `_TTSCache` ويقوم بتهيئة كائن منه في دالة البداية واستدعاء `self._tts_cache.clear()` عند الخروج. ولكن **لا يتم استخدامه نهائياً** في أي جزء آخر من السكربت.
  حيث تم بناء نظام كاش حقيقي ومستقل في الموديول المشترك [shared/tts.py](file:///d:/Final%20Project/Logic_System/emotion%20&%20face%20recognition%20final_v6/shared/tts.py#L180).
* **الحل البرمجي المقترح:**
  حذف كلاس وكائن `_TTSCache` من ملف `main.py` لتنظيف وتخفيف الكود.

---

## 4. تمرير صيغة صوتية غير صحيحة لمحرك Vosk
* **درجة الخطورة:** 🟢 منخفضة (تحسين دقة وأداء التعرف على الكلام)
* **المشكلة:**
  في ملف [shared/stt.py](file:///d:/Final%20Project/Logic_System/emotion%20&%20face%20recognition%20final_v6/shared/stt.py#L221)، يتم استخراج بيانات الصوت لاستخدامها في التعرف غير المتصل بالإنترنت (Offline STT) عن طريق:
  ```python
  wav = audio.get_wav_data(convert_rate=16000, convert_width=2)
  rec.AcceptWaveform(wav)
  ```
  دالة `get_wav_data` تعيد بيانات ملف WAV كاملة **بما فيها الـ Header (الترويسة) المكونة من 44 بايت**. بينما يتوقع Vosk بيانات PCM خام (Raw PCM bytes). قد يتسبب تمرير الترويسة في ظهور تحذيرات في سجل الأخطاء أو عدم دقة طفيفة في أول جزء من الصوت.
* **الحل البرمجي المقترح:**
  تعديل السطر لاستخدام دالة `get_raw_data` التي تعيد الصوت الخام الصافي المتوافق تماماً مع محرك Vosk:
  ```python
  wav = audio.get_raw_data(convert_rate=16000, convert_width=2)
  ```

---

## 5. مسارات ملفات مطلقة صلبة (Hardcoded Absolute Paths)
* **درجة الخطورة:** 🔴 خطرة عند نقل المشروع وتشغيله في لجنة التقييم
* **المشكلة:**
  تحتوي السكربتات الخاصة بتحديث وتصحيح التقرير الأكاديمي (`correct_docx.py` و `build_done.py` و `build_final.py`) على مسار مطلق صلب ومحدد على القرص `D:` كالتالي:
  ```python
  input_path = r'D:\Final Project\Logic_System\emotion & face recognition final_v6\final_report_v6_Vision.docx'
  ```
  عند نقل المشروع لجهاز لجنة التقييم أو أي جهاز آخر لا يحتوي على قرص `D` بنفس المجلدات، ستنهار هذه السكربتات تماماً وتفشل في تصحيح ملفات الوورد.
* **الحل البرمجي المقترح:**
  تحويل هذه المسارات إلى مسارات نسبية برمجية تعتمد على موقع السكربت الحالي تلقائياً:
  ```python
  import os
  BASE_DIR = os.path.dirname(os.path.abspath(__file__))
  input_path = os.path.join(BASE_DIR, 'final_report_v6_Vision.docx')
  output_path = os.path.join(BASE_DIR, 'final_report_v6_Vision_FINAL.docx')
  ```

---
**تاريخ المراجعة:** 14 يونيو 2026  
**حالة التعديل:** ⚠️ بانتظار الإذن والموافقة للبدء في التطبيق والتعديل.
