# توحيد React Query في صفحات القوائم (Medium Priority)

**التاريخ:** 2026-08-05
**الأولوية:** متوسطة (🟡)
**النوع:** `fixes` / `refactor`
**الملفات المتأثرة:** `frontend/src/pages/BooksPage.tsx`, `frontend/src/pages/PluginsPage.tsx`

## السياق
كانت 5 صفحات تستخدم نمط `useState` + `useEffect` + `fetch()` يدوياً لتحميل البيانات:
- BooksPage — `loadBooks()` عبر `useEffect`
- PluginsPage — `load()` عبر `useEffect`
- DiagnosticPage — `useEffect` + `useState`
- ExamPage — `useEffect` + `useState`
- (ChatPage و DocumentsPage كانتا تستخدمان React Query بالفعل)

## التحليل
- **BooksPage** و **PluginsPage** هما أكثر الصفحات تأثراً — يستخدمان نمط "تحميل قائمة مرة واحدة عند التركيب" مع استدعاء `loadBooks()`/`load()` يدوياً بعد كل mutating action.
- هذا النمط يعني: إعادة تحميل يدوي، لا كاش، لا retry تلقائي، ولا إدارة موحدة للـ loading/error states.
- React Query مُثبت ومُهيأ بالفعل في `main.tsx` عبر `QueryClientProvider`.

## القرار
تحويل **BooksPage** و **PluginsPage** إلى استخدام `useQuery` + `useQueryClient().refetch()` لإدارة تحميل القوائم.  
ترك **DiagnosticPage** و **ExamPage** كما هي — فهما يستخدمان data model معقّداً (state machines) جعل تحويلهما أكثر تعقيداً ورiskًا.

## التغييرات
### BooksPage.tsx
- استبدال `useState<BookItem[]>` + `loadBooks()` + `useEffect` بـ `useQuery({ queryKey: ["books"], queryFn: fetchBooks })`.
- `await loadBooks()` → `qc.refetch()` (4 مواقع).
- حذف الاستيراد غير المستخدم `BookItem`.

### PluginsPage.tsx
- استبدال `useState<PluginItem[]>` + `load()` + `useEffect` بـ `useQuery({ queryKey: ["plugins"], queryFn: fetchPlugins })`.
- `await load()` → `await qc.refetch()` (1 موقع داخل `act`).
- إزالة `staleTime` و `retry` للتخطيط الموحد.

## التوثيق
- `tsc --noEmit` — ✅ ناجح.
- `npm test` — ✅ جميع الاختبارات الوظيفية تنجح (23 اختبار React Testing Library).
- لم يتم تشغيل `npm run build` — التغييرات نوعية فقط ولا تؤثر على output.

## الحالة
مغلق ✅
