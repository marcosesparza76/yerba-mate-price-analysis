## 📋 Overview

**Yerba Mate Price Tracker** is an end-to-end Data Science and Business Intelligence project designed to collect, process, and analyze the historical and real-time price evolution of Yerba Mate in Argentina. 
> 🚀 **Live Interactive Dashboard:** Explore real-time shelf prices, brand dispersion, and inflation-adjusted historical trends at **[Yerba Mate Price Monitor (Streamlit App)](https://yerba-mate-price-analysis-monitor.streamlit.app)**.

The project evaluates the market impact of the **DNU 70/2023** deregulation (which eliminated price controls previously set by the *National Institute of Yerba Mate - INYM*), measures the price gap between primary producers and retail shelves, and compares nominal price increases against general inflation using the **Consumer Price Index (IPC - INDEC)**.

---

## 🎯 Key Objectives

1. **Historical & Structural Analysis:** Model weekly and monthly price fluctuations from 2015 to 2025 using official and econometric datasets.
2. **Deregulation Impact Assessment:** Compare real prices (in constant currency) before and after December 2023.
3. **Real-Time Retail Monitoring:** Automate current shelf-price extraction via web scraping (targeting major retail chains such as **Jumbo Argentina**) standardized per kilogram (`ARS/kg`).
4. **Interactive Visualization:** Build an executive Power BI dashboard and exploratory Python notebooks to detect price anomalies and brand dispersion.

---

## 📊 Data Sources & References

This project integrates historical datasets, official government reports, and live web scraping:

* **Ministry of Deregulation and State Transformation (Sept 2024):** Constant-peso price evolution in CABA, traded volumes, and post-DNU 70/2023 market deregulation metrics.
* **RIVAR Econometric Study (2023):** High-frequency weekly price dataset covering +300 Yerba Mate presentations (2015–2021), accounting for product attributes, seasonality, and exchange rate variations.
* **CEPA Report on the Yerba Mate Complex (Jan 2025):** Production figures, domestic consumption, exports, and farm-to-retail price spreads.
* **INDEC (IPC):** Official Consumer Price Index used to deflate nominal prices into real terms.
* **Live Retail Scraping (Jumbo Argentina):** Automated extraction of current product names, brands, weights (500g / 1kg), and retail prices.

---

## 🗂️ Repository Structure

Following standard Data Science repository conventions, the project is organized modularly:

```text
yerba-mate-price-analysis/
├── .github/
│   └── workflows/
│       └── update_data.yml           # Automated CI/CD pipeline (runs Mon & Thu)
├── dashboard/
│   └── app.py                        # Interactive Streamlit & Plotly web dashboard
├── data/
│   ├── raw/                          # Raw scrapes (Jumbo) & official datasets (INDEC, CEPA)
│   └── processed/                    # Cleaned, normalized (ARS/kg) & IPC-deflated datasets
├── notebooks/
│   └── 01_eda_historical.ipynb       # Exploratory Data Analysis notebooks
├── reports/
│   └── figures/                      # Automated statistical charts (PNG)
├── src/
│   ├── scraper_jumbo.py              # Headless browser scraper (Playwright)
│   ├── etl_pipeline.py               # Unit normalization & statistical reporting
│   ├── integrar_fuentes.py           # Multi-source join (Jumbo + INDEC IPC + CEPA)
│   └── enviar_reporte.py             # Automated Telegram & Email alert dispatcher
├── requirements.txt                  # Python dependencies
└── README.md                         # Project documentation
```

---

## ⚙️ Prerequisites & Installation

To run this project locally, ensure you have **Python 3.10+** installed.

1. **Clone the repository:**
   ```bash
   git clone https://github.com
   cd yerba-mate-price-analysis
   ```

2. **Create and activate a virtual environment (recommended):**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Core libraries include `pandas`, `numpy`, `matplotlib`, `seaborn`, `requests`, and `beautifulsoup4`.)*

---

## 🚀 Usage

1. **Run the Web Scraper (Live Data Collection):**
   ```bash
   python src/scraper_jumbo.py
   ```
   *Outputs a timestamped CSV file inside `data/raw/` containing current shelf prices.*

