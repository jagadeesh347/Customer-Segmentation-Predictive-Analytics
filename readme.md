# Customer Segmentation and Predictive Analytics System

A Python-based web application that analyzes customer purchasing behavior, segments customers, and predicts customer churn using Machine Learning.

## Project Overview

The Customer Segmentation and Predictive Analytics System helps businesses understand customer behavior through RFM analysis, K-Means clustering, and Logistic Regression.

It provides an interactive Flask dashboard to visualize customer insights and support data-driven decisions.

## Features

- RFM Analysis (Recency, Frequency, Monetary)
- Customer Segmentation using K-Means Clustering
- Customer Churn Prediction using Logistic Regression
- Interactive Dashboard with charts
- Add Customer and Purchase Records
- Customer Segment and Churn Filters
- CSV and PDF Report Generation
- Customer Churn Prediction Page

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Flask | Web framework |
| MySQL | Database |
| Pandas | Data manipulation |
| NumPy | Numerical operations |
| Scikit-learn | Machine Learning |
| Matplotlib | Data visualization |
| HTML | Frontend |
| Joblib | Model storage |
| ReportLab | PDF generation |

## Machine Learning Algorithms

**1. RFM Analysis**

Analyzes customers based on:
- Recency
- Frequency
- Monetary Value

**2. K-Means Clustering**

Groups customers according to purchasing behavior.

**3. Logistic Regression**

Predicts potential customer churn.

## Project Structure

```text
Customer-Segmentation-Predictive-Analytics/
│
├── analysis/
│   ├── churn_prediction.py
│   ├── customer_segmentation.py
│   ├── rfm_analysis.py
│   ├── compare_segments.py
│   ├── visualize_segments.py
│   └── model and analysis files
│
├── app/
│   ├── dashboard.py
│   ├── db.py
│   ├── test_customers.py
│   └── templates/
│       ├── index.html
│       ├── predict.html
│       ├── add_customer.html
│       └── add_purchase.html
│
├── database/
│   └── .gitkeep
│
├── tests/
│   └── .gitkeep
│
├── requirements.txt
├── run.py
├── test_db.py
├── .gitignore
└── README.md
```

## Installation and Setup

**1. Clone the repository**

```bash
git clone https://github.com/jagadeesh347/Customer-Segmentation-Predictive-Analytics.git
```

**2. Navigate to the project**

```bash
cd Customer-Segmentation-Predictive-Analytics
```

**3. Create a virtual environment**

```bash
python -m venv .venv
```

**4. Activate the environment**

```powershell
.venv\Scripts\Activate.ps1
```

**5. Install dependencies**

```bash
pip install -r requirements.txt
```

**6. Configure MySQL**

Create the database:

```sql
CREATE DATABASE customer_segmentation;
```

Create a `.env` file in the project root:

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=customer_segmentation
```

Configure the required database tables according to the application code.

**7. Run the application**

```bash
python run.py
```

Open:

http://127.0.0.1:5000

## Applications

- Customer behavior analysis
- Customer segmentation
- Customer retention strategies
- Churn risk identification
- Business decision support

## Team Members

**Mohan Babu University**

Department of Computer Science and Engineering – Artificial Intelligence and Machine Learning

- K Jagadeeswar Sai
- K Yuga Shankar Reddy
- C Vidya Sagar
- B Vyshnavi
- M Meghana Reddy

## Future Enhancements

- Real-time customer analytics
- Advanced machine learning models
- Improved dashboard visualizations
- Automated customer retention recommendations

---

Developed as an academic project using Python, Flask, MySQL, and Machine Learning.