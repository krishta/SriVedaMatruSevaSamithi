import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { AuthService } from '../../services/auth.service';
import { NgoSettingsService, NgoSettingsPublic } from '../../services/ngo-settings.service';

@Component({
  selector: 'svmss-admin-login',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSnackBarModule,
  ],
  template: `
    <div class="login-split">
      <div class="login-split__brand">
        <img src="/assets/logo.png" alt="SVMSS logo" class="login-split__logo" />
        <h1 class="login-split__name">{{ ngo?.name || 'SVMSS' }}</h1>
      </div>
      <div class="login-split__form-side">
        <div class="login-split__card svmss-card">
          <h2>Admin Login</h2>
          <form [formGroup]="form" (ngSubmit)="submit()">
            <mat-form-field class="full-width">
              <mat-label>Username</mat-label>
              <input matInput formControlName="username" required />
            </mat-form-field>
            <mat-form-field class="full-width">
              <mat-label>Password</mat-label>
              <input matInput type="password" formControlName="password" required />
            </mat-form-field>
            <button
              mat-raised-button
              color="primary"
              class="full-width"
              type="submit"
              [disabled]="form.invalid || loading"
            >
              {{ loading ? 'Signing in…' : 'Sign in' }}
            </button>
          </form>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .login-split {
        display: flex;
        min-height: 100vh;
      }
      .login-split__brand {
        flex: 1 1 50%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 16px;
        background: var(--svmss-sidebar-bg);
        color: var(--svmss-sidebar-text-strong);
        padding: 24px;
        text-align: center;
      }
      .login-split__logo {
        width: min(260px, 55vw);
        height: min(260px, 55vw);
        object-fit: contain;
        border-radius: 20px;
        background: #fff;
      }
      .login-split__name {
        margin: 0;
        font-size: 22px;
        font-weight: 700;
      }
      .login-split__form-side {
        flex: 1 1 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 24px;
      }
      .login-split__card {
        width: 100%;
        max-width: 360px;
      }
      @media (max-width: 720px) {
        .login-split {
          flex-direction: column;
        }
        .login-split__brand {
          padding: 32px 16px;
        }
        .login-split__logo {
          width: min(200px, 48vw);
          height: min(200px, 48vw);
        }
      }
    `,
  ],
})
export class AdminLoginComponent implements OnInit {
  private fb = inject(FormBuilder);
  loading = false;
  ngo: NgoSettingsPublic | null = null;
  form = this.fb.group({
    username: ['', Validators.required],
    password: ['', Validators.required],
  });

  constructor(
    private auth: AuthService,
    private router: Router,
    private snackBar: MatSnackBar,
    private ngoSettingsService: NgoSettingsService
  ) {}

  ngOnInit(): void {
    this.ngoSettingsService.getPublic().subscribe({
      next: (ngo) => (this.ngo = ngo),
      error: () => {},
    });
  }

  submit(): void {
    if (this.form.invalid) return;
    this.loading = true;
    const { username, password } = this.form.value;
    this.auth.login(username!, password!).subscribe({
      next: () => {
        this.loading = false;
        this.router.navigate(['/admin/ledger']);
      },
      error: () => {
        this.loading = false;
        this.snackBar.open('Invalid credentials', 'Dismiss');
      },
    });
  }
}