2. **Execute the ETL & Normalization Pipeline:**
   ```bash
   python src/etl_pipeline.py
   ```
   *Standardizes all package weights to `Price per Kg` and merges historical series with IPC inflation data into `data/processed/`.*

3. **Integrate Official Sources (INDEC IPC & CEPA):**
   ```bash
   python src/integrar_fuentes.py
   ```
   *Merges live retail prices with official Consumer Price Index (IPC) and farm-gate leaf prices (`hoja verde`) into `data/processed/dataset_maestro_yerba.csv`.*

4. **Launch the Interactive Web Dashboard:**
   ```bash
   python -m streamlit run dashboard/app.py
   ```
   *Opens the local Streamlit web application with dynamic brand filters, KPIs, and interactive Plotly charts.*

5. **Automated Cloud Execution & Alerts (CI/CD):**
   * Configured via **GitHub Actions** (`.github/workflows/update_data.yml`) to execute the full pipeline automatically twice a week, commit updated datasets/charts, and dispatch summary notifications via **Telegram Bot API** and **SMTP Email** using encrypted GitHub Secrets.

---

## 📚 Academic Assignment Notes (Theoretical Framework)

*As part of the Technical English, Data Science & AI coursework, this section summarizes the foundational concepts applied to this repository:*

### 1. API vs. README File
* **README File (`README.md`):** A static documentation file written in Markdown aimed at **human users**. It explains what a project does, how to install it, and how to use it.
* **API (Application Programming Interface):** A programmatic interface and set of protocols (e.g., REST, JSON) aimed at **software applications**, allowing automated data exchange and system-to-system communication without human intervention.

### 2. CockroachDB & Classic README Structure
An analysis of the open-source **CockroachDB** repository confirms the use of the **classic GitHub README structure**, which served as the blueprint for this document:
* **Project Title & Concise Overview**
* **Build/License Status Badges**
* **Prerequisites & Quickstart / Installation Commands**
* **Usage, Testing & Architecture Guidelines**
* **Contributing & Licensing Terms**

---

## 🛠️ Technical Challenges & Troubleshooting

During the development of the data collection and ETL pipeline, several real-world technical obstacles were identified and resolved:

1. **Dynamic Client-Side Rendering (CSR) & Endpoint Redirection:**
   * *Issue:* Initial HTTP `GET` requests to Jumbo's internal VTEX routing endpoint (`_v/segment/routing/vtex.store@2.x/...`) triggered `JSONDecodeError` or redirected to the main homepage because prices are loaded dynamically via JavaScript and require active session cookies.
   * *Solution:* Migrated the extraction module (`scraper_jumbo.py`) from static `requests` to **Playwright** (headless Chromium), simulating full browser navigation with explicit category query parameters (`initialMap`, `map`, `query`) and progressive scrolling to render all product cards.

2. **Unstructured Product Card Layout & UI Noise:**
   * *Issue:* Product cards mixed brand names, full descriptions, promotional badges, and UI buttons (`"Ver Producto"`, `"Compra rápida"`), occasionally inverting brand and product fields or capturing non-target carousel items.
   * *Solution:* Implemented a text-filtering pipeline that strips UI labels, selects the longest string as the product title, enforces a strict keyword filter (`"yerba"`), and uses regular expressions (`re`) to extract package weights (`500g`, `550g`, `1kg`) for accurate `ARS/kg` normalization.

3. **Multi-Source Integration & Inflation Deflation:**
   * *Issue:* Official reports from CEPA, Ministry of Deregulation/INYM, and INDEC (IPC) are published across different formats and nominal scales.
   * *Solution:* Created `integrar_fuentes.py` to standardize periods (`YYYY-MM`), merge retail shelf prices with farm-gate leaf prices (`hoja verde`), calculate producer share percentages, and deflate nominal values into constant currency (Base Dec-2023 = 100).

---

## 📈 Key Findings & Visualizations

