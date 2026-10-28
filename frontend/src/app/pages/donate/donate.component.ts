import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatRadioModule } from '@angular/material/radio';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { DonationService } from '../../services/donation.service';
import { NgoSettingsService, NgoSettingsPublic } from '../../services/ngo-settings.service';

const REASONS = [
  { value: 'monthly_donation', label: 'Monthly Donation' },
  { value: 'birthday', label: 'Birthday' },
  { value: 'occasion_veda_sabha', label: 'Occasion / Veda Sabha' },
  { value: 'telangana_veda_sabhalu_2026', label: '2026 Telangana Veda Sabhalu' },
  { value: 'general_donation', label: 'General Donation' },
  { value: 'other', label: 'Other' },
];

@Component({
  selector: 'svmss-donate',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatRadioModule,
    MatButtonModule,
    MatCardModule,
    MatSnackBarModule,
  ],
  template: `
    <div class="page-container" [class.svmss-card]="embedded" [style.max-width]="embedded ? '1100px' : '720px'">
      <mat-card *ngIf="ngo && !embedded">
        <mat-card-header>
          <img
            mat-card-avatar
            src="/assets/logo.png"
            alt="{{ ngo.name }} logo"
            style="width: 40px; height: 40px; object-fit: contain;"
          />
          <mat-card-title>{{ ngo.name }}</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <p>{{ ngo.address }}</p>
          <p>UPI: {{ ngo.upi_id }}</p>
          <p>
            Bank: {{ ngo.bank_details.account_name }}, A/C {{ ngo.bank_details.account_no }},
            IFSC {{ ngo.bank_details.ifsc }}, {{ ngo.bank_details.bank }}
          </p>
        </mat-card-content>
      </mat-card>

      <h2 style="font-weight: 700;">{{ embedded ? 'One-off Receipt' : 'Make a Donation' }}</h2>
      <form [formGroup]="form" (ngSubmit)="submit()">
        <div class="form-grid">
          <mat-form-field>
            <mat-label>Name</mat-label>
            <input matInput formControlName="name" required />
          </mat-form-field>

          <mat-form-field>
            <mat-label>Phone (+91)</mat-label>
            <input matInput formControlName="phone" required maxlength="10" />
          </mat-form-field>

          <mat-form-field>
            <mat-label>Email (optional)</mat-label>
            <input matInput type="email" formControlName="email" />
          </mat-form-field>

          <mat-form-field>
            <mat-label>Amount (₹)</mat-label>
            <input matInput type="number" formControlName="amountRupees" required min="1" />
          </mat-form-field>

          <mat-form-field class="span-2">
            <mat-label>Address (optional)</mat-label>
            <textarea matInput formControlName="address"></textarea>
          </mat-form-field>

          <mat-form-field>
            <mat-label>Reason</mat-label>
            <mat-select formControlName="reason" required>
              <mat-option *ngFor="let r of reasons" [value]="r.value">{{ r.label }}</mat-option>
            </mat-select>
          </mat-form-field>

          <mat-form-field *ngIf="form.value.reason === 'other'">
            <mat-label>Please specify</mat-label>
            <input matInput formControlName="reasonOther" />
          </mat-form-field>

          <div class="span-2">
            <label class="block-label">Payment Mode</label>
            <mat-radio-group formControlName="mode">
              <mat-radio-button value="upi">UPI</mat-radio-button>
              <mat-radio-button value="bank_transfer">Bank Transfer</mat-radio-button>
              <mat-radio-button value="cheque_dd">Cheque / DD</mat-radio-button>
            </mat-radio-group>
          </div>

          <mat-form-field *ngIf="form.value.mode === 'upi'" class="span-2">
            <mat-label>UPI Transaction ID</mat-label>
            <input matInput formControlName="upiTxnId" required />
          </mat-form-field>

          <ng-container *ngIf="form.value.mode === 'bank_transfer' || form.value.mode === 'cheque_dd'">
            <mat-form-field>
              <mat-label>Bank Name</mat-label>
              <input matInput formControlName="bankName" required />
            </mat-form-field>
            <mat-form-field>
              <mat-label>Branch Name</mat-label>
              <input matInput formControlName="branchName" required />
            </mat-form-field>
            <mat-form-field class="span-2">
              <mat-label>{{ form.value.mode === 'bank_transfer' ? 'Date of Transfer' : 'Date of Cheque / DD' }}</mat-label>
              <input matInput type="date" formControlName="transactionDate" required />
            </mat-form-field>
          </ng-container>

          <div class="span-2 file-field">
            <label class="block-label">Payment screenshot (image or PDF, max 5MB)</label>
            <input type="file" accept="image/*,.pdf" (change)="onFileSelected($event)" required />
          </div>

          <div class="span-2">
            <button mat-raised-button color="primary" type="submit" [disabled]="form.invalid || submitting">
              {{ submitting ? 'Submitting…' : 'Submit Donation' }}
            </button>
          </div>
        </div>
      </form>
    </div>
  `,
  styles: [
    `
      .form-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
      }
      .form-grid mat-form-field {
        width: 100%;
      }
      .form-grid .span-2 {
        grid-column: 1 / -1;
      }
      .block-label {
        display: block;
        margin-bottom: 8px;
        font-weight: 500;
      }
      .file-field {
        margin-bottom: 16px;
      }
      .file-field input[type='file'] {
        display: block;
        margin-top: 8px;
      }
      @media (max-width: 600px) {
        .form-grid {
          grid-template-columns: 1fr;
        }
      }
    `,
  ],
})
export class DonateComponent implements OnInit {
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  reasons = REASONS;
  ngo: NgoSettingsPublic | null = null;
  submitting = false;
  embedded = this.route.snapshot.data['embedded'] === true;
  private selectedFile: File | null = null;

