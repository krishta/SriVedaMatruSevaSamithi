import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { MeetingListResponse, MeetingService } from '../../services/meeting.service';
import { MeetingViewDialogComponent } from './meeting-view-dialog.component';
import { MeetingFormDialogComponent, MeetingFormResult } from './meeting-form-dialog.component';

@Component({
  selector: 'svmss-admin-meetings',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatTableModule,
    MatPaginatorModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatDialogModule,
    MatSnackBarModule,
  ],
  template: `
    <div class="page-container svmss-card" style="max-width: 1100px;">
      <h2 style="font-weight: 700;">Monthly Meetings</h2>

      <div class="toolbar-row">
        <mat-form-field style="width: 260px;">
          <mat-label>Search notes</mat-label>
          <input matInput [(ngModel)]="search" (keyup.enter)="reload()" />
        </mat-form-field>
        <mat-form-field style="width: 170px;">
          <mat-label>From</mat-label>
          <input matInput type="date" [(ngModel)]="dateFrom" (change)="reload()" />
        </mat-form-field>
        <mat-form-field style="width: 170px;">
          <mat-label>To</mat-label>
          <input matInput type="date" [(ngModel)]="dateTo" (change)="reload()" />
        </mat-form-field>
        <button mat-raised-button color="primary" (click)="reload()">Search</button>
        <button mat-raised-button (click)="exportAll()" [disabled]="exporting">
          {{ exporting ? 'Exporting…' : 'Export all (.docx)' }}
        </button>
        <span class="spacer"></span>
        <button mat-raised-button color="primary" (click)="openLog()">Log meeting notes</button>
      </div>

      <div class="svmss-table-scroll">
        <table mat-table [dataSource]="data.items" class="full-width">
          <ng-container matColumnDef="date">
            <th mat-header-cell *matHeaderCellDef>Meeting Date</th>
            <td mat-cell *matCellDef="let row">{{ row.meeting_date | date: 'dd-MMM-yyyy' }}</td>
          </ng-container>
          <ng-container matColumnDef="notes">
            <th mat-header-cell *matHeaderCellDef>Minutes of Meeting</th>
            <td mat-cell *matCellDef="let row">
              <a href="javascript:void(0)" (click)="view(row.id, row.meeting_date)">{{
                row.notes_preview || 'View'
              }}</a>
            </td>
          </ng-container>
          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef>Actions</th>
            <td mat-cell *matCellDef="let row">
              <button mat-raised-button (click)="edit(row.id)">Edit</button>
              <button mat-raised-button (click)="downloadOne(row.id, row.meeting_date)">
                Download .docx
              </button>
              <button mat-raised-button color="warn" (click)="remove(row.id)">Delete</button>
            </td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="columns"></tr>
          <tr mat-row *matRowDef="let row; columns: columns"></tr>
        </table>
      </div>

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
      .toolbar-row .spacer {
        flex: 1;
      }
    `,
  ],
})
export class AdminMeetingsComponent implements OnInit {
  private meetingService = inject(MeetingService);
  private dialog = inject(MatDialog);
  private snackBar = inject(MatSnackBar);

  columns = ['date', 'notes', 'actions'];
  data: MeetingListResponse = { items: [], total: 0, page: 1, size: 20 };
  search = '';
  dateFrom = '';
  dateTo = '';
  exporting = false;

  ngOnInit(): void {
    this.reload();
  }

  private filterParams(): Record<string, string> {
    const params: Record<string, string> = {};
    if (this.search) params['search'] = this.search;
    if (this.dateFrom) params['date_from'] = this.dateFrom;
    if (this.dateTo) params['date_to'] = this.dateTo;
    return params;
  }

  reload(page = 1): void {
    this.meetingService
      .list({ page, size: this.data.size, ...this.filterParams() })
      .subscribe((res) => (this.data = res));
  }

  onPage(event: PageEvent): void {
    this.data.size = event.pageSize;
    this.reload(event.pageIndex + 1);
  }

  view(id: number, meetingDate: string): void {
    this.meetingService.get(id).subscribe((meeting) => {
      this.dialog.open(MeetingViewDialogComponent, {
        data: { meetingDate: meeting.meeting_date, notesHtml: meeting.notes_html },
      });
    });
  }

  openLog(): void {
    const ref = this.dialog.open(MeetingFormDialogComponent, {
      data: { id: null, meetingDate: null, notesHtml: null },
    });
    ref.afterClosed().subscribe((result: MeetingFormResult | undefined) => {
      if (!result) return;
      this.meetingService.create(result).subscribe({
        next: () => {
          this.snackBar.open('Meeting notes recorded', 'Dismiss');
          this.reload(this.data.page);
        },
        error: () => this.snackBar.open('Failed to save meeting notes', 'Dismiss'),
      });
    });
  }

  edit(id: number): void {
    this.meetingService.get(id).subscribe((meeting) => {
      const ref = this.dialog.open(MeetingFormDialogComponent, {
        data: { id: meeting.id, meetingDate: meeting.meeting_date, notesHtml: meeting.notes_html },
      });
      ref.afterClosed().subscribe((result: MeetingFormResult | undefined) => {
        if (!result) return;
        this.meetingService.update(id, result).subscribe({
          next: () => {
            this.snackBar.open('Meeting notes updated', 'Dismiss');
            this.reload(this.data.page);
          },
          error: () => this.snackBar.open('Failed to update meeting notes', 'Dismiss'),
        });
      });
    });
  }

  remove(id: number): void {
    if (!confirm('Delete this meeting entry? This cannot be undone.')) return;
    this.meetingService.delete(id).subscribe({
      next: () => {
        this.snackBar.open('Meeting deleted', 'Dismiss');
        this.reload(this.data.page);
      },
      error: () => this.snackBar.open('Failed to delete meeting', 'Dismiss'),
    });
  }

  private downloadBlob(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  downloadOne(id: number, meetingDate: string): void {
    this.meetingService
      .exportOne(id)
      .subscribe((blob) => this.downloadBlob(blob, `svmss_meeting_${meetingDate}.docx`));
  }

  exportAll(): void {
    this.exporting = true;
    this.meetingService.exportAll(this.filterParams()).subscribe({
      next: (blob) => {
        this.exporting = false;
        this.downloadBlob(blob, 'svmss_meeting_minutes.docx');
      },
      error: () => {
        this.exporting = false;
      },
    });
  }
}