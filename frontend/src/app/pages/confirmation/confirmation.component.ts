import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { environment } from '../../../environments/environment';
import { DonationCreateResponse } from '../../services/donation.service';

@Component({
  selector: 'svmss-confirmation',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatButtonModule],
  template: `
    <div class="page-container" *ngIf="result">
      <mat-card>
        <mat-card-header>
          <mat-card-title>Thank you, {{ donorName }}!</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <p>Your donation has been recorded. Receipt No: <strong>{{ result.receipt_no }}</strong></p>
          <p *ngIf="result.email_sent">A copy has been emailed to you.</p>
          <div class="confirmation-actions">
            <a mat-raised-button color="primary" [href]="pdfUrl" target="_blank">Download Receipt PDF</a>
            <a mat-raised-button color="accent" [href]="whatsappUrl" target="_blank">
              Share on WhatsApp
            </a>
            <button mat-stroked-button type="button" (click)="backToHome()">Back to home</button>
          </div>
        </mat-card-content>
      </mat-card>
    </div>
    <div class="page-container" *ngIf="!result">
      <p>No submission found. <a (click)="backToHome()">Return to the admin ledger</a>.</p>
    </div>
  `,
  styles: [
    `
      .confirmation-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }
    `,
  ],
})
export class ConfirmationComponent {
  result: DonationCreateResponse | null = null;
  donorName = '';

  constructor(public router: Router) {
    const nav = this.router.getCurrentNavigation();
    const state = (nav?.extras.state ?? history.state) as {
      result?: DonationCreateResponse;
      donorName?: string;
    };
    this.result = state?.result ?? null;
    this.donorName = state?.donorName ?? '';
  }

  get pdfUrl(): string {
    return this.result ? `${environment.apiBaseUrl.replace(/\/api$/, '')}${this.result.pdf_url}` : '';
  }

  get whatsappUrl(): string {
    const msg = `Thank you for your donation to Sri Veda Matru Seva Samiti. Your receipt: ${this.pdfUrl}`;
    return `https://wa.me/?text=${encodeURIComponent(msg)}`;
  }

  backToHome(): void {
    void this.router.navigate(['/admin/ledger']);
  }
}