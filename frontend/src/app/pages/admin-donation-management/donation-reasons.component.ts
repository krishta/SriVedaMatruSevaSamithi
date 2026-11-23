import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatTableModule } from '@angular/material/table';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import {
  DonationReason,
  DonationReasonService,
} from '../../services/donation-reason.service';

@Component({
  selector: 'svmss-donation-reasons',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatTableModule,
    MatSnackBarModule,
  ],
  template: `
    <section aria-labelledby="reasons-heading">
      <h3 id="reasons-heading">{{ editing ? 'Edit donation reason' : 'Add donation reason' }}</h3>
      <form class="reason-form" (ngSubmit)="save()">
        <mat-form-field>
          <mat-label>Reason name</mat-label>
          <input
            matInput
            name="reasonLabel"
            [(ngModel)]="label"
            required
            maxlength="120"
            autocomplete="off"
          />
        </mat-form-field>
        <button mat-raised-button color="primary" type="submit" [disabled]="saving || !label.trim()">
          {{ saving ? 'Saving…' : editing ? 'Update reason' : 'Add reason' }}
        </button>
        <button mat-button type="button" *ngIf="editing" (click)="cancelEdit()">Cancel</button>
      </form>

      <p *ngIf="loading" role="status">Loading donation reasons…</p>
      <p *ngIf="errorMessage" role="alert">{{ errorMessage }}</p>
      <div class="svmss-table-scroll" *ngIf="!loading && !errorMessage">
        <table mat-table [dataSource]="reasons" class="full-width">
          <ng-container matColumnDef="label">
            <th mat-header-cell *matHeaderCellDef>Reason</th>
            <td mat-cell *matCellDef="let row">{{ row.label }}</td>
          </ng-container>
          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>Status</th>
            <td mat-cell *matCellDef="let row">
              {{ row.is_active ? 'Active' : 'Archived' }}{{ row.is_system ? ' · Required' : '' }}
            </td>
          </ng-container>
          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef>Actions</th>
            <td mat-cell *matCellDef="let row">
              <ng-container *ngIf="!row.is_system">
                <button mat-button *ngIf="row.is_active" (click)="startEdit(row)">Edit</button>
                <button mat-button color="warn" *ngIf="row.is_active" (click)="archive(row)">Archive</button>
                <button mat-button *ngIf="!row.is_active" (click)="activate(row)">Restore</button>
              </ng-container>
            </td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="columns"></tr>
          <tr mat-row *matRowDef="let row; columns: columns"></tr>
        </table>
      </div>
    </section>
  `,
  styles: [
    `
      .reason-form {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
        margin-bottom: 20px;
      }

      .reason-form mat-form-field {
        width: min(420px, 100%);
      }
    `,
  ],
})
export class DonationReasonsComponent implements OnInit {
  columns = ['label', 'status', 'actions'];
  reasons: DonationReason[] = [];
  label = '';
  editing: DonationReason | null = null;
  saving = false;
  loading = false;
  errorMessage = '';

  constructor(
    private reasonService: DonationReasonService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.errorMessage = '';
    this.reasonService.all().subscribe({
      next: (reasons) => {
        this.reasons = reasons;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.errorMessage = 'Could not load donation reasons. Please try again.';
      },
    });
  }

  startEdit(reason: DonationReason): void {
    this.editing = reason;
    this.label = reason.label;
  }

  cancelEdit(): void {
    this.editing = null;
    this.label = '';
  }

  save(): void {
    const label = this.label.trim();
    if (!label || this.saving) return;
    this.saving = true;
    const request = this.editing
      ? this.reasonService.update(this.editing.code, label)
      : this.reasonService.create(label);
    request.subscribe({
      next: () => {
        this.saving = false;
        this.snackBar.open(this.editing ? 'Donation reason updated' : 'Donation reason added', 'Dismiss');
        this.cancelEdit();
        this.load();
      },
      error: (error) => {
        this.saving = false;
        this.snackBar.open(error?.error?.detail ?? 'Could not save donation reason', 'Dismiss');
      },
    });
  }

  archive(reason: DonationReason): void {
    if (!confirm(`Archive “${reason.label}”? It will no longer appear on new donations.`)) return;
    this.reasonService.archive(reason.code).subscribe({
      next: () => {
        this.snackBar.open('Donation reason archived', 'Dismiss');
        if (this.editing?.code === reason.code) this.cancelEdit();
        this.load();
      },
      error: (error) => this.snackBar.open(error?.error?.detail ?? 'Could not archive reason', 'Dismiss'),
    });
  }

  activate(reason: DonationReason): void {
    this.reasonService.activate(reason.code).subscribe({
      next: () => {
        this.snackBar.open('Donation reason restored', 'Dismiss');
        this.load();
      },
      error: (error) => this.snackBar.open(error?.error?.detail ?? 'Could not restore reason', 'Dismiss'),
    });
  }
}
