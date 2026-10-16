import { Component, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AuthService } from '../../services/auth.service';

interface AdminNavItem {
  path: string;
  label: string;
  icon: string;
}

/**
 * Shared layout for every authenticated /admin/* route: a collapsible left-hand
 * navigation rail (icon-only by default, expands on hover or when pinned open)
 * instead of the previous top tab bar, plus a user/logout footer.
 */
@Component({
  selector: 'svmss-admin-shell',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive, RouterOutlet],
  template: `
    <div class="admin-shell" [class.admin-shell--open]="expanded()">
      <aside class="admin-shell__rail" (mouseenter)="onRailEnter()" (mouseleave)="onRailLeave()">
        <div class="admin-shell__brand-row">
          <button
            type="button"
            class="admin-shell__icon-btn"
            aria-label="Toggle navigation"
            (click)="togglePin()"
          >
            <span class="material-symbols-outlined">{{ pinned() ? 'close' : 'menu' }}</span>
          </button>
          <img src="/assets/logo.png" alt="SVMSS logo" class="admin-shell__logo" />
          <span class="admin-shell__brand-text">SVMSS Admin</span>
        </div>

        <nav class="admin-shell__nav">
          @for (item of navItems; track item.path) {
            <a
              class="admin-shell__nav-item"
              [routerLink]="item.path"
              routerLinkActive="admin-shell__nav-item--active"
              [attr.title]="!expanded() ? item.label : null"
            >
              <span class="material-symbols-outlined">{{ item.icon }}</span>
              <span class="admin-shell__nav-label">{{ item.label }}</span>
            </a>
          }
        </nav>

        <div class="admin-shell__footer">
          <div class="admin-shell__user" [attr.title]="username()">
            <span class="material-symbols-outlined admin-shell__user-icon">person</span>
            <span class="admin-shell__nav-label admin-shell__user-name">{{ username() || 'Admin' }}</span>
          </div>
          <button type="button" class="admin-shell__nav-item admin-shell__logout" (click)="logout()">
            <span class="material-symbols-outlined">logout</span>
            <span class="admin-shell__nav-label">Logout</span>
          </button>
        </div>
      </aside>

      <main class="admin-shell__content svmss-page">
        <router-outlet />
      </main>
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
      }
      .admin-shell {
        --_rail: 68px;
        --_panel: 232px;
        display: flex;
        min-height: 100vh;
      }
      .admin-shell__rail {
        position: sticky;
        top: 0;
        align-self: flex-start;
        height: 100vh;
        width: var(--_rail);
        flex: 0 0 var(--_rail);
        background: var(--svmss-sidebar-bg);
        color: var(--svmss-sidebar-text);
        border-right: 1px solid var(--svmss-sidebar-border);
        display: flex;
        flex-direction: column;
        overflow: hidden;
        transition: width 0.18s ease, flex-basis 0.18s ease;
        z-index: 10;
      }
      .admin-shell--open .admin-shell__rail {
        width: var(--_panel);
        flex-basis: var(--_panel);
      }
      .admin-shell__brand-row {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
        padding: 10px 8px;
        border-bottom: 1px solid var(--svmss-sidebar-border);
      }
      .admin-shell--open .admin-shell__brand-row {
        flex-direction: row;
        gap: 10px;
        padding: 12px;
        min-height: 60px;
      }
      .admin-shell__icon-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        flex: 0 0 auto;
        border: none;
        border-radius: var(--svmss-radius-md);
        background: transparent;
        color: var(--svmss-sidebar-text-strong);
        cursor: pointer;
      }
      .admin-shell__icon-btn:hover {
        background: var(--svmss-sidebar-hover);
      }
      .admin-shell__logo {
        width: 28px;
        height: 28px;
        object-fit: contain;
        border-radius: 4px;
        background: #fff;
        flex: 0 0 auto;
      }
      .admin-shell__brand-text {
        color: var(--svmss-sidebar-text-strong);
        font-weight: 600;
        font-size: 14px;
        white-space: nowrap;
        opacity: 0;
        transition: opacity 0.15s ease;
      }
      .admin-shell--open .admin-shell__brand-text {
        opacity: 1;
      }
      .admin-shell__nav {
        flex: 1 1 auto;
        overflow-y: auto;
        overflow-x: hidden;
        padding: 10px 8px;
        display: flex;
        flex-direction: column;
        gap: 2px;
      }
      .admin-shell__nav-item {
        display: flex;
        align-items: center;
        gap: 12px;
        width: 100%;
        padding: 10px 12px;
        border: none;
        background: transparent;
        color: var(--svmss-sidebar-text);
        border-radius: var(--svmss-radius-md);
        cursor: pointer;
        text-decoration: none;
        font-size: 13.5px;
        font-family: inherit;
        font-weight: 500;
        white-space: nowrap;
        transition: background 0.12s ease, color 0.12s ease;
      }
      .admin-shell__nav-item:hover {
        background: var(--svmss-sidebar-hover);
        color: var(--svmss-sidebar-text-strong);
      }
      .admin-shell__nav-item--active {
        background: var(--svmss-sidebar-active);
        color: var(--svmss-sidebar-text-strong);
        box-shadow: inset 0 0 0 1px var(--svmss-sidebar-border);
      }
      .admin-shell:not(.admin-shell--open) .admin-shell__nav-item {
        justify-content: center;
      }
      .admin-shell__nav-label {
        opacity: 0;
        transition: opacity 0.15s ease;
      }
      .admin-shell--open .admin-shell__nav-label {
        opacity: 1;
      }
      .admin-shell:not(.admin-shell--open) .admin-shell__nav-label {
        width: 0;
        overflow: hidden;
      }
      .admin-shell__footer {
        border-top: 1px solid var(--svmss-sidebar-border);
        padding: 10px 8px;
      }
      .admin-shell__user {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 12px;
        color: var(--svmss-sidebar-text-strong);
      }
      .admin-shell:not(.admin-shell--open) .admin-shell__user {
        justify-content: center;
      }
      .admin-shell__user-name {
        font-size: 13px;
        font-weight: 600;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .admin-shell__content {
        flex: 1 1 auto;
        min-width: 0;
      }
      @media (max-width: 720px) {
        .admin-shell__brand-text {
          display: none;
        }
      }
    `,
  ],
})
export class AdminShellComponent {
  navItems: AdminNavItem[] = [
    { path: '/admin/ledger', label: 'Ledger', icon: 'receipt_long' },
    { path: '/admin/donors', label: 'Donors', icon: 'group' },
    { path: '/admin/batch-receipts', label: 'Batch Receipts', icon: 'playlist_add_check' },
    { path: '/admin/donate', label: 'One-off Receipt', icon: 'add_card' },
    { path: '/admin/meetings', label: 'Monthly Meetings', icon: 'event_note' },
    { path: '/admin/settings', label: 'Settings', icon: 'settings' },
  ];

  private pinnedSignal = signal(false);
  private hoverSignal = signal(false);
  expanded = computed(() => this.pinnedSignal() || this.hoverSignal());
  pinned = this.pinnedSignal.asReadonly();
  username = computed(() => this.auth.username);

  constructor(private auth: AuthService, private router: Router) {}

  togglePin(): void {
    this.pinnedSignal.update((v) => !v);
  }

  onRailEnter(): void {
    this.hoverSignal.set(true);
  }

  onRailLeave(): void {
    this.hoverSignal.set(false);
  }

  logout(): void {
    this.auth.logout();
    this.router.navigate(['/admin/login']);
  }
}