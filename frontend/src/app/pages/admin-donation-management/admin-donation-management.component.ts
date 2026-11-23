import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'svmss-admin-donation-management',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  template: `
    <div class="page-container svmss-card" style="max-width: 1300px;">
      <h2>Donation Management</h2>
      <nav class="management-tabs" aria-label="Donation management">
        <a routerLink="./reasons" routerLinkActive="management-tabs__active">Donation Reasons</a>
        <a routerLink="./reports" routerLinkActive="management-tabs__active">Report Generation</a>
      </nav>
      <router-outlet />
    </div>
  `,
  styles: [
    `
      .management-tabs {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 0 0 20px;
        border-bottom: 1px solid var(--svmss-border);
      }

      .management-tabs a {
        padding: 10px 14px;
        color: var(--svmss-muted);
        text-decoration: none;
        border-bottom: 2px solid transparent;
      }

      .management-tabs .management-tabs__active {
        color: var(--svmss-brand-dark);
        border-bottom-color: var(--svmss-brand-dark);
        font-weight: 600;
      }
    `,
  ],
})
export class AdminDonationManagementComponent {}
