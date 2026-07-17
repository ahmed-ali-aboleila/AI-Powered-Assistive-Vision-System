# Face Recognition - Graduation Discussion Guide

## 1. الفكرة العامة

جزء Face Recognition مسؤول عن معرفة الشخص الموجود أمام المستخدم الكفيف:

- هل الشخص معروف ومسجل؟
- هل هو شخص غير معروف؟
- هل هو شخص محظور؟
- هل يحتاج المستخدم إلى تسجيله أو تحسين تسجيله؟

الفكرة الأساسية:

> The system does not only detect that there is a face. It identifies whether this face belongs to a known registered person, an unknown person, or a blocked person, then speaks this information to the blind user.

## 2. الفرق بين Face Detection و Face Recognition

مهم جدا تفرق بينهم قدام اللجنة:

Face Detection:

- يجاوب سؤال: هل يوجد وجه في الصورة؟
- يعطي bounding box حول الوجه.

Face Recognition:

- يجاوب سؤال: هذا الوجه لمن؟
- يقارن الوجه بقاعدة الأشخاص المسجلين.

جملة جاهزة:

> Face detection tells us where the face is, while face recognition tells us whose face it is.

## 3. الـ Pipeline العام

الخطوات داخل النظام:

1. الكاميرا تلتقط frame.
2. يتم اكتشاف الوجوه باستخدام Haar Cascade للوجه الأمامي والجانبي.
3. يتم عمل تحسين بسيط للصورة مثل gamma correction.
4. يتم اختيار الوجه أو الوجوه المهمة.
5. يتم عمل liveness check باستخدام LBP texture.
6. يتم قص الوجه مع margin.
7. DeepFace/Facenet512 يستخرج embedding.
8. embedding يتم normalize.
9. يتم مقارنة embedding مع embeddings المحفوظة في قاعدة البيانات.
10. يتم حساب cosine distance.
11. يتم اختيار أقرب شخص إذا المسافة أقل من threshold والشروط الأخرى متحققة.
12. يتم استخدام vote buffer لتثبيت النتيجة قبل إعلانها.
13. النظام ينطق اسم الشخص أو يقول Unknown.

## 4. الموديل المستخدم

النظام يستخدم:

`DeepFace` مع model:

`Facenet512`

Facenet512 لا يرجع اسم الشخص مباشرة. هو يرجع vector أو embedding يمثل ملامح الوجه رقميا.

بمعنى:

- الصورة تدخل للموديل.
- الموديل يخرج embedding طوله تقريبا 512 قيمة.
- هذا embedding يمثل هوية الوجه.
- بعد ذلك النظام يقارن embedding الجديد بالـ embeddings القديمة.

إجابة جاهزة:

> Facenet512 converts each face into a numerical embedding. Similar faces should have embeddings close to each other, while different people should have larger distances.

## 5. لماذا DeepFace/Facenet512؟

استخدمنا DeepFace لأنه يعطي واجهة عملية لموديلات face recognition قوية، وFacenet512 معروف بجودة embeddings عالية.

نقطة مهمة:

> We use Facenet512 for identity representation, not for emotion. Emotion uses a separate CNN model.

دي نقطة اللجنة ممكن تسألها، فلازم تكون واضحة.

## 6. قاعدة بيانات الأشخاص

الأشخاص المسجلون يتم حفظهم في:

`face_data.pkl`

كل شخص له:

- name
- list of embeddings

يعني لا يتم تخزين الصور نفسها كأساس للتعرف، بل يتم تخزين التمثيل الرقمي للوجه.

هذا أفضل من تخزين الصور لأنه:

- أسرع في المقارنة.
- أخف في الذاكرة.
- أكثر مناسبة للـ recognition.

في `face_db.py` يوجد حد أقصى:

`MAX_EMBEDDINGS = 120`

يعني لكل شخص يتم حفظ آخر 120 embedding فقط حتى لا تكبر الذاكرة بلا حدود.

## 7. التسجيل Registration

عند تسجيل شخص جديد:

1. المستخدم يقول أمر مثل `vision register`.
2. النظام يطلب اسم الشخص.
3. يستخدم STT لسماع الاسم.
4. يكرر الاسم ويسأل yes/no للتأكيد.
5. يبدأ تصوير الشخص.
6. يعطي إرشادات صوتية:
   - انظر مباشرة
   - لف قليلا لليسار
   - لف قليلا لليمين
   - غير تعبير وجهك
7. كل 3 ثواني يعمل beep ليطمئن الشخص أن التصوير مستمر.
8. يستخرج embeddings من frames متعددة.
9. يحفظها تحت اسم الشخص في قاعدة البيانات.

جملة جاهزة:

> During registration, we do not store only one face sample. We collect multiple embeddings from different angles and expressions to make recognition more robust.

## 8. لماذا نأخذ أكثر من embedding؟

