\# Calibration Management and Production Compliance System



\## 1. Project Overview



The Calibration Management and Production Compliance System is a web-based application designed to manage industrial instruments, calibration schedules, calibration results, certificates, work orders, and production-use compliance.



The system helps organizations monitor calibration validity, identify overdue instruments, detect production usage outside valid calibration periods, and maintain traceable records of calibration and corrective actions.



\## 2. Technology Stack



\*\*Frontend\*\*

\- React.js

\- Vite

\- CSS



\*\*Backend\*\*

\- Python

\- Flask

\- MySQL Connector

\- python-dotenv



\*\*Database\*\*

\- MySQL 8.0



\*\*Data Generation and Validation\*\*

\- Python

\- NumPy

\- Pandas

\- CSV and JSON



\## 3. Main Modules



\- Asset Management

\- Instrument Type Management

\- Calibration Plan Management

\- Calibration Event Management

\- Certificate Management

\- Work Order Management

\- Production Use Management

\- Emergency Calibration Extensions

\- Impact Assessments

\- Compliance Monitoring

\- Audit Records



\## 4. Database Entities



The database includes:



1\. Instrument Type

2\. Asset

3\. Supplier

4\. Calibration Plan

5\. Calibration Event

6\. Certificate

7\. Work Order

8\. Production Use

9\. Alert

10\. Audit Record

11\. Emergency Extension

12\. Impact Assessment



Relationships are maintained using primary keys, foreign keys, and database constraints.



\## 5. Dataset Generation



The project includes a configurable, deterministic dataset generator.



Default configuration:



\- Random seed: `20261022`

\- Assets: 2,000

\- Calibration events: 5,000

\- Production-use events: 100,000



Generate the baseline dataset:



```bash

python backend/generate\_data.py

```



Generate a smaller test dataset:



```bash

python backend/generate\_data.py --assets 20 --calibrations 100 --production-uses 500 --output-dir data/generated\_test

```



The generator exports CSV and JSON datasets, anomaly fixtures, ground-truth labels, a source manifest, and a validation summary.



Ground-truth labels are maintained separately from the baseline input datasets.



\## 6. Installation and Setup



\### Prerequisites



\- Python 3

\- Node.js and npm

\- MySQL 8.0

\- Git



\### Backend Setup



Create and activate a virtual environment:



```bash

python -m venv venv

```



Windows PowerShell:



```powershell

.\\venv\\Scripts\\Activate.ps1

```



Install dependencies:



```bash

pip install -r backend/requirements.txt

```



\### Environment Configuration



Create a `.env` file in the project root:



```env

DB\_HOST=localhost

DB\_USER=root

DB\_PASSWORD=your\_mysql\_password

DB\_NAME=calibration\_management

```



Use `.env.example` as the configuration template. Never publish actual credentials.



\### Database Setup



Create the MySQL database:



```sql

CREATE DATABASE calibration\_management;

```



Execute the SQL files in the `database` directory in numerical order, from `01` through `07`.



\### Start the Backend



```powershell

cd backend

python app.py

```



Backend address:



`http://127.0.0.1:5000`



\### Frontend Setup



Open another terminal:



```powershell

cd frontend

npm install

npm run dev

```



Frontend address:



`http://localhost:5173`



\## 7. Compliance Monitoring



The compliance module checks:



\- Overdue calibration assets

\- Calibration due-date inconsistencies

\- Production-use violations

\- Missing calibration certificates

\- Certificate and asset mismatches

\- Failed calibrations without corrective actions

\- Failed calibrations without completed impact assessments



The system also evaluates emergency calibration extensions and their approval status.



\## 8. Testing and Validation



The project includes:



\- Dataset validation checks

\- Deterministic generation tests

\- Emergency extension integration tests

\- Impact assessment integration tests

\- Backend API checks

\- Frontend production build verification



Run the integration tests:



```powershell

python -m backend.test\_emergency\_extension

python -m backend.test\_impact\_assessment

```



Build the frontend:



```powershell

cd frontend

npm run build

```



\## 9. Project Structure



```text

Calibration Management and Production Compliance System/

│

├── backend/

│   ├── app.py

│   ├── db.py

│   ├── generate\_data.py

│   ├── import\_data.py

│   ├── requirements.txt

│   ├── services/

│   └── test files

│

├── database/

│   └── SQL schema and migration files

│

├── data/

│   └── generated/

│

├── docs/

│   └── data\_dictionary.md

│

├── frontend/

│   ├── src/

│   ├── package.json

│   └── vite.config.js

│

├── .env.example

├── .gitignore

└── README.md

```



\## 10. Assumptions and Limitations



\- Calibration compliance is evaluated using the configured calibration plans and recorded calibration events.

\- Emergency extensions are evaluated according to their approval status and validity period.

\- Impact assessments require documented quality decisions.

\- Certificate file references are maintained in the database; this does not necessarily mean the corresponding PDF files have been generated.

\- The project is a demonstration implementation and requires production security, deployment, and operational review before real industrial use.



\## 11. AI Assistance Disclosure



AI tools were used during development for coding assistance, debugging, documentation, and testing guidance. Generated suggestions were reviewed and tested as part of the implementation. The project developer remains responsible for the final implementation, technical decisions, and validation.



\## 12. License



Add the license applicable to this project before public distribution.



