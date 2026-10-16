import { Routes } from '@angular/router';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'admin/ledger', pathMatch: 'full' },
  {
    path: 'donate/confirmation',
    loadComponent: () =>
      import('./pages/confirmation/confirmation.component').then((m) => m.ConfirmationComponent),
  },
  {
    path: 'receipt-lookup',
    loadComponent: () =>
      import('./pages/receipt-lookup/receipt-lookup.component').then(
        (m) => m.ReceiptLookupComponent
      ),
  },
  {
    path: 'admin/login',
    loadComponent: () =>
      import('./pages/admin-login/admin-login.component').then((m) => m.AdminLoginComponent),
  },
  {
    path: 'admin',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/admin-shell/admin-shell.component').then((m) => m.AdminShellComponent),
    children: [
      { path: '', redirectTo: 'ledger', pathMatch: 'full' },
      {
        path: 'ledger',
        loadComponent: () =>
          import('./pages/admin-ledger/admin-ledger.component').then(
            (m) => m.AdminLedgerComponent
          ),
      },
      {
        path: 'donors',
        loadComponent: () =>
          import('./pages/admin-donors/admin-donors.component').then(
            (m) => m.AdminDonorsComponent
          ),
      },
      {
        path: 'donors/:id',
        loadComponent: () =>
          import('./pages/admin-donor/admin-donor.component').then((m) => m.AdminDonorComponent),
      },
      {
        path: 'batch-receipts',
        loadComponent: () =>
          import('./pages/admin-batch-receipts/admin-batch-receipts.component').then(
            (m) => m.AdminBatchReceiptsComponent
          ),
      },
      {
        path: 'settings',
        loadComponent: () =>
          import('./pages/admin-settings/admin-settings.component').then(
            (m) => m.AdminSettingsComponent
          ),
      },
      {
        path: 'donate',
        data: { embedded: true },
        loadComponent: () =>
          import('./pages/donate/donate.component').then((m) => m.DonateComponent),
      },
      {
        path: 'meetings',
        loadComponent: () =>
          import('./pages/admin-meetings/admin-meetings.component').then(
            (m) => m.AdminMeetingsComponent
          ),
      },
    ],
  },
  { path: '**', redirectTo: 'admin/login' },
];