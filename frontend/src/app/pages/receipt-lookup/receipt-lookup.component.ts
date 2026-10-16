import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatListModule } from '@angular/material/list';

import { ReceiptLookupItem, ReceiptService } from '../../services/receipt.service';
import { InrCurrencyPipe } from '../../pipes/inr-currency.pipe';

@Component({
  selector: 'svmss-receipt-lookup',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatListModule,
    InrCurrencyPipe,
  ],
  template: `
    <div class="page-container">
      <h2>Look up my receipts</h2>
      <form [formGroup]="form" (ngSubmit)="lookup()">
        <mat-form-field class="full-width">
          <mat-label>Phone (10 digits)</mat-label>
          <input matInput formControlName="phone" maxlength="10" />
        </mat-form-field>
        <mat-form-field class="full-width">
          <mat-label>Last 4 digits of your phone</mat-label>
          <input matInput formControlName="last4" maxlength="4" />
        </mat-form-field>
        <button mat-raised-button color="primary" type="submit" [disabled]="form.invalid || loading">
          {{ loading ? 'Searching…' : 'Find my receipts' }}
        </button>
      </form>

      <mat-list *ngIf="results.length">
        <mat-list-item *ngFor="let r of results">
          {{ r.receipt_no }} — {{ r.amount_paise | inrCurrency }} — {{ r.status }}
          <a [href]="r.pdf_url" target="_blank" style="margin-left: 8px;">Download</a>
        </mat-list-item>
      </mat-list>
      <p *ngIf="searched && !results.length">No receipts found for these details.</p>
    </div>
  `,
})
export class ReceiptLookupComponent {
  private fb = inject(FormBuilder);
  results: ReceiptLookupItem[] = [];
  loading = false;
  searched = false;

  form = this.fb.group({
    phone: ['', [Validators.required, Validators.pattern(/^\d{10}$/)]],
    last4: ['', [Validators.required, Validators.pattern(/^\d{4}$/)]],
  });

  constructor(private receiptService: ReceiptService) {}

  lookup(): void {
    if (this.form.invalid) return;
    this.loading = true;
    this.searched = false;
    const { phone, last4 } = this.form.value;
    this.receiptService.lookup(phone!, last4!).subscribe({
      next: (res) => {
        this.results = res;
        this.loading = false;
        this.searched = true;
      },
      error: () => {
        this.results = [];
        this.loading = false;
        this.searched = true;
      },
    });
  }
}