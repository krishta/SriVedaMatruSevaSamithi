import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { NgoSettingsService } from '../../services/ngo-settings.service';

@Component({
  selector: 'svmss-admin-settings',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSnackBarModule,
  ],
  template: `
    <div class="page-container svmss-card" style="max-width: 1100px;">
      <h2 style="font-weight: 700;">NGO Settings</h2>

      <form [formGroup]="form" (ngSubmit)="save()" *ngIf="loaded" class="settings-grid">
        <mat-form-field class="span-2">
          <mat-label>NGO Name</mat-label>
          <input matInput formControlName="name" required />
        </mat-form-field>

        <mat-form-field class="span-2">
          <mat-label>Address</mat-label>
          <textarea matInput formControlName="address" required></textarea>
        </mat-form-field>

        <mat-form-field class="span-2">
          <mat-label>UPI ID</mat-label>
          <input matInput formControlName="upi_id" required />
        </mat-form-field>

        <mat-form-field>
          <mat-label>Bank Account Name</mat-label>
          <input matInput formControlName="account_name" />
        </mat-form-field>

        <mat-form-field>
          <mat-label>Bank Account Number</mat-label>
          <input matInput formControlName="account_no" />
        </mat-form-field>

        <mat-form-field>
          <mat-label>IFSC</mat-label>
          <input matInput formControlName="ifsc" />
        </mat-form-field>

        <mat-form-field>
          <mat-label>Bank Name</mat-label>
          <input matInput formControlName="bank" />
        </mat-form-field>

        <mat-form-field class="span-2">
          <mat-label>80G Registration No. (only fill in once registration is confirmed)</mat-label>
          <input matInput formControlName="reg_80g_number" />
        </mat-form-field>

        <div class="span-2">
          <button mat-raised-button color="primary" type="submit" [disabled]="saving">
            {{ saving ? 'Saving…' : 'Save Settings' }}
          </button>
        </div>
      </form>
    </div>
  `,
  styles: [
    `
      .settings-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
      }
      .settings-grid mat-form-field {
        width: 100%;
      }
      .settings-grid .span-2 {
        grid-column: 1 / -1;
      }
      @media (max-width: 600px) {
        .settings-grid {
          grid-template-columns: 1fr;
        }
      }
    `,
  ],
})
export class AdminSettingsComponent implements OnInit {
  private fb = inject(FormBuilder);
  loaded = false;
  saving = false;

  form = this.fb.group({
    name: ['', Validators.required],
    address: ['', Validators.required],
    upi_id: ['', Validators.required],
    account_name: [''],
    account_no: [''],
    ifsc: [''],
    bank: [''],
    reg_80g_number: [''],
  });

  constructor(private ngoSettingsService: NgoSettingsService, private snackBar: MatSnackBar) {}

  ngOnInit(): void {
    this.ngoSettingsService.getAdmin().subscribe((ngo) => {
      this.form.patchValue({
        name: ngo.name,
        address: ngo.address,
        upi_id: ngo.upi_id,
        account_name: ngo.bank_details.account_name ?? '',
        account_no: ngo.bank_details.account_no ?? '',
        ifsc: ngo.bank_details.ifsc ?? '',
        bank: ngo.bank_details.bank ?? '',
        reg_80g_number: ngo.reg_80g_number ?? '',
      });
      this.loaded = true;
    });
  }

  save(): void {
    if (this.form.invalid) return;
    const v = this.form.value;
    this.saving = true;
    this.ngoSettingsService
      .update({
        name: v.name!,
        address: v.address!,
        upi_id: v.upi_id!,
        bank_details: {
          account_name: v.account_name || undefined,
          account_no: v.account_no || undefined,
          ifsc: v.ifsc || undefined,
          bank: v.bank || undefined,
        },
        reg_80g_number: v.reg_80g_number || null,
      })
      .subscribe({
        next: () => {
          this.saving = false;
          this.snackBar.open('Settings saved', 'Dismiss');
        },
        error: () => {
          this.saving = false;
          this.snackBar.open('Failed to save settings', 'Dismiss');
        },
      });
  }
}