الشخص لا يظهر دائما بنفس الشكل:

- زاوية الرأس تتغير
- الإضاءة تتغير
- التعبير يتغير
- المسافة من الكاميرا تتغير
- جودة الصورة تختلف

لذلك حفظ embedding واحد فقط قد يسبب أخطاء كثيرة.

النظام يحفظ عدة embeddings للشخص، ثم عند التعرف يقارن الوجه الجديد بكل هذه العينات.

## 9. طريقة المقارنة Cosine Distance

بعد استخراج embedding جديد، النظام يقارنه مع embeddings المحفوظة.

المعادلة الأساسية:

```text
cosine distance = 1 - cosine similarity
```

كلما كانت المسافة أقل، كلما كان الوجهان أكثر تشابها.

النظام لا يأخذ embedding واحد فقط، بل:

1. يحسب المسافات لكل embeddings الخاصة بكل شخص.
2. يأخذ أفضل 10 نتائج.
3. يعمل weighted average.
4. الشخص صاحب أقل distance هو المرشح الأقرب.

إجابة جاهزة:

> We use cosine distance because face embeddings are high-dimensional vectors. Cosine distance measures the angle between vectors, which is suitable for comparing identity representations.

## 10. Threshold

ليس كل أقرب شخص يعتبر match.

لازم المسافة تكون أقل من threshold.

في المشروع:

- threshold الطبيعي تقريبا `0.51`
- في low light قد يتم استخدام threshold مختلف
- يوجد strong match distance
- يوجد gap ratio بين أفضل شخص وثاني أفضل شخص

ليه؟

عشان نقلل مشكلة إن شخص غريب يتعرف باسم شخص مسجل.

جملة مهمة:

> The nearest embedding is not automatically accepted. It must pass a threshold and a separation check from the second-best match to reduce false positives.

## 11. Gap Ratio

لو أفضل شخص قريب، لكن ثاني أفضل شخص قريب جدا أيضا، النظام لا يكون متأكد.

لذلك يستخدم `FACE_GAP_RATIO`.

المعنى:

- لو أفضل match ليس مميزا بشكل كاف عن ثاني match، النتيجة تصبح Unknown.
- هذا يقلل الخلط بين أشخاص متشابهين.

إجابة جاهزة:

> We added a gap ratio check because the best match alone is not enough. The best match should also be clearly better than the second-best match.

## 12. Voting Buffer

لو النظام قال اسم شخص من frame واحد فقط، قد يحدث خطأ.

لذلك يوجد vote buffer:

- يجمع نتائج عدة frames.
- لا يعلن الاسم إلا لو ظهر بنسبة كافية.
- يقلل التذبذب بين Unknown واسم الشخص.

في المشروع:

- minimum count تقريبا 3
- minimum ratio تقريبا 65%

جملة جاهزة:

> Voting makes recognition more stable because we do not trust a single frame. We wait for consistent recognition across multiple frames.

## 13. Liveness Check

النظام يستخدم LBP texture كـ liveness check بسيط.

LBP يقيس texture داخل منطقة الوجه.

الغرض:

- تقليل احتمالية التعرف على صورة مسطحة.
- التأكد أن الوجه يحتوي texture حقيقي.

لكن في الإضاءة الضعيفة، LBP قد يعطي نتائج خاطئة، لذلك النظام يتخطاه أحيانا في low light حتى لا يمنع المستخدم الحقيقي.

إجابة جاهزة:

> Liveness is implemented using LBP texture analysis. It is lightweight and suitable for Raspberry Pi, but we bypass it in very low light to avoid false rejection.

## 14. Unknown Person

لو الوجه لا يحقق شروط المطابقة:

- النظام يقول Unknown.
- يمكن للمستخدم تسجيل الشخص.
- يمكن تحسين التسجيل لو الشخص معروف لكنه يظهر أحيانا Unknown.

ده مهم لمشروع Assistive System لأن النظام لا يجب أن يخمن اسم شخص بدون ثقة.

جملة جاهزة:

> In an assistive system, a false positive is more dangerous than saying Unknown. So we prefer being conservative when confidence is not enough.

## 15. Improve Person

لو شخص مسجل لكن النظام أحيانا يقرأه Unknown، عندنا أمر تحسين:

`vision improve person`

النظام يسأل:

- هل تريد تحسين تسجيل أحمد؟
- ثم يأخذ embeddings إضافية.
- يضيفها لنفس الشخص بدل إنشاء شخص جديد.

ليه ده مهم؟

لأن التسجيل الأول قد لا يغطي كل الزوايا أو الإضاءة. التحسين يجعل قاعدة البيانات أقوى تدريجيا.

## 16. Blocked Person

النظام يدعم فكرة الشخص المحظور.

لو شخص لا يريد المستخدم سماع اسمه أو يريد تمييزه كحالة خاصة، يمكن حفظه كـ blocked.

