import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCardModule } from '@angular/material/card';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { DonorListItem, DonorListResponse, DonorService } from '../../services/donor.service';

@Component({
  selector: 'svmss-admin-donors',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    ReactiveFormsModule,
    FormsModule,
    MatTableModule,
    MatPaginatorModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatCardModule,
    MatSnackBarModule,
  ],
  template: `
    <div class="page-container svmss-card" style="max-width: 1100px;">
      <h2>Donor Master List</h2>

      <mat-card style="margin-bottom: 16px;">
        <mat-card-content>
          <h3>{{ editingId ? 'Edit donor' : 'Add donor' }}</h3>
          <form [formGroup]="form" (ngSubmit)="save()" class="donor-form">
            <mat-form-field>
              <mat-label>Name</mat-label>
              <input matInput formControlName="name" required />
            </mat-form-field>
            <mat-form-field>
              <mat-label>Phone (10 digits)</mat-label>
              <input matInput formControlName="phone" required maxlength="10" />
            </mat-form-field>
            <mat-form-field>
              <mat-label>Email (optional)</mat-label>
              <input matInput type="email" formControlName="email" />
            </mat-form-field>
            <mat-form-field>
              <mat-label>Address (optional)</mat-label>
              <input matInput formControlName="address" />
            </mat-form-field>
            <div class="form-actions">
              <button mat-raised-button color="primary" type="submit" [disabled]="form.invalid || saving">
                {{ saving ? 'Saving…' : editingId ? 'Update donor' : 'Add donor' }}
              </button>
              <button mat-raised-button type="button" *ngIf="editingId" (click)="cancelEdit()">Cancel</button>
            </div>
          </form>
        </mat-card-content>
      </mat-card>

      <div class="toolbar-row">
        <mat-form-field>
          <mat-label>Search name/phone</mat-label>
          <input matInput [(ngModel)]="search" [ngModelOptions]="{ standalone: true }" (keyup.enter)="reload()" />
        </mat-form-field>
        <button mat-raised-button color="primary" (click)="reload()">Search</button>
      </div>

      <div class="svmss-table-scroll">
      <table mat-table [dataSource]="data.items" class="full-width">
        <ng-container matColumnDef="name">
          <th mat-header-cell *matHeaderCellDef>Name</th>
          <td mat-cell *matCellDef="let row">
            <a [routerLink]="['/admin/donors', row.id]">{{ row.name }}</a>
          </td>
        </ng-container>
        <ng-container matColumnDef="phone">
          <th mat-header-cell *matHeaderCellDef>Phone</th>
          <td mat-cell *matCellDef="let row">{{ row.phone }}</td>
        </ng-container>
        <ng-container matColumnDef="email">
          <th mat-header-cell *matHeaderCellDef>Email</th>
          <td mat-cell *matCellDef="let row">{{ row.email || '—' }}</td>
        </ng-container>
        <ng-container matColumnDef="address">
          <th mat-header-cell *matHeaderCellDef>Address</th>
          <td mat-cell *matCellDef="let row">{{ row.address || '—' }}</td>
        </ng-container>
        <ng-container matColumnDef="actions">
          <th mat-header-cell *matHeaderCellDef>Actions</th>
          <td mat-cell *matCellDef="let row">
            <button mat-raised-button (click)="startEdit(row)">Edit</button>
            <button mat-raised-button color="warn" (click)="remove(row)">Delete</button>
          </td>
        </ng-container>
        <tr mat-header-row *matHeaderRowDef="columns"></tr>
        <tr mat-row *matRowDef="let row; columns: columns"></tr>
      </table>
      </div>
      <p *ngIf="loading" role="status">Loading donors…</p>
      <p *ngIf="errorMessage" role="alert">{{ errorMessage }}</p>
      <p *ngIf="!loading && !errorMessage && !data.items.length">No donors found.</p>

      <mat-paginator
        [length]="data.total"
        [pageSize]="data.size"
        [pageIndex]="data.page - 1"
        (page)="onPage($event)"
      ></mat-paginator>
    </div>
  `,
  styles: [
    `
      .admin-nav {
        display: flex;
        gap: 12px;
        margin-bottom: 12px;
      }
      .donor-form {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
      }
      .donor-form mat-form-field {
        width: 100%;
      }
      .form-actions {
        grid-column: 1 / -1;
      }
      @media (max-width: 600px) {
        .donor-form {
          grid-template-columns: 1fr;
        }
      }
    `,
  ],
})
export class AdminDonorsComponent implements OnInit {
  private fb = inject(FormBuilder);
  columns = ['name', 'phone', 'email', 'address', 'actions'];
  data: DonorListResponse = { items: [], total: 0, page: 1, size: 50 };
  search = '';
  saving = false;
  editingId: number | null = null;
  loading = false;
  errorMessage = '';

  form = this.fb.group({
    name: ['', Validators.required],
    phone: ['', [Validators.required, Validators.pattern(/^\d{10}$/)]],
    email: [''],
    address: [''],
  });

  constructor(
    private donorService: DonorService,
    private snackBar: MatSnackBar,
    private changeDetector: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.reload();
  }

  reload(page = 1): void {
    this.loading = true;
    this.errorMessage = '';
    this.donorService
      .list({ page, size: this.data.size, ...(this.search ? { search: this.search } : {}) })
      .subscribe({
        next: (res) => {
          this.data = res;
          this.loading = false;
          this.changeDetector.markForCheck();
        },
        error: () => {
          this.loading = false;
          this.errorMessage = 'Could not load donors. Please try again.';
          this.changeDetector.markForCheck();
        },
      });
  }

  onPage(event: PageEvent): void {
    this.data.size = event.pageSize;
    this.reload(event.pageIndex + 1);
  }

  startEdit(row: DonorListItem): void {
    this.editingId = row.id;
    this.form.patchValue({
      name: row.name,
      phone: row.phone.replace('+91', ''),
      email: row.email ?? '',
      address: row.address ?? '',
    });
  }

  cancelEdit(): void {
    this.editingId = null;
    this.form.reset();
  }

  save(): void {
    if (this.form.invalid) return;
    const v = this.form.value;
    const payload = {
      name: v.name!,
      phone: v.phone!,
      email: v.email || null,
      address: v.address || null,
    };
    this.saving = true;
    const request$ = this.editingId
      ? this.donorService.update(this.editingId, payload)
      : this.donorService.create(payload);

    request$.subscribe({
      next: () => {
        this.saving = false;
        this.snackBar.open(this.editingId ? 'Donor updated' : 'Donor added', 'Dismiss');
        this.cancelEdit();
        this.reload(this.data.page);
      },
      error: (err) => {
        this.saving = false;
        this.snackBar.open(err?.error?.detail ?? 'Could not save donor', 'Dismiss');
      },
    });
  }

  remove(row: DonorListItem): void {
    if (!confirm(`Remove ${row.name} from the donor list? Their past receipts are kept.`)) return;
    this.donorService.delete(row.id).subscribe({
      next: () => {
        this.snackBar.open('Donor removed', 'Dismiss');
        this.reload(this.data.page);
      },
      error: () => this.snackBar.open('Could not remove donor', 'Dismiss'),
    });
  }
}