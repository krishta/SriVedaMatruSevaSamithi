import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { FormsModule } from '@angular/forms';

import { DonationService, DonationListResponse } from '../../services/donation.service';
import { ReceiptService } from '../../services/receipt.service';
import { InrCurrencyPipe } from '../../pipes/inr-currency.pipe';

@Component({
  selector: 'svmss-admin-ledger',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    MatTableModule,
    MatPaginatorModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    FormsModule,
    InrCurrencyPipe,
  ],
  template: `
    <div class="page-container svmss-card" style="max-width: 1100px;">
      <h2 style="font-weight: 700;">Donation Ledger</h2>
      <div class="toolbar-row">
        <mat-form-field style="width: 420px;">
          <mat-label>Search donor name/phone</mat-label>
          <input matInput [(ngModel)]="search" (keyup.enter)="reload()" />
        </mat-form-field>
        <button mat-raised-button color="primary" (click)="reload()">Search</button>
        <button mat-raised-button (click)="exportCsv()" [disabled]="exporting">
          {{ exporting ? 'Exporting…' : 'Export CSV' }}
        </button>
      </div>

      <div class="svmss-table-scroll">
      <table mat-table [dataSource]="data.items" class="full-width">
        <ng-container matColumnDef="date">
          <th mat-header-cell *matHeaderCellDef>Date</th>
          <td mat-cell *matCellDef="let row">{{ row.created_at | date: 'dd-MMM-yyyy' }}</td>
        </ng-container>
        <ng-container matColumnDef="donor">
          <th mat-header-cell *matHeaderCellDef>Donor</th>
          <td mat-cell *matCellDef="let row">
            <a [routerLink]="['/admin/donors', row.donor_id]">{{ row.donor_name }}</a>
          </td>
        </ng-container>
        <ng-container matColumnDef="amount">
          <th mat-header-cell *matHeaderCellDef>Amount</th>
          <td mat-cell *matCellDef="let row">{{ row.amount_paise | inrCurrency }}</td>
        </ng-container>
        <ng-container matColumnDef="reason">
          <th mat-header-cell *matHeaderCellDef>Reason</th>
          <td mat-cell *matCellDef="let row">{{ row.reason_other || row.reason }}</td>
        </ng-container>
        <ng-container matColumnDef="status">
          <th mat-header-cell *matHeaderCellDef>Status</th>
          <td mat-cell *matCellDef="let row">{{ row.status }}</td>
        </ng-container>
        <ng-container matColumnDef="receipt">
          <th mat-header-cell *matHeaderCellDef>Receipt</th>
          <td mat-cell *matCellDef="let row">{{ row.receipt_no }}</td>
        </ng-container>
        <ng-container matColumnDef="actions">
          <th mat-header-cell *matHeaderCellDef>Actions</th>
          <td mat-cell *matCellDef="let row">
            <button mat-raised-button color="warn" *ngIf="row.status === 'issued'" (click)="voidReceipt(row)">
              Void
            </button>
          </td>
        </ng-container>
        <tr mat-header-row *matHeaderRowDef="columns"></tr>
        <tr mat-row *matRowDef="let row; columns: columns"></tr>
      </table>
      </div>
      <p *ngIf="loading" role="status">Loading donations…</p>
      <p *ngIf="errorMessage" role="alert">{{ errorMessage }}</p>
      <p *ngIf="!loading && !errorMessage && !data.items.length">No donations found.</p>

      <mat-paginator
        [length]="data.total"
        [pageSize]="data.size"
        [pageIndex]="data.page - 1"
        (page)="onPage($event)"
      ></mat-paginator>
    </div>
  `,
})
export class AdminLedgerComponent implements OnInit {
  columns = ['date', 'donor', 'amount', 'reason', 'status', 'receipt', 'actions'];
  data: DonationListResponse = { items: [], total: 0, page: 1, size: 20 };
  search = '';
  exporting = false;
  loading = false;
  errorMessage = '';

  constructor(
    private donationService: DonationService,
    private receiptService: ReceiptService,
    private changeDetector: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.reload();
  }

  exportCsv(): void {
    this.exporting = true;
    this.donationService
      .exportCsv(this.search ? { search: this.search } : {})
      .subscribe({
        next: (blob) => {
          this.exporting = false;
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'svmss_donations.csv';
          a.click();
          window.URL.revokeObjectURL(url);
        },
        error: () => {
          this.exporting = false;
        },
      });
  }

  reload(page = 1): void {
    this.loading = true;
    this.errorMessage = '';
    this.donationService
      .list({ page, size: this.data.size, ...(this.search ? { search: this.search } : {}) })
      .subscribe({
        next: (res) => {
          this.data = res;
          this.loading = false;
          this.changeDetector.markForCheck();
        },
        error: () => {
          this.loading = false;
          this.errorMessage = 'Could not load donations. Please try again.';
          this.changeDetector.markForCheck();
        },
      });
  }

  onPage(event: PageEvent): void {
    this.data.size = event.pageSize;
    this.reload(event.pageIndex + 1);
  }

  voidReceipt(row: DonationListResponse['items'][number]): void {
    if (!row.receipt_id) return;
    const reason = prompt('Reason for voiding this receipt?');
    if (!reason) return;
    this.receiptService.void(row.receipt_id, reason).subscribe(() => this.reload(this.data.page));
  }
}