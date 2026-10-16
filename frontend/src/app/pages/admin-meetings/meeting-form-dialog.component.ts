import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { QuillModule } from 'ngx-quill';

export interface MeetingFormDialogData {
  id: number | null;
  meetingDate: string | null;
  notesHtml: string | null;
}

export interface MeetingFormResult {
  meeting_date: string;
  notes_html: string;
}

/** Log/edit dialog: date + rich-text notes (Bold/Italic/Underline/lists only — kept small so the
 * dependency-free backend docx exporter can faithfully reproduce every supported format). */
@Component({
  selector: 'svmss-meeting-form-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    QuillModule,
  ],
  template: `
    <h2 mat-dialog-title>{{ data.id ? 'Edit meeting notes' : 'Log meeting notes' }}</h2>
    <mat-dialog-content>
      <form [formGroup]="form" class="meeting-form">
        <mat-form-field class="full-width">
          <mat-label>Meeting Date</mat-label>
          <input matInput type="date" formControlName="meetingDate" required />
        </mat-form-field>

        <label class="block-label">Minutes of Meeting</label>
        <quill-editor
          formControlName="notesHtml"
          format="html"
          [modules]="editorModules"
          placeholder="Capture what was discussed and decided…"
        ></quill-editor>
      </form>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-raised-button (click)="cancel()">Cancel</button>
      <button mat-raised-button color="primary" [disabled]="form.invalid" (click)="save()">
        Record meeting notes
      </button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      .meeting-form {
        min-width: 480px;
        max-width: 640px;
      }
      .block-label {
        display: block;
        margin: 8px 0;
        font-weight: 500;
      }
      ::ng-deep quill-editor .ql-editor {
        min-height: 200px;
      }
    `,
  ],
})
export class MeetingFormDialogComponent {
  private dialogRef = inject(MatDialogRef<MeetingFormDialogComponent, MeetingFormResult>);
  data = inject<MeetingFormDialogData>(MAT_DIALOG_DATA);

  editorModules = {
    toolbar: [['bold', 'italic', 'underline'], [{ list: 'ordered' }, { list: 'bullet' }]],
  };

  form = new FormBuilder().group({
    meetingDate: [this.data.meetingDate ?? '', Validators.required],
    notesHtml: [this.data.notesHtml ?? '', Validators.required],
  });

  cancel(): void {
    this.dialogRef.close();
  }

  save(): void {
    if (this.form.invalid) return;
    const v = this.form.value;
    this.dialogRef.close({ meeting_date: v.meetingDate!, notes_html: v.notesHtml! });
  }
}