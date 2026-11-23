import { Component, OnInit } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { finalize, TimeoutError, timeout } from 'rxjs';

import { DonationReason, DonationReasonService } from '../../services/donation-reason.service';
import { DonationReportRequest, ReportService } from '../../services/report.service';

interface ReportColumn {
  key: string;
  label: string;
  required?: boolean;
}

@Component({
  selector: 'svmss-report-generation',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
  ],
  template: `
    <section aria-labelledby="report-heading">
      <h3 id="report-heading">Generate donation report</h3>
      <form (ngSubmit)="generate()">
        <div class="report-filters">
          <mat-form-field>
            <mat-label>Report type</mat-label>
            <mat-select [(ngModel)]="reportType" name="reportType">
              <mat-option *ngFor="let report of reportTypes" [value]="report.value">
                {{ report.label }}
              </mat-option>
            </mat-select>
          </mat-form-field>
          <mat-form-field *ngIf="reportType !== 'monthly_donations'">
            <mat-label>Reason (optional)</mat-label>
            <mat-select [(ngModel)]="reasonCode" name="reasonCode">
              <mat-option value="">All reasons</mat-option>
              <mat-option *ngFor="let reason of reasons" [value]="reason.code">
                {{ reason.label }}{{ reason.is_active ? '' : ' (Archived)' }}
              </mat-option>
            </mat-select>
          </mat-form-field>
          <mat-form-field>
            <mat-label>Donation received from</mat-label>
            <input matInput type="date" [(ngModel)]="dateFrom" name="dateFrom" />
          </mat-form-field>
          <mat-form-field>
            <mat-label>Donation received to</mat-label>
            <input matInput type="date" [(ngModel)]="dateTo" name="dateTo" />
          </mat-form-field>
        </div>

        <p class="hint">
          Period filters use the donation received/recorded date. The exported workbook includes
          both that date and the receipt issue date, plus a summary sheet.
        </p>
        <mat-checkbox
          [(ngModel)]="includeVoided"
          name="includeVoided"
        >
          Include voided donations / receipts
        </mat-checkbox>

        <h4>Columns</h4>
        <div class="report-columns">
          <label class="report-column" *ngFor="let column of columns">
            <input
              type="checkbox"
              [checked]="isSelected(column)"
              [disabled]="column.required"
              (change)="toggleColumn(column, $event)"
            />
            <span>{{ column.label }}<strong *ngIf="column.required"> · Required</strong></span>
          </label>
        </div>

        <p *ngIf="errorMessage" role="alert">{{ errorMessage }}</p>
        <button mat-raised-button color="primary" type="submit" [disabled]="generating">
          {{ generating ? 'Generating…' : 'Download Excel report' }}
        </button>
      </form>
    </section>
  `,
  styles: [
    `
      .report-filters {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 12px;
      }

      .report-filters mat-form-field {
        width: 100%;
      }

      .hint {
        color: var(--svmss-muted);
      }

      .report-columns {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 10px 16px;
        margin: 0 0 20px;
      }

      .report-column {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .report-column strong {
        color: var(--svmss-muted);
        font-size: 0.8em;
        font-weight: 500;
      }
    `,
  ],
})
export class ReportGenerationComponent implements OnInit {
  reportTypes = [
    { value: 'reason_period', label: 'Donations by reason and period' },
    { value: 'monthly_donations', label: 'Monthly donations by donor' },
    { value: 'donor_summary', label: 'Donor contribution summary' },
    { value: 'payment_reconciliation', label: 'Payment method reconciliation' },
    { value: 'receipt_register', label: 'Receipt register' },
  ];

  columns: ReportColumn[] = [
    { key: 'donor_name', label: 'Donor name', required: true },
    { key: 'donation_date', label: 'Donation received date', required: true },
    { key: 'receipt_date', label: 'Receipt issue date', required: true },
    { key: 'reason', label: 'Reason', required: true },
    { key: 'amount', label: 'Amount', required: true },
    { key: 'payment_mode', label: 'Payment method' },
    { key: 'donation_status', label: 'Donation / receipt status' },
    { key: 'receipt_no', label: 'Receipt number' },
    { key: 'phone', label: 'Phone' },
    { key: 'email', label: 'Email' },
    { key: 'address', label: 'Address' },
    { key: 'reason_detail', label: 'Reason details' },
  ];

  reasons: DonationReason[] = [];
  reportType = 'reason_period';
  reasonCode = '';
  dateFrom = '';
  dateTo = '';
  includeVoided = false;
  selectedColumns = new Set([
    'donor_name',
    'donation_date',
    'receipt_date',
    'reason',
    'amount',
    'payment_mode',
    'receipt_no',
  ]);
  generating = false;
  errorMessage = '';

  constructor(
    private reasonService: DonationReasonService,
    private reportService: ReportService
  ) {}

  ngOnInit(): void {
    this.reasonService.all().subscribe({
      next: (reasons) => (this.reasons = reasons),
      error: () => (this.errorMessage = 'Could not load donation reasons for the report filter.'),
    });
  }

  isSelected(column: ReportColumn): boolean {
    return column.required || this.selectedColumns.has(column.key);
  }

  toggleColumn(column: ReportColumn, event: Event): void {
    if (column.required) return;
    const checked = (event.target as HTMLInputElement).checked;
    if (checked) this.selectedColumns.add(column.key);
    else this.selectedColumns.delete(column.key);
  }

  generate(): void {
    if (this.generating) return;
    if (this.dateFrom && this.dateTo && this.dateFrom > this.dateTo) {
      this.errorMessage = 'The start date must be on or before the end date.';
      return;
    }

    this.generating = true;
    this.errorMessage = '';
    const payload: DonationReportRequest = {
      report_type: this.reportType,
      columns: this.columns
        .filter((column) => this.isSelected(column))
        .map((column) => column.key),
      date_from: this.dateFrom || null,
      date_to: this.dateTo || null,
      reason_code:
        this.reportType === 'monthly_donations' || !this.reasonCode ? null : this.reasonCode,
      include_voided: this.includeVoided,
    };

    this.reportService
      .export(payload)
      .pipe(
        timeout({ first: 30_000 }),
        finalize(() => (this.generating = false))
      )
      .subscribe({
        next: (blob) => {
          const from = this.dateFrom || 'all';
          const to = this.dateTo || 'all';
          const url = window.URL.createObjectURL(blob);
          const anchor = document.createElement('a');
          anchor.href = url;
          anchor.download = `svmss_${this.reportType}_${from}_${to}.xlsx`;
          anchor.click();
          window.setTimeout(() => window.URL.revokeObjectURL(url), 1000);
        },
        error: (error: unknown) => {
          if (error instanceof HttpErrorResponse && error.status === 404) {
            this.errorMessage = 'No data to generate for the selected filters.';
            window.alert(this.errorMessage);
          } else if (error instanceof TimeoutError) {
            this.errorMessage = 'The report request timed out. Check the API connection and try again.';
          } else {
            this.errorMessage = 'Could not generate the report. Check the filters and try again.';
          }
        },
      });
  }
}