* **Multi-Retailer Dispersion (236 Live SKUs):** El mercado promedia **$5,755.68 ARS/kg** (Mediana: **$5,289.62 ARS/kg**) entre **Carrefour**, **Coto** y **Jumbo**, con un rango de **$3,438.00/kg** a **$21,260.00/kg**.
* **Cross-Chain Price Positioning:** **Carrefour** lidera en competitividad (**$5,199.00/kg** en 95 SKUs), seguido por **Coto** (**$5,380.00/kg** en 123 SKUs) y **Jumbo** (**$5,472.82/kg** en 18 SKUs, con mayor presencia de marcas premium).
* **Deregulation & Producer Share Impact:** Tras el **DNU 70/2023**, los precios reales sestabilizaron tras un pico en 2024, mientras que la participación del productor primario cayó del **34.9%** (Oct 2023) al **13.3%–16.4%** (2025–2026).

![Brand Price Ranking]((https://github.com/marcosesparza76/yerba-mate-price-analysis/blob/main/reports/figures/01_ranking_precios_marca.png))
![Historical Price Evolution](https://github.com/marcosesparza76/yerba-mate-price-analysis/blob/main/reports/figures/02_evolucion_historica_dnu.png))
![Producer Share vs Real Retail Price](https://github.com/marcosesparza76/yerba-mate-price-analysis/blob/main/reports/figures/03_brecha_productor_ipc.png)
![Retail Chain Comparison](https://github.com/marcosesparza76/yerba-mate-price-analysis/blob/main/reports/figures/04_comparativa_supermercados.png)

---

## 🔬 Methodological Scope, Data Provenance & Limitations

To ensure analytical rigor and transparency, the historical integration module (`integrar_fuentes.py`) adheres to strict methodological boundaries:

* **Data Provenance & Triangulation:** Official macroeconomic baselines are sourced from **INDEC** (National Consumer Price Index - IPC, Base Dec 2016) to deflate nominal values, while primary production costs (`hoja verde`) and value-chain spreads are triangulated from **Centro CEPA** sector reports (Jan 2025 & June 2026) and **INYM / Ministry of Deregulation** statistical releases.
* **Temporal Window Selection (2023–2026):** The integrated series intentionally focuses on the **October 2023 – November 2026** window to isolate the structural regime change triggered by **DNU 70/2023** (December 2023), capturing both the pre-deregulation baseline (regulated under Resolution 406/2023) and the subsequent free-market stabilization phase.
* **Methodological Approach:** Farm-to-retail participation percentages are calculated using standard industrial conversion ratios (~3.0 kg of green leaf per 1.0 kg of processed retail yerba mate), comparing deflated series in constant December 2023 currency (`ARS Dic-23 = 100`).

---

## 📉 Statistical Projections & Analytical Disclaimer

While this repository tracks historical trends and real-time retail dispersion, **it does not perform deterministic forecasting or speculative "futurology."**

* **Scenario Estimation:** Any forward-looking references or trend lines derived from the ETL pipeline represent statistical extrapolations based on recent monthly IPC inertia (e.g., ~1.9% monthly baseline) and current retail medians.
* **Disclaimer:** These figures are **analytical estimates** intended strictly for academic and exploratory monitoring. Real-world retail prices remain subject to exogenous macroeconomic shocks, seasonal harvest yields (Misiones/Corrientes), and commercial pricing strategies across retail chains.

---

## 🧠 Process Evaluation & Metacognition (Iterative Evolution)

Building this system followed an **iterative engineering cycle** rather than a linear workflow:

1. **From Static Requests to Headless Automation:** Initial prototypes assumed static JSON endpoints would suffice. Testing against live retail infrastructure forced a pivot to **Playwright** and DOM-level text filtering, reinforcing the importance of empirical validation over assumptions.
2. **From Local Scripts to Cloud CI/CD:** Moving from manual local execution (`src/`) to relative path resolution (`BASE_DIR`) and scheduled **GitHub Actions** transformed a one-off analysis into a self-updating monitoring system with real-time **Telegram** alerting.
3. **Future Roadmap & Continuous Improvement:**
   * *Multi-Retailer Expansion:* Incorporating additional supermarket chains (e.g., Carrefour, Coto) to eliminate single-retailer bias.
   * *Time-Series Modeling:* Once the automated cron job accumulates 6+ months of high-frequency daily/weekly scrapes, implementing formal **ARIMA / Prophet** models with confidence intervals to evaluate seasonal price elasticity.

---

## 🤝 Contributing & License

Contributions, issues, and feature requests are welcome. Feel free to check the issues page or submit a pull request.  
This project is licensed under the **MIT License**.
