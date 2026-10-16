# SVMSS Frontend

Angular web application for donation entry, receipt lookup, and administration. In local development it calls the backend API at `http://localhost:8000/api`.

## Requirements

- Node.js version supported by the Angular CLI version in `package.json` (an active Node.js LTS release is recommended)
- npm
- The backend running locally; see [backend setup](../backend/README.md)

## Run locally

1. Start the backend in a separate terminal by following [backend setup](../backend/README.md). The API should be available at `http://localhost:8000`.
2. Open another terminal and change to the `frontend/` directory.
3. Install the exact dependency versions from the lockfile.

   ```bash
   npm ci
   ```

4. Start the Angular development server.

   ```bash
   npm start
   ```

5. Open <http://localhost:4200>. Leave both terminals running while using the application.

The root page opens the admin ledger (unauthenticated users are redirected to the admin login). The public receipt lookup is at `/receipt-lookup`; donation entry and administration are available under `/admin`. Use the admin username and password configured and seeded in the backend's `.env` file.

## Useful commands

Run these from `frontend/`:

```bash
npm start       # Start the development server at http://localhost:4200
npm run build   # Build the production application into dist/
```

The development API URL is configured in `src/environments/environment.ts`. If the backend runs at a different address or port, update `apiBaseUrl` there and ensure the backend's `CORS_ALLOWED_ORIGINS` includes the frontend origin.

## Troubleshooting

- **API requests fail:** confirm the backend is running at `http://localhost:8000` and that `http://localhost:4200` is allowed by the backend's CORS settings.
- **Port 4200 is already in use:** stop the other process using the port, or start Angular on another port with `npm start -- --port 4201`. If you change the frontend port, add its origin to the backend's `CORS_ALLOWED_ORIGINS`.
- **Dependency installation fails:** check your Node.js/npm versions against the requirements of the Angular CLI in `package.json`, then retry `npm ci`.
