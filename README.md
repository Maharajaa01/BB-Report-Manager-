### Bb Report Manager

This App Is Designed For Report Manager 

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app bb_report_manager
```

### Manager Charts dashboard (`/bb-reports`)

A Vue 3 + TypeScript app (Vite) in `frontend/`, served by Frappe at `/bb-reports`.

- `frontend/` builds into `bb_report_manager/public/reports/`, and `frontend/scripts/make-page.mjs`
  writes `bb_report_manager/www/bb-reports.html`. Both are build output (gitignored).
  `bench build --app bb_report_manager` runs the whole build.
- `bb_report_manager/www/bb_reports.py` sends guests to login and needs the **BB Report Viewer**
  (or System Manager) role.
- Data APIs:
  - `api/tuition.py` reads Student, Fee and Complaint data on the tuition site.
  - `api/dashboard.py` is the only API the browser calls. It forwards tuition-site reports over
    REST using the key and secret in **BB Report Settings**.
  - The app is installed on both sites.

```bash
cd apps/bb_report_manager/frontend
npm ci
npm run dev        # http://localhost:8084/bb-reports (proxies /api to the local bench)
npm test           # vitest
npm run typecheck  # vue-tsc
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/bb_report_manager
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
