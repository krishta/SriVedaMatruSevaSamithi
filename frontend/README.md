# SVMSS Frontend

Angular web application for donation entry, receipt lookup, and administration. In local development it calls the backend API at `http://192.168.1.101:8000/api`, allowing clients on the same network to share the Mac mini's backend and database.

## Requirements

- Node.js version supported by the Angular CLI version in `package.json` (an active Node.js LTS release is recommended)
- npm
- The backend running locally; see [backend setup](../backend/README.md)

## Run locally

1. Start the backend in a separate terminal by following [backend setup](../backend/README.md). Bind it to `0.0.0.0` so it is reachable on the network.
2. Open another terminal and change to the `frontend/` directory.
3. Install the exact dependency versions from the lockfile.

   ```bash
   npm ci
   ```

4. Start the Angular development server.

   ```bash
   npm start -- --host 0.0.0.0
   ```

5. On the Mac mini, open <http://localhost:4200>. From another device on the same network, open <http://192.168.1.101:4200>. Leave both terminals running while using the application.

The root page opens the admin ledger (unauthenticated users are redirected to the admin login). The public receipt lookup is at `/receipt-lookup`; donation entry and administration are available under `/admin`. Use the admin username and password configured and seeded in the backend's `.env` file. In the Donation Ledger, **Regenerate receipt** rebuilds and downloads an active receipt without changing its receipt number; voided receipts must be reissued instead.

**Donation Management** in the left navigation contains **Donation Reasons** for maintaining active/archived reasons and **Report Generation** for creating configurable Excel workbooks. Reports support donation-by-reason/date, monthly donations by donor, donor totals, payment reconciliation, and the receipt register. Date filters use the donation received/recorded date; both that date and the receipt issue date are included as required columns.

## Useful commands

Run these from `frontend/`:

```bash
npm start -- --host 0.0.0.0  # Share the development server with devices on the LAN
npm run build   # Build the production application into dist/
```

The development API URL is configured in `src/environments/environment.ts`. If the Mac mini's network IP changes, update `apiBaseUrl` there and update `CORS_ALLOWED_ORIGINS` in the backend `.env` to include both frontend origins.

## Troubleshooting

- **API requests fail from another device:** confirm the backend is bound to `0.0.0.0`, the device can access `http://192.168.1.101:8000/api/health`, and both frontend origins are allowed by the backend's CORS settings. `localhost` on another device refers to that device, not the Mac mini.
- **Port 4200 is already in use:** stop the other process using the port, or start Angular on another port with `npm start -- --port 4201`. If you change the frontend port, add its origin to the backend's `CORS_ALLOWED_ORIGINS`.
- **Dependency installation fails:** check your Node.js/npm versions against the requirements of the Angular CLI in `package.json`, then retry `npm ci`.
