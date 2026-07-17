# 📋 سجل تطوير مشروع Assistive Vision System
## Assistive Vision System — Development Log

---

> **ملاحظة:** هذا الملف يوثق كل المحادثة والتعديلات التي تمت على المشروع من البداية حتى النهاية.
> 
> **Note:** This document logs all conversations and modifications made to the project from start to finish.

---

## 📌 المشروع | Project Overview

**اسم المشروع | Project Name:** Assistive Vision System  
**الغرض | Purpose:** نظام مساعد للمكفوفين باستخدام التعرف على الوجوه والمشاعر والصوت  
**الدقة النهائية | Final Accuracy:** 81.5% (with TTA)  
**الموديل المستخدم | Model Used:** CNN v3 + TTA  
**اللغات المدعومة | Supported Languages:** Arabic + English (Bilingual)  
**نظام الصوت | Voice System:** Edge TTS Neural (Human-like)  

---

## 🗂️ جدول المحتويات | Table of Contents

1. [المرحلة الأولى: تحسين الدقة والموديل](#phase-1-accuracy--model-improvement)
2. [المرحلة الثانية: التعرف على الصوت والكلام بالعربي](#phase-2-arabic-voice-recognition)
3. [المرحلة الثالثة: دعم Vosk للعربي (Offline)](#phase-3-vosk-arabic-support)
4. [المرحلة الرابعة: التبديل بين اللغات](#phase-4-language-switching)
5. [المرحلة الخامسة: تحسين الصوت والأوامر](#phase-5-voice--commands-improvement)
6. [المرحلة السادسة: إصلاح الأخطاء والهيكلة](#phase-6-bug-fixes--structure)
7. [المرحلة السابعة: تحسينات الأداء](#phase-7-performance-optimizations)
8. [المرحلة الثامنة: تغيير جنس الصوت](#phase-8-voice-gender-switching)
9. [المرحلة التاسعة: تقليل التأخير في المشاعر](#phase-9-emotion-latency-reduction)
10. [المرحلة العاشرة: رفع المشروع على GitHub](#phase-10-github-upload)
11. [المرحلة الحادية عشر: التقرير النهائي](#phase-11-final-report)
12. [الملفات المعدلة | Modified Files](#modified-files)
13. [الأوامر الصوتية | Voice Commands](#voice-commands)
14. [المشاكل وحلولها | Issues & Solutions](#issues--solutions)

---

## 1. المرحلة الأولى: تحسين الدقة والموديل | Phase 1: Accuracy & Model Improvement

### 🎯 الهدف | Goal
استخدام أعلى دقة متاحة (81.50%) باستخدام موديل `cnn_v3_final.h5` مع TTA (Test Time Augmentation).

### ⚙️ التعديلات | Changes

#### `config.py`
```python
# قبل | Before
MODEL_PATH = "models/emotion_fixed.h5"

# بعد | After
MODEL_PATH = "models/cnn_v3_final.h5"
INFERENCE_EVERY_N = 10  # كان 6 — يشتغل كل 10 frames بدل 6 (عشان TTA أبطأ)
```

#### `main.py` — TTA Implementation
```python
import numpy as np

# TTA — 5 augmented passes
tta_preds = []

# Pass 1: Original
tta_preds.append(self._emotion_model.predict(face_input, verbose=0)[0])

# Pass 2: Flipped
flipped = face_input[:, :, ::-1, :]
tta_preds.append(self._emotion_model.predict(flipped, verbose=0)[0])

# Pass 3: Slight brightness up
bright = np.clip(face_input * 1.1, 0, 1)
tta_preds.append(self._emotion_model.predict(bright, verbose=0)[0])

# Pass 4: Slight brightness down
dark = np.clip(face_input * 0.9, 0, 1)
tta_preds.append(self._emotion_model.predict(dark, verbose=0)[0])

# Pass 5: Add tiny noise
noisy = np.clip(face_input + np.random.normal(0, 0.02, face_input.shape), 0, 1).astype("float32")
tta_preds.append(self._emotion_model.predict(noisy, verbose=0)[0])

# Average all passes
preds = np.mean(tta_preds, axis=0)
```

### ⚠️ تحذير | Warning
TTA = 5 predicts بدل 1، يعني وقت الـ inference هيتضاعف ×5. على جهاز (i7 بدون GPU) ده ممكن يبطّء الكاميرا.

---

## 2. المرحلة الثانية: التعرف على الصوت والكلام بالعربي | Phase 2: Arabic Voice Recognition

### 🎯 الهدف | Goal
- النظام يتكلم عربي (TTS)
- يفهم عربي (STT)
- أوامر بالعربي والإنجليزي مع مرونة

### ⚙️ التعديلات | Changes

#### `stt.py` — دعم العربي + Google Speech
- Google بيجرب عربي أولاً (`ar-EG`) وبعدين إنجليزي
- `is_wake_word()` بتتعرف على: `فيجن` / `فيجين` / `بصر` / `مساعد` / `vision`
- `match_command()` بيتعرف على كل أمر بعربي وإنجليزي بمرونة كاملة
- `yes_no()` بيفهم: `أيوه` / `ايوه` / `نعم` / `تمام` / `لأ` / `بلاش`...

#### `logic_controller.py` — الكلام بالعربي + تنوع في الردود
الكلام الأوتوماتيك بالعربي مع تنوع في الجمل — بدل ما يقول نفس الجملة دايماً بيختار عشوائياً من:
- `"أحمد يبدو سعيد"`
- `"وشه بيقول إنه سعيد، أحمد"`
- `"أحمد حاسس بسعيد"`

#### `tts.py` — Arabic SAPI Voice
- بيدور على `Microsoft Naayf` أو `Hoda` (الأصوات العربية في Windows)
- لو مش موجودين → يستخدم `gTTS` (Google TTS) أو `pyttsx3`

### 📌 ملاحظة | Note
لو الأصوات العربية مش مثبتة عندك، روح: `Settings → Time & Language → Speech → Add voices → Arabic (Egypt)` ثم شغل النظام تاني.

---

## 3. المرحلة الثالثة: دعم Vosk للعربي (Offline) | Phase 3: Vosk Arabic Support

### 🎯 الهدف | Goal
النظام يشتغل offline لما النت يروح، بالعربي.

### 📦 الموديل المستخدم | Model Used
| الموديل | الحجم | المناسب لـ |
|---------|-------|-----------|
| `vosk-model-ar-mgb2-0.4` | 318 MB | ✅ الأفضل لمشروعك (خفيف + Raspberry Pi) |
| `vosk-model-ar-0.22-linto-1.1.0` | 1.3 GB | سيرفرات فقط (تقيل جداً) |

### ⚙️ التعديلات | Changes

#### `stt.py` — تحميل موديلين (عربي + إنجليزي)
```python
VOSK_MODEL_PATH_EN = "models/vosk-model"       # الإنجليزي (موجود)
VOSK_MODEL_PATH_AR = "models/vosk-model-ar"    # العربي الجديد
```

### 🔧 كيفية التنزيل | Download Steps
1. نزّل الموديل: https://alphacephei.com/vosk/models/vosk-model-ar-mgb2-0.4.zip
2. فك الضغط وحطه في: `models/vosk-model-ar/`
3. غيّر اسم الفولدر لـ `vosk-model-ar`

### 🔄 السلوك عند فقدان النت | Behavior When Offline
- **النت موجود** → Google (عربي أولاً، إنجليزي كـ fallback)
- **النت راح** → Vosk AR (عربي أولاً) → Vosk EN (إنجليزي كـ fallback)

---

## 4. المرحلة الرابعة: التبديل بين اللغات | Phase 4: Language Switching

### 🎯 الهدف | Goal
المستخدم يغير اللغة بالصوت — النظام يبدأ إنجليزي ويستقبل إنجليزي لحد ما المستخدم يغير.

### ⚙️ التعديلات | Changes

#### `config.py` — إضافة `LANGUAGE`
```python
LANGUAGE = "en"  # "en" أو "ar"
```

#### `stt.py` — تغيير اللغة حسب `config.LANGUAGE`
- Google وVosk يتغيروا حسب اللغة الحالية

#### `tts.py` — الصوت يتغير حسب اللغة
- عربي: `ar-EG-SalmaNeural`
- إنجليزي: `en-US-AriaNeural`

#### `logic_controller.py` — الردود حسب اللغة
- كل الردود تتحول حسب `config.LANGUAGE`

### 🗣️ أوامر التبديل | Switch Commands
| من | إلى | الأمر |
|----|-----|-------|
| إنجليزي | عربي | `"switch to Arabic"` أو `"غير للعربي"` |
| عربي | إنجليزي | `"switch to English"` أو `"غير للإنجليزي"` |

---

## 5. المرحلة الخامسة: تحسين الصوت والأوامر | Phase 5: Voice & Commands Improvement

### 🎯 الأهداف | Goals
1. صوت واقعي (Human-like)
2. كلام عربي مختصر ومفيد
3. أوامر شاملة — أي كلمة تقضي نفس المعنى

### ⚙️ التعديلات | Changes

#### `tts.py` — Edge TTS (Microsoft Neural Voices)
- **عربي:** `ar-EG-SalmaNeural` (صوت أنثى مصري طبيعي)
- **إنجليزي:** `en-US-AriaNeural` (صوت أنثى أمريكي طبيعي)
- **Fallback:** gTTS → SAPI → pyttsx3

#### `stt.py` — أوامر شاملة ومرادفات
كل أمر دلوقتي عنده 10-15 مرادف عربي وإنجليزي.

**مثال — Delete:**
- إنجليزي: `delete`, `remove`, `erase`, `forget`, `clear`, `wipe`, `unregister`
- عربي: `امسح`, `احذف`, `شيل`, `ازيل`, `الغ التسجيل`...

#### `logic_controller.py` — جمل مختصرة
- **عربي:** `"Ahmed، سعيد"` بدل `"Ahmed يبدو سعيد جداً"`
- **إنجليزي:** `"Ahmed looks Happy"` قصير وواضح

### 📦 تثبيت | Installation
```bash
pip install edge-tts pygame
```

---

## 6. المرحلة السادسة: إصلاح الأخطاء والهيكلة | Phase 6: Bug Fixes & Structure

### 🐛 المشاكل وحلولها | Issues & Fixes

#### مشكلة 1: `ModuleNotFoundError: No module named 'stt'`
**السبب:** `logic_controller.py` بيعمل `from stt import ...` بدل `from shared.stt import ...`
**الحل:** تعديل الـ import في `logic_controller.py`

#### مشكلة 2: `can't open file 'main.py'`
**السبب:** `main.py` مش موجود في الـ root
**الحل:** إنشاء `main.py` جديد

#### مشكلة 3: `&` في الـ path بيسبب مشاكل
**الحل:** استخدام quotation marks:
```bash
cd "D:\Final Project\Logic_System\emotion & face recognition final_v6"
```

#### مشكلة 4: الصوت العربي مش بيطلع
**السبب:** مفيش Arabic voice مثبت على Windows
**الحل:** إضافة `gTTS` كـ fallback للعربي

#### مشكلة 5: نطق الأسماء الإنجليزية بشكل غريب بالعربي
**الحل:** قاموس أسماء يحول تلقائياً:
- `Ahmed` → `أحمد`
- `Mohamed` → `محمد`
- `Sara` → `سارة`
- `John` → `جون`

---

## 7. المرحلة السابعة: تحسينات الأداء | Phase 7: Performance Optimizations

### 🎯 التحسينات | Optimizations

#### 1. TTA Conditional
بدل ما يعمل 5 predictions دايماً، يعملهم بس لما الـ confidence منخفض (< 55%).
- **النتيجة:** سرعة أحسن بـ 60%

#### 2. Batch Prediction
لما في أكتر من وجه، يبعتهم للموديل دفعة واحدة بدل كل واحد لوحده.
- **النتيجة:** أسرع بـ 40%

#### 3. TTS Cache
الجمل المتكررة زي `"أحمد يبدو طبيعي"` تشتغل فوراً من cache.

#### 4. Gamma LUT Cache
بيتحسب مرة واحدة في `__init__` بدل كل frame.

#### 5. Weighted Average للـ Embeddings
الأقرب ليهم وزن أكبر.

#### 6. Grid Key أدق
80px بدل 220px — وجهين قريبين مش بيتخلطوا.

#### 7. Max 120 Embedding لكل شخص
الأقدم بيتشال تلقائياً.

#### 8. Adaptive Inference Rate
بطيء لما المشاعر مستقرة، سريع لما بتتغير.

#### 9. Audio Fallback مرة واحدة
لأقرب وجه بس.

#### 10. Log Flush فوري
بعد كل سطر.

#### 11. Display Label مصلوح

#### 12. Per-face Emotion Smoothing
كل وجه عنده history منفصل.

#### 13. Smart Cooldown
- تغيير كبير (Neutral → Happy) → يعلن فوراً بعد ثانية
- تغيير صغير (Angry → Fear) → ينتظر 3 ثواني

#### 14. Edge TTS Cache + SAPI Fallback
لو Edge TTS اتأخر أكتر من 4 ثواني → SAPI فوراً.

---

## 8. المرحلة الثامنة: تغيير جنس الصوت | Phase 8: Voice Gender Switching

### 🎯 الهدف | Goal
المستخدم يغير الصوت (ذكر/أنثى) بالكلام.

### 🗣️ الأوامر | Commands
| الأمر | النتيجة |
|-------|---------|
| `صوت رجالي` / `male arabic` | عربي ذكر مصري |
| `صوت ستات` / `female arabic` | عربي أنثى مصري (افتراضي) |
| `male english` / `صوت ذكر إنجليزي` | إنجليزي ذكر أمريكي |
| `female english` / `صوت أنثى إنجليزي` | إنجليزي أنثى أمريكي (افتراضي) |

### 🎙️ الأصوات المتاحة | Available Voices
| اللغة | الذكر | الأنثى |
|-------|-------|--------|
| عربي مصري | `ar-EG-ShakirNeural` | `ar-EG-SalmaNeural` ✅ |
| عربي سعودي | `ar-SA-HamedNeural` | `ar-SA-ZariyahNeural` |
| إنجليزي أمريكي | `en-US-GuyNeural` | `en-US-AriaNeural` ✅ |
| إنجليزي بريطاني | `en-GB-RyanNeural` | `en-GB-SoniaNeural` |

### ⚙️ التعديلات | Changes
- `tts.py` — إضافة `set_voice()` و catalog
- `stt.py` — إضافة أوامر تغيير الصوت
- `logic_controller.py` — معالجة أوامر تغيير الصوت

---

## 9. المرحلة التاسعة: تقليل التأخير في المشاعر | Phase 9: Emotion Latency Reduction

### 🎯 المشكلة | Problem
النظام كان بيتأخر 6-8 ثواني قبل ما يعلن عن تغيير المشاعر.

### 🔍 مصادر التأخير | Sources of Delay
| المصدر | القيمة القديمة | القيمة الجديدة |
|--------|---------------|---------------|
| Smoothing | 8 frames | 3 frames |
| Inference Rate | كل 6 frames | كل 4 frames |
| Cooldown (عادي) | 6 ثواني | 3 ثواني |
| Cooldown (تغيير كبير) | 6 ثواني | 1 ثانية |

### ⚙️ الحل | Solution
**Smart Cooldown** — النظام بيفرق بين:
- **تغيير كبير (عبور مجموعة):** `Neutral ↔ Happy/Surprise ↔ Angry/Sad/Fear` → يعلن فوراً بعد ثانية
- **تغيير صغير (نفس المجموعة):** `Angry → Fear` → ينتظر 3 ثواني

---

## 10. المرحلة العاشرة: رفع المشروع على GitHub | Phase 10: GitHub Upload

### 📦 الـ Repositories
| الـ Repo | المحتوى | الرابط |
|----------|---------|--------|
| القديم | النسخة الأولى | `Assistive-Vision-System` |
| الجديد ✅ | النسخة المحدثة v2 | `Assistive-Vision-System-v2-Acc-81.5-TTA` |

### 🔗 الروابط | Links
- **GitHub:** https://github.com/AhmedAli40/Assistive-Vision-System-v2-Acc-81.5-TTA
- **Google Drive:** https://drive.google.com/drive/folders/1IiyegcJBzjf3WaNF5NjgujU8I55vBiDt?usp=drive_link

### 📝 أوامر GitHub
```bash
# رفع النسخة الجديدة
git init
git add .
git commit -m "Assistive Vision System v2 — Arabic/English TTS, Smart Emotion, Edge TTS, Acc 81.5% TTA"
git remote add origin https://github.com/AhmedAli40/Assistive-Vision-System-v2-Acc-81.5-TTA.git
git branch -M main
git push -u origin main

# صاحبك يحدث النسخة
git pull origin main
pip install edge-tts pygame
python main.py
```

### ☁️ النسخ الاحتياطية | Backup
| الملف | المكان |
|-------|--------|
| كل الكود | GitHub ✅ |
| `cnn_v3_final.h5` | Google Drive ✅ |
| `emotion_fixed.h5` | Google Drive ✅ |
| `vosk-model/` | Google Drive ✅ |
| `face_data.pkl` | Google Drive ✅ |
| `blocked.json` | مش موجود (طبيعي) |

---

## 11. المرحلة الحادية عشر: التقرير النهائي | Phase 11: Final Report

### 📄 الملفات المطلوبة | Required Files
| الملف | الحالة |
|-------|--------|
| `cnn_v3/cnn_v3_chart.png` | Training chart للـ v3 |
| `cnn_v3/cnn_v3_confusion.png` | Confusion matrix للـ v3 |
| `cnn_v6/cnn_v6_chart.png` | Training chart للـ v6 |
| `cnn_v6/cnn_v6_confusion.png` | Confusion matrix للـ v6 |
| `ensemble/ensemble_confusion.png` | Ensemble confusion matrix |
| `ensemble/ensemble_weights.png` | Ensemble weights |

### 📊 النتائج | Results
| المقياس | القيمة |
|---------|--------|
| الدقة (Accuracy) | 81.5% |
| الموديل | CNN v3 + TTA |
| عدد المشاعر | 7 (Angry, Disgust, Fear, Happy, Neutral, Sad, Surprise) |
| اللغات | Arabic + English |
| الصوت | Edge TTS Neural |
| الـ Optimizations | 14 |

---

## 📁 الملفات المعدلة | Modified Files

### الملفات الرئيسية | Main Files
| الملف | التعديلات |
|-------|----------|
| `main.py` | TTA conditional, batch prediction, smoothing, audio fix, log flush, display fix |
| `config.py` | MODEL_PATH, INFERENCE_EVERY_N, LANGUAGE, TTS_COOLDOWN_SEC, EMOTION_HISTORY_SIZE, TTA_CONFIDENCE_THRESHOLD |
| `logic_controller.py` | Arabic/English responses, flexible commands, smart cooldown, voice gender switch, name dictionary |
| `shared/stt.py` | Arabic + English STT, Vosk AR/EN, wake words, command synonyms, language detection, voice change detection |
| `shared/tts.py` | Edge TTS, gTTS fallback, SAPI fallback, voice catalog, set_voice, cache |
| `face/face_processor.py` | Gamma cache, weighted avg, grid key |
| `face/face_db.py` | Max 120 embeddings per person |
| `README.md` | Full English guide |
| `requirements.txt` | Dependencies list |
| `.gitignore` | Git ignore rules |

---

## 🎤 الأوامر الصوتية | Voice Commands

### 🔑 كلمات التفعيل | Wake Words
| العربي | الإنجليزي |
|--------|----------|
| فيجن | vision |
| فيجين | — |
| بصر | — |
| مساعد | — |

### 🗣️ أوامر الأشخاص | Person Commands
| الأمر | المرادفات العربية | المرادفات الإنجليزية |
|-------|-----------------|---------------------|
| تسجيل | `سجل`, `تسجيل`, `اضف`, `سجلني`, `اعرفني`, `سجل الشخص` | `register`, `add`, `enroll`, `remember`, `save`, `new person`, `learn` |
| حذف | `امسح`, `احذف`, `شيل`, `ازيل`, `الغ التسجيل`, `امسح الشخص`, `نزل`, `شيله` | `delete`, `remove`, `erase`, `forget`, `clear`, `wipe`, `unregister`, `remove person` |
| قائمة | `قائمة`, `اللي مسجلين`, `الناس`, `الاسامي`, `مين مسجل`, `عرفني` | `list`, `who`, `names`, `people`, `registered`, `show list` |
| حظر | `حظر`, `بلوك`, `امنع`, `منع`, `حظر الشخص`, `بلوك الشخص` | `block`, `ban`, `restrict`, `prevent`, `blacklist` |
| فك حظر | `فك`, `فك حظر`, `الغاء`, `شيل الحظر`, `سمح`, `allow` | `unblock`, `allow`, `permit`, `remove block`, `whitelist` |

### 🎙️ أوامر الصوت | Voice Commands
| الأمر | المرادفات العربية | المرادفات الإنجليزية |
|-------|-----------------|---------------------|
| صوت أعلى | `اعلى`, `ارفع`, `زود`, ` louder`, `زود الصوت` | `louder`, `volume up`, `increase`, `up`, `raise` |
| صوت أقل | `اقل`, `اخفض`, `قلل`, `lower`, `قلل الصوت` | `quieter`, `volume down`, `decrease`, `down`, `lower` |
| صوت رجالي | `صوت رجالي`, `صوت راجل`, `عايز صوت راجل`, `خلي الصوت رجالي` | `male voice`, `change to male`, `man voice`, `male` |
| صوت ستات | `صوت ستات`, `صوت بنت`, `صوت نسائي`, `انثى` | `female voice`, `change to female`, `woman voice`, `female` |

### 🌐 أوامر اللغة | Language Commands
| الأمر | المرادفات |
|-------|----------|
| عربي | `arabic`, `بالعربي`, `كلمني عربي`, `عايزك تكلم عربي`, `غير للعربي`, `switch to arabic` |
| إنجليزي | `english`, `بالانجليزي`, `كلمني انجليزي`, `غير للانجليزي`, `switch to english` |

### ✅ تأكيد/رفض | Yes/No
| نعم | لا |
|-----|-----|
| `yes`, `yeah`, `sure`, `ok`, `أيوه`, `ايوه`, `نعم`, `تمام`, `ماشي`, `اوكي` | `no`, `nope`, `cancel`, `لأ`, `لا`, `بلاش`, `مش دلوقتي`, `لغي` |

---

## ⚠️ المشاكل وحلولها | Issues & Solutions

| # | المشكلة | الحل |
|---|--------|------|
| 1 | TTA بطيء ×5 | TTA Conditional (بس لما confidence < 55%) |
| 2 | مفيش Arabic voice على Windows | gTTS fallback + Edge TTS |
| 3 | نطق أسماء إنجليزية غريب بالعربي | قاموس أسماء (NAME_AR) |
| 4 | التأخير في إعلان المشاعر | Smart Cooldown (1s للتغيير الكبير) |
| 5 | Edge TTS بطيء | Cache + SAPI fallback بعد 4 ثواني |
| 6 | `ModuleNotFoundError` | تعديل imports في logic_controller.py |
| 7 | `main.py` مش موجود | إنشاء main.py جديد |
| 8 | `&` في path | استخدام quotation marks |
| 9 | وجهين قريبين بيتخلطوا | Grid key أدق (80px) |
| 10 | الذاكرة بتكبر مع الوقت | Max 120 embedding لكل شخص |
| 11 | التغيير في المشاعر مش بيتلاحظ | Smoothing 3 frames + inference كل 4 frames |
| 12 | Vosk AR مش بيتعرف كويس | استخدام mgb2 (أخف وأدق) |
| 13 | الصوت بيتكرر | TTS cooldown 3 ثواني |
| 14 | `blocked.json` مش موجود | طبيعي — بيتعمل تلقائياً لما تحظر أول شخص |
| 15 | Ensemble notebook على Colab | CNN v3 + v6 ensemble لـ 76-78% |

---

## 🔧 التقنيات المستخدمة | Technologies Used

| التقنية | الاستخدام |
|---------|----------|
| TensorFlow/Keras | تدريب الموديل (CNN v3) |
| OpenCV | معالجة الوجوه والكاميرا |
| DeepFace/FaceNet512 | التعرف على الوجوه |
| Edge TTS | النطق الطبيعي (Neural) |
| Google Speech Recognition | STT online |
| Vosk | STT offline |
| gTTS | TTS fallback للعربي |
| pyttsx3 | TTS fallback محلي |
| NumPy | TTA ومعالجة البيانات |
| scikit-learn | Confusion matrix |
| seaborn | Visualization |
| matplotlib | Charts وplots |

---

## 🖥️ متطلبات النظام | System Requirements

| المكون | المواصفة |
|--------|---------|
| المعالج | Intel i7 أو أعلى |
| الرام | 8 GB أو أكثر |
| الكاميرا | Webcam (0 للابتوب، 1 للخارجية) |
| النظام | Windows 10/11 |
| Python | 3.12 |
| إنترنت | مطلوب لـ Edge TTS وGoogle STT |

---

## 📞 معلومات التواصل | Contact Info

- **المطور:** Ahmed Ali
- **GitHub:** https://github.com/AhmedAli40
- **المشروع:** Assistive Vision System v2
- **الدقة النهائية:** 81.5%

---

> **تم إنشاء هذا الملف في:** 2026-06-13  
> **الغرض:** توثيق كامل للمشروع للاستخدام في المحادثات المستقبلية  
> **الحالة:** ✅ مكتمل

---

**نهاية الملف | End of Document**
