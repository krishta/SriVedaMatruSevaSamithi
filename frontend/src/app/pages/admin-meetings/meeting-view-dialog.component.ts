import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';

export interface MeetingViewDialogData {
  meetingDate: string;
  notesHtml: string;
}

/** Read-only popup showing one meeting's rich-text minutes (Angular sanitizes the innerHTML binding). */
@Component({
  selector: 'svmss-meeting-view-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule],
  template: `
    <h2 mat-dialog-title>Minutes of Meeting — {{ data.meetingDate | date: 'dd-MMM-yyyy' }}</h2>
    <mat-dialog-content>
      <div class="notes-view" [innerHTML]="data.notesHtml"></div>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-raised-button (click)="close()">Close</button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      .notes-view {
        min-width: 420px;
        max-width: 640px;
        line-height: 1.5;
      }
      .notes-view ul,
      .notes-view ol {
        margin: 0 0 0 20px;
        padding: 0;
      }
    `,
  ],
})
export class MeetingViewDialogComponent {
  constructor(
    private dialogRef: MatDialogRef<MeetingViewDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: MeetingViewDialogData
  ) {}

  close(): void {
    this.dialogRef.close();
  }
}