import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormArray, FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { DonorService } from '../../services/donor.service';
import { BatchReceiptResponse, DonationService } from '../../services/donation.service';
import { toAbsoluteApiUrl } from '../../services/ngo-settings.service';
import { InrCurrencyPipe } from '../../pipes/inr-currency.pipe';

const MONTHS = [
  { value: 1, label: 'January' },
  { value: 2, label: 'February' },
  { value: 3, label: 'March' },
  { value: 4, label: 'April' },
  { value: 5, label: 'May' },
  { value: 6, label: 'June' },
  { value: 7, label: 'July' },
  { value: 8, label: 'August' },
  { value: 9, label: 'September' },
  { value: 10, label: 'October' },
  { value: 11, label: 'November' },
  { value: 12, label: 'December' },
];

@Component({
  selector: 'svmss-admin-batch-receipts',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatTableModule,
    MatCheckboxModule,
    MatSelectModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatCardModule,
    MatSnackBarModule,
    InrCurrencyPipe,
  ],
  template: `
    <div class="page-container svmss-card" style="max-width: 1300px;">
      <h2>Generate Monthly Receipts</h2>

      <mat-card style="margin-bottom: 16px;">
        <mat-card-content>
          <div class="period-row">
            <mat-form-field>
              <mat-label>Year</mat-label>
              <mat-select [formControl]="yearControl">
                <mat-option *ngFor="let y of years" [value]="y">{{ y }}</mat-option>
              </mat-select>
            </mat-form-field>
            <mat-form-field>
              <mat-label>Month</mat-label>
              <mat-select [formControl]="monthControl">
                <mat-option *ngFor="let m of months" [value]="m.value">{{ m.label }}</mat-option>
              </mat-select>
            </mat-form-field>
            <button mat-raised-button color="primary" (click)="loadDonors()" [disabled]="loading">
              {{ loading ? 'Loading…' : 'Load donor list' }}
            </button>
          </div>
          <p class="hint">
            Receipts are numbered against the selected month
            (<strong>SVMSS/{{ yearControl.value }}/{{ paddedMonth }}/…</strong>).
          </p>
        </mat-card-content>
      </mat-card>

      <form [formGroup]="form" (ngSubmit)="submit()" *ngIf="rows.length">
        <div class="toolbar">
          <button mat-raised-button type="button" (click)="toggleAll(true)">Select all</button>
          <button mat-raised-button type="button" (click)="toggleAll(false)">Clear all</button>
          <span class="spacer"></span>
          <strong>{{ selectedCount }} selected · Total {{ selectedTotalPaise | inrCurrency }}</strong>
        </div>

        <div class="svmss-table-scroll">
        <table class="batch-table">
          <thead>
            <tr>
              <th style="width:40px;"></th>
              <th>Donor</th>
              <th style="width:130px;">Amount (₹)</th>
              <th style="width:170px;">Payment Mode</th>
              <th>Payment details</th>
              <th style="width:190px;">Screenshot (optional)</th>
            </tr>
          </thead>
          <tbody formArrayName="rows">
            <tr *ngFor="let row of rows.controls; let i = index" [formGroupName]="i">
              <td><mat-checkbox formControlName="selected"></mat-checkbox></td>
              <td>
                <div>{{ row.value.donorName }}</div>
                <small>{{ row.value.donorPhone }}</small>
              </td>
              <td>
                <mat-form-field class="dense">
                  <input matInput type="number" min="1" formControlName="amountRupees" />
                </mat-form-field>
              </td>
              <td>
                <mat-form-field class="dense">
                  <mat-select formControlName="mode">
                    <mat-option value="upi">UPI</mat-option>
                    <mat-option value="bank_transfer">Bank Transfer</mat-option>
                    <mat-option value="cheque_dd">Cheque / DD</mat-option>
                  </mat-select>
                </mat-form-field>
              </td>
              <td>
                <ng-container *ngIf="row.value.mode === 'upi'">
                  <mat-form-field class="dense">
                    <mat-label>UPI Transaction ID</mat-label>
                    <input matInput formControlName="upiTxnId" />
                  </mat-form-field>
                </ng-container>
                <ng-container *ngIf="row.value.mode === 'bank_transfer' || row.value.mode === 'cheque_dd'">
                  <div class="bank-fields">
                    <mat-form-field class="dense">
                      <mat-label>Bank Name</mat-label>
                      <input matInput formControlName="bankName" />
                    </mat-form-field>
                    <mat-form-field class="dense">
                      <mat-label>Branch Name</mat-label>
                      <input matInput formControlName="branchName" />
                    </mat-form-field>
                    <mat-form-field class="dense">
                      <mat-label>{{ row.value.mode === 'bank_transfer' ? 'Date of Transfer' : 'Date of Cheque / DD' }}</mat-label>
                      <input matInput type="date" formControlName="transactionDate" />
                    </mat-form-field>
                  </div>
                </ng-container>
              </td>
              <td>
                <input type="file" accept="image/*,.pdf" (change)="onFileSelected($event, i)" />
              </td>
            </tr>
          </tbody>
        </table>
        </div>

        <button mat-raised-button color="primary" type="submit" [disabled]="submitting || !selectedCount">
          {{ submitting ? 'Generating…' : 'Generate ' + selectedCount + ' receipt(s)' }}
        </button>
      </form>

      <mat-card *ngIf="result" style="margin-top: 20px;">
        <mat-card-content>
          <h3>Result for {{ result.period }}</h3>
          <p>{{ result.generated }} generated · {{ result.failed }} failed</p>
          <ul>
            <li *ngFor="let r of result.results">
              <ng-container *ngIf="r.status === 'generated'">
                {{ r.donor_name }} — {{ r.receipt_no }}
                <a [href]="pdfUrl(r.pdf_url)" target="_blank">Download</a>
                <span *ngIf="r.email_sent"> · emailed</span>
              </ng-container>
              <ng-container *ngIf="r.status === 'failed'">
                <span class="failed">{{ r.donor_name }} — failed: {{ r.error }}</span>
              </ng-container>
            </li>
          </ul>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [
    `
      .admin-nav {
        display: flex;
        gap: 12px;
        margin-bottom: 12px;
      }
      .period-row {
        display: flex;
        gap: 16px;
        align-items: center;
        flex-wrap: wrap;
      }
      .hint {
        color: #555;
        font-size: 0.9em;
      }
      .toolbar {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
      }
      .toolbar .spacer {
        flex: 1;
      }
      .batch-table {
        width: 100%;
        min-width: 900px;
        border-collapse: collapse;
        margin-bottom: 16px;
        background: var(--svmss-surface);
      }
      .batch-table thead tr {
        background: var(--svmss-bg);
      }
      .batch-table th {
        font-weight: 600;
        font-size: 12px;
        color: var(--svmss-muted);
        text-transform: uppercase;
        letter-spacing: 0.02em;
      }
      .batch-table th,
      .batch-table td {
        border-bottom: 1px solid var(--svmss-border);
        padding: 6px 8px;
        text-align: left;
        vertical-align: top;
      }
      .dense {
        width: 100%;
        font-size: 0.9em;
      }
      .bank-fields {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 0 8px;
      }
      .failed {
        color: #b00020;
      }
    `,
  ],
})
export class AdminBatchReceiptsComponent implements OnInit {
  private fb = inject(FormBuilder);
  months = MONTHS;
  years: number[] = [];
  loading = false;
  submitting = false;
  result: BatchReceiptResponse | null = null;
  private files = new Map<number, File>();

  yearControl = this.fb.control(new Date().getFullYear(), { nonNullable: true });
  monthControl = this.fb.control(new Date().getMonth() + 1, { nonNullable: true });
  form = this.fb.group({ rows: this.fb.array([] as FormGroup[]) });

  constructor(
    private donorService: DonorService,
    private donationService: DonationService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    const thisYear = new Date().getFullYear();
    this.years = [thisYear + 1, thisYear, thisYear - 1, thisYear - 2];
    this.loadDonors();
  }

  get rows(): FormArray<FormGroup> {
    return this.form.get('rows') as FormArray<FormGroup>;
  }

  get paddedMonth(): string {
    return String(this.monthControl.value).padStart(2, '0');
  }

  get selectedCount(): number {
    return this.rows.controls.filter((c) => c.value.selected).length;
  }

  get selectedTotalPaise(): number {
    return this.rows.controls
      .filter((c) => c.value.selected)
      .reduce((sum, c) => sum + Math.round((c.value.amountRupees ?? 0) * 100), 0);
  }

  loadDonors(): void {
    this.loading = true;
    this.result = null;
    this.files.clear();
    this.donorService.list({ page: 1, size: 500 }).subscribe({
      next: (res) => {
        this.rows.clear();
        res.items.forEach((d) =>
          this.rows.push(
            this.fb.group({
              selected: [false],
              donorId: [d.id],
              donorName: [d.name],
              donorPhone: [d.phone],
              amountRupees: [null as number | null],
              mode: ['upi'],
              upiTxnId: [''],
              bankName: [''],
              branchName: [''],
              transactionDate: [''],
            })
          )
        );
        this.loading = false;
        if (!res.items.length) {
          this.snackBar.open('No donors in the master list yet — add donors first', 'Dismiss');
        }
      },
      error: () => {
        this.loading = false;
        this.snackBar.open('Could not load the donor list', 'Dismiss');
      },
    });
  }

  toggleAll(selected: boolean): void {
    this.rows.controls.forEach((c) => c.patchValue({ selected }));
  }

  onFileSelected(event: Event, index: number): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    const donorId = this.rows.at(index).value.donorId as number;
    if (!file) {
      this.files.delete(donorId);
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      this.snackBar.open('File exceeds 5MB limit', 'Dismiss');
      input.value = '';
      this.files.delete(donorId);
      return;
    }
    this.files.set(donorId, file);
  }

  submit(): void {
    const selected = this.rows.controls.filter((c) => c.value.selected);
    if (!selected.length) return;

    const items: Record<string, unknown>[] = [];
    for (const control of selected) {
      const v = control.value;
      const amountPaise = Math.round((v.amountRupees ?? 0) * 100);
      if (amountPaise <= 0) {
        this.snackBar.open(`Enter an amount for ${v.donorName}`, 'Dismiss');
        return;
      }
      if (v.mode === 'upi' && !v.upiTxnId) {
        this.snackBar.open(`Enter the UPI Transaction ID for ${v.donorName}`, 'Dismiss');
        return;
      }
      if (
        (v.mode === 'bank_transfer' || v.mode === 'cheque_dd') &&
        (!v.bankName || !v.branchName || !v.transactionDate)
      ) {
        this.snackBar.open(`Enter bank, branch and date for ${v.donorName}`, 'Dismiss');
        return;
      }
      items.push({
        donor_id: v.donorId,
        amount_paise: amountPaise,
        mode: v.mode,
        reason: 'monthly_donation',
        upi_txn_id: v.mode === 'upi' ? v.upiTxnId : null,
        bank_name: v.mode !== 'upi' ? v.bankName : null,
        branch_name: v.mode !== 'upi' ? v.branchName : null,
        transaction_date: v.mode !== 'upi' ? v.transactionDate : null,
      });
    }

    const formData = new FormData();
    formData.append('period', `${this.yearControl.value}-${this.paddedMonth}`);
    formData.append('items', JSON.stringify(items));
    for (const item of items) {
      const donorId = item['donor_id'] as number;
      const file = this.files.get(donorId);
      if (file) formData.append(`screenshot_${donorId}`, file);
    }

    this.submitting = true;
    this.donationService.generateBatch(formData).subscribe({
      next: (res) => {
        this.submitting = false;
        this.result = res;
        this.snackBar.open(`${res.generated} receipt(s) generated, ${res.failed} failed`, 'Dismiss');
        this.toggleAll(false);
      },
      error: (err) => {
        this.submitting = false;
        this.snackBar.open(err?.error?.detail ?? 'Batch generation failed', 'Dismiss');
      },
    });
  }

  pdfUrl(relative: string | null): string {
    return relative ? toAbsoluteApiUrl(relative) : '';
  }
}