# נאות נבון — Dashboard אנליטי

מערכת אינטראקטיבית לחקירת פרויקט **שובל טאץ' נאות נבון חיפה**.

כלי חקירה וניתוח בלבד — ללא המלצות השקעה וללא תחזיות.

## דרישות

- Python 3.10+
- מאגר הנתונים `naot_navon_database/` באותה רמה כמו תיקיית ה-dashboard

```
C:\Users\nmaatuk\
├── naot_navon_database\
│   ├── apartments_database.json    ← מקור ראשי
│   ├── apartments_quality_analysis.json
│   └── apartments_value_analysis.json
└── naot_navon_dashboard\
    └── app.py
```

## התקנה

```bash
cd naot_navon_dashboard
pip install -r requirements.txt
```

## הפעלה

```bash
streamlit run app.py
```

הדפדפן ייפתח בכתובת: http://localhost:8501

## מסכים

| מסך | תיאור |
|-----|--------|
| סקירה | מדדים כלליים, התפלגות חדרים וקומות |
| חוקר דירות | טבלה עם סינון לפי מחיר, חדרים, קומה, נוף, ציונים |
| מפת חום | בניין × קומה — איכות / מחיר / Value |
| דירוג | Top 20 לפי Value, Quality, Premium Exit או מחיר למ"ר |
| Premium Exit | דירוג פוטנציאל ביקוש בשוק החופשי + הסברים טקסטואליים |
| השוואה | השוואה בין 2–5 דירות |
| סימולטור | דירות מתאימות לתקציב |
| גרפים | גרפי מחיר, התפלגות, Quality/Value מול מחיר |

## עדכון נתונים

1. עדכן `naot_navon_database/apartments_database.json`
2. הרץ מחדש את סקריפטי הניתוח (אם נדרש):
   ```bash
   python ../naot_navon_database/analyze_quality.py
   python ../naot_navon_database/analyze_value.py
   ```
3. רענן את ה-dashboard בדפדפן (או נקה cache מהתפריט)

## מבנה פרויקט

```
naot_navon_dashboard/
├── app.py
├── requirements.txt
├── README.md
├── data/
│   ├── loader.py      # טעינה מ-apartments_database.json
│   └── paths.py
├── components/
│   ├── overview.py
│   ├── explorer.py
│   ├── heatmap.py
│   ├── ranking.py
│   ├── comparison.py
│   ├── simulator.py
│   └── charts.py
└── utils/
    ├── floor.py
    └── formatters.py
```
