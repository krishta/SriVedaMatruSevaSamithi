import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';

import { DonorDetail, DonorService } from '../../services/donor.service';
import { InrCurrencyPipe } from '../../pipes/inr-currency.pipe';

@Component({
  selector: 'svmss-admin-donor',
  standalone: true,
  imports: [CommonModule, RouterLink, MatCardModule, MatTableModule, MatButtonModule, InrCurrencyPipe],
  template: `
    <div class="page-container svmss-card" style="max-width: 900px;">
      <a routerLink="/admin/ledger">&larr; Back to ledger</a>
      <p *ngIf="loading" role="status">Loading donor details…</p>
      <p *ngIf="errorMessage" role="alert">{{ errorMessage }}</p>

      <mat-card *ngIf="donor">
        <mat-card-header>
          <mat-card-title>{{ donor.name }}</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <p><strong>Phone:</strong> {{ donor.phone }}</p>
          <p *ngIf="donor.email"><strong>Email:</strong> {{ donor.email }}</p>
          <p *ngIf="donor.address"><strong>Address:</strong> {{ donor.address }}</p>
          <p><strong>Lifetime total:</strong> {{ donor.lifetime_total_paise | inrCurrency }}</p>
        </mat-card-content>
      </mat-card>

      <h3>Donation history</h3>
      <table mat-table [dataSource]="donor.donations" class="full-width" *ngIf="donor">
        <ng-container matColumnDef="date">
          <th mat-header-cell *matHeaderCellDef>Date</th>
          <td mat-cell *matCellDef="let row">{{ row.created_at | date: 'dd-MMM-yyyy' }}</td>
        </ng-container>
        <ng-container matColumnDef="amount">
          <th mat-header-cell *matHeaderCellDef>Amount</th>
          <td mat-cell *matCellDef="let row">{{ row.amount_paise | inrCurrency }}</td>
        </ng-container>
        <ng-container matColumnDef="reason">
          <th mat-header-cell *matHeaderCellDef>Reason</th>
          <td mat-cell *matCellDef="let row">{{ row.reason }}</td>
        </ng-container>
        <ng-container matColumnDef="status">
          <th mat-header-cell *matHeaderCellDef>Status</th>
          <td mat-cell *matCellDef="let row">{{ row.status }}</td>
        </ng-container>
        <ng-container matColumnDef="receipt">
          <th mat-header-cell *matHeaderCellDef>Receipt</th>
          <td mat-cell *matCellDef="let row">{{ row.receipt_no ?? '—' }}</td>
        </ng-container>
        <tr mat-header-row *matHeaderRowDef="columns"></tr>
        <tr mat-row *matRowDef="let row; columns: columns"></tr>
      </table>
    </div>
  `,
})
export class AdminDonorComponent implements OnInit {
  columns = ['date', 'amount', 'reason', 'status', 'receipt'];
  donor: DonorDetail | null = null;
  loading = false;
  errorMessage = '';

  constructor(
    private route: ActivatedRoute,
    private donorService: DonorService,
    private changeDetector: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.loading = true;
    this.donorService.get(id).subscribe({
      next: (donor) => {
        this.donor = donor;
        this.loading = false;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.errorMessage = 'Could not load donor details. Please return to the ledger and try again.';
        this.changeDetector.markForCheck();
      },
    });
  }
}