الأسماء المحظورة تحفظ داخليا prefix:

`__blocked__`

ولها threshold أضيق حتى لا يتم حظر شخص بالخطأ.

## 17. Raspberry Pi Optimization

Face recognition هو أثقل جزء لأن Facenet512 يحتاج وقت أكبر من emotion model.

لذلك على Raspberry Pi استخدمنا:

- frame size أصغر: `320x240`
- recognition ليس كل frame
- cache لنتيجة التعرف لعدة ثواني
- max face واحد غالبا، الأقرب للكاميرا
- TFLite للـ emotion حتى نوفر موارد للـ recognition

جملة جاهزة:

> The main bottleneck on Raspberry Pi is face embedding extraction using Facenet512, so we reduced repeated recognition calls using caching and frame skipping while keeping the same recognition logic.

## 18. الفرق بين Accuracy و Safety

في مشروع للأشخاص المكفوفين، ليس الهدف فقط أعلى accuracy رقمية.

الأهم:

- عدم نطق اسم خاطئ لشخص غريب.
- عدم إزعاج المستخدم بتكرار الكلام.
- إعطاء Unknown عند عدم الثقة.
- إتاحة تحسين التسجيل.

جملة قوية:

> For blind users, reliability and safety are more important than forcing a prediction. If the system is uncertain, it should say Unknown instead of guessing.

## 19. نقاط القوة

- يستخدم Facenet512 embeddings.
- يدعم تسجيل أسماء جديدة بالصوت.
- يحفظ عدة embeddings لكل شخص.
- يستخدم cosine distance.
- يستخدم threshold و gap ratio لتقليل false positives.
- يستخدم voting لتثبيت الهوية.
- يدعم improve registration.
- يدعم blocked persons.
- مناسب للراسبيري من خلال caching و frame skipping.
- لا يعتمد على الإنترنت في face recognition بعد تحميل الموديلات.

## 20. الحدود المتوقعة

لازم تقول الحدود بثقة:

- الإضاءة الضعيفة قد تقلل الدقة.
- زاوية الوجه الشديدة قد تسبب Unknown.
- الأشخاص المتشابهون قد يحتاجون threshold أدق أو عينات أكثر.
- Facenet512 ثقيل على Raspberry Pi، لذلك الأداء أقل من اللابتوب.
- جودة الكاميرا مهمة جدا.
- التسجيل الضعيف يؤدي إلى تعرف ضعيف.

إجابة جاهزة:

> The system improves with better registration samples. If the initial registration is done under different angles, expressions, and lighting, recognition becomes more stable.

## 21. أسئلة متوقعة من اللجنة

### Q: Do you store face images?

No. The system stores numerical embeddings in `face_data.pkl`, not raw images as the main recognition database.

### Q: Why multiple samples per person?

Because the same person can appear with different expressions, lighting, and head angles. Multiple embeddings improve robustness.

### Q: Why can the system say Unknown for a registered person?

Because the current face may be too different from stored samples or the image quality may be low. This is safer than giving a wrong identity.

### Q: How do you reduce false positives?

Using threshold, gap ratio, voting across frames, liveness check, and multiple embeddings.

### Q: What is the heaviest part on Raspberry Pi?

Facenet512 embedding extraction is the heaviest part. We reduce its cost using frame skipping and cached recognition results.

### Q: Why not train your own face recognition model?

Training a robust face recognition model requires huge datasets and compute. Instead, we use a strong pretrained embedding model and build our own registration, matching, thresholding, voting, and assistive logic around it.

### Q: What happens if a stranger looks similar to a registered person?

The system uses gap ratio and conservative thresholds. If the match is not clearly better than other identities, it returns Unknown.

### Q: Why did you add improve person?

Because real-world users may register someone in one condition, then use the system in different lighting or angles. Improve person adds more embeddings to increase stability.

## 22. كلام مختصر تقوله في العرض

> The face recognition module first detects faces using OpenCV cascades, then checks liveness using LBP texture. For each valid face, we extract a Facenet512 embedding using DeepFace. During registration, we store multiple embeddings for each person in a local database. During recognition, we compare the new embedding with stored embeddings using cosine distance, apply thresholding, second-best gap validation, and voting across frames. If the system is not confident, it returns Unknown instead of guessing, which is safer for a blind user.

## 23. أهم الملفات في المشروع

- `face/face_processor.py`: detection, liveness, embeddings, matching, voting.
- `face/face_db.py`: حفظ وتحميل قاعدة بيانات الأشخاص.
- `face/registration.py`: تسجيل الأشخاص، تحسين التسجيل، الحذف، الحظر.
- `main.py`: دمج face recognition مع emotion و logic controller.
- `config.py`: thresholds وأداء Raspberry Pi.
- `face_data.pkl`: قاعدة بيانات الأشخاص المسجلين.