  form = this.fb.group({
    name: ['', Validators.required],
    phone: ['', [Validators.required, Validators.pattern(/^\d{10}$/)]],
    email: [''],
    address: [''],
    amountRupees: [null as number | null, [Validators.required, Validators.min(1)]],
    reason: ['', Validators.required],
    reasonOther: [''],
    mode: ['upi', Validators.required],
    upiTxnId: ['', Validators.required],
    bankName: [''],
    branchName: [''],
    transactionDate: [''],
  });

  constructor(
    private donationService: DonationService,
    private ngoSettingsService: NgoSettingsService,
    private router: Router,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.ngoSettingsService.getPublic().subscribe({
      next: (ngo) => (this.ngo = ngo),
      error: () => this.snackBar.open('Could not load NGO details', 'Dismiss'),
    });

    this.form.get('mode')!.valueChanges.subscribe((mode) => this.applyModeValidators(mode));
    this.applyModeValidators(this.form.value.mode ?? 'upi');
  }

  private applyModeValidators(mode: string | null | undefined): void {
    const upiTxnId = this.form.get('upiTxnId')!;
    const bankName = this.form.get('bankName')!;
    const branchName = this.form.get('branchName')!;
    const transactionDate = this.form.get('transactionDate')!;

    if (mode === 'upi') {
      upiTxnId.setValidators(Validators.required);
      bankName.clearValidators();
      branchName.clearValidators();
      transactionDate.clearValidators();
    } else if (mode === 'bank_transfer' || mode === 'cheque_dd') {
      upiTxnId.clearValidators();
      bankName.setValidators(Validators.required);
      branchName.setValidators(Validators.required);
      transactionDate.setValidators(Validators.required);
    }
    [upiTxnId, bankName, branchName, transactionDate].forEach((c) => c.updateValueAndValidity());
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    if (file && file.size > 5 * 1024 * 1024) {
      this.snackBar.open('File exceeds 5MB limit', 'Dismiss');
      this.selectedFile = null;
      return;
    }
    this.selectedFile = file;
  }

  submit(): void {
    if (this.form.invalid || !this.selectedFile) {
      this.snackBar.open('Please complete all required fields and attach a screenshot', 'Dismiss');
      return;
    }
    const v = this.form.value;
    const formData = new FormData();
    formData.append('name', v.name!);
    formData.append('phone', v.phone!);
    if (v.email) formData.append('email', v.email);
    if (v.address) formData.append('address', v.address);
    formData.append('amount_paise', String(Math.round((v.amountRupees ?? 0) * 100)));
    formData.append('reason', v.reason!);
    if (v.reason === 'other' && v.reasonOther) formData.append('reason_other', v.reasonOther);
    formData.append('mode', v.mode!);
    if (v.mode === 'upi' && v.upiTxnId) formData.append('upi_txn_id', v.upiTxnId);
    if (v.mode === 'bank_transfer' || v.mode === 'cheque_dd') {
      if (v.bankName) formData.append('bank_name', v.bankName);
      if (v.branchName) formData.append('branch_name', v.branchName);
      if (v.transactionDate) formData.append('transaction_date', v.transactionDate);
    }
    formData.append('screenshot', this.selectedFile);

    this.submitting = true;
    this.donationService.submit(formData).subscribe({
      next: (res) => {
        this.submitting = false;
        this.router.navigate(['/donate/confirmation'], {
          state: { result: res, donorName: v.name },
        });
      },
      error: (err) => {
        this.submitting = false;
        const msg = err?.error?.error?.message ?? 'Submission failed — please check the form';
        this.snackBar.open(typeof msg === 'string' ? msg : JSON.stringify(msg), 'Dismiss');
      },
    });
  }
}