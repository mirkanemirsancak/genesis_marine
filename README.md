# Genesis Marine

Genesis Marine is an open-access marine intelligence workspace for environmental analysis, forecasting, anomaly detection, and dataset exploration.

The current public release is designed for researchers, environmental monitoring teams, and scientific users who want a cleaner analytical surface on top of marine data products. It combines regional filtering, statistical analysis, AI-assisted forecasting, anomaly screening, and local dataset management in a single Streamlit application.

## Product Overview

Genesis Marine currently provides:

- Spatial marine analysis with shared region, time, and depth filters
- Statistical summaries, climatology, annual variability, and trophic-state views
- AI-assisted forecasting for environmental time series
- Anomaly detection for unusual marine observations
- Dataset catalog visibility
- Local storage management for downloaded NetCDF files
- Export of local NetCDF cache files

The current analytical implementation is focused on East Black Sea environmental workflows, but the product structure is being prepared for broader global marine coverage in future iterations.

## Open Access and Enterprise Development

The current workspace is publicly accessible and free to use.

If you need additional capabilities, custom integrations, broader geographic coverage, organization-specific workflows, or a tailored enterprise version of the platform, please contact **Mirkan Emir Sancak** directly. Additional product development can be delivered as a custom enterprise engagement.

## Repository Structure

```text
analysis/        Statistical and eutrophication analysis utilities
assets/          Shared design assets and branding
components/      Dash UI components from the earlier app structure
data/            Data access, caching, and dataset management
ml/              Forecasting, feature engineering, and anomaly detection
pages/           Dash pages from the earlier app structure
scheduler/       Background refresh jobs
streamlit_ui/    Current public Streamlit interface
utils/           Shared helpers
app.py           Original Dash entry point
streamlit_ui/app.py  Current Streamlit entry point
```

## Installation

Requirements:

- Python 3.10+ recommended
- A Copernicus Marine account if you want to fetch CMEMS data

Clone the repository and install dependencies:

```bash
git clone https://github.com/mirkanemirsancak/genesis_marine.git
cd genesis_marine
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root:

```env
COPERNICUSMARINE_SERVICE_USERNAME=your_username_here
COPERNICUSMARINE_SERVICE_PASSWORD=your_password_here
```

An example template is already included in `.env.example`.

## Run the Streamlit App

The current public interface runs from the Streamlit entry point:

```bash
source venv/bin/activate
python -m streamlit run streamlit_ui/app.py
```

Then open:

- [http://localhost:8501](http://localhost:8501)

## Using the Application

The application has two top-level sections:

1. `Analysis Workspace`
   Use this page to run actual scientific workflows.
2. `Platform Overview`
   Use this page to understand the product, technical capabilities, and case study framing.

Inside the analysis workspace:

1. Choose a workspace module.
2. Set data filters in the left sidebar.
3. Click `Run Analysis`.

Available modules:

- Spatial Map
- Statistics
- AI Forecast
- Anomaly Detection
- Data Catalog
- Local Storage

## Deployment

### Streamlit Community Cloud

1. Push this repository to GitHub.
2. Open [Streamlit Community Cloud](https://streamlit.io/cloud).
3. Create a new app.
4. Select this repository.
5. Set the main file path to:

```text
streamlit_ui/app.py
```

6. Add the following secrets or environment variables:

```env
COPERNICUSMARINE_SERVICE_USERNAME=your_username_here
COPERNICUSMARINE_SERVICE_PASSWORD=your_password_here
```

7. Deploy.

### Local or Server Deployment

For a simple server deployment:

```bash
source venv/bin/activate
python -m streamlit run streamlit_ui/app.py --server.port 8501 --server.address 0.0.0.0
```

## Notes

- This repository intentionally does not include local cache files, logs, or virtual environment files.
- Some legacy Dash files are still present because they remain part of the broader codebase history.
- The active public product surface is the Streamlit app in `streamlit_ui/app.py`.

## Contact

For collaboration, research adaptation, or enterprise-grade custom development, please contact **Mirkan Emir Sancak**.
