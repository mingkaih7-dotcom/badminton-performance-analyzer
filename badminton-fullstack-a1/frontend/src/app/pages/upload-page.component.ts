import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../api.service';

@Component({
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page">
      <div class="title">
        <h1>Upload</h1>
        <div class="lead">Select a match video and start analysis. Advanced settings are optional.</div>
      </div>

      <div class="card">
        <div class="section">
          <div class="label">Video</div>
          <input #fileInput class="file" type="file" accept="video/mp4,video/*" (change)="onFile($event)" />
          <div
            class="drop"
            [class.drag]="dragging"
            (click)="openPicker(fileInput)"
            (dragover)="onDragOver($event)"
            (dragleave)="onDragLeave($event)"
            (drop)="onDrop($event)"
          >
            <div class="dropTitle">Drag & drop a video here</div>
            <div class="dropSub">or click to choose a file</div>

            <div class="fileMeta" *ngIf="file">
              <div class="fileName">{{file.name}}</div>
              <div class="fileInfo">{{formatBytes(file.size)}}</div>
            </div>
          </div>
          <div class="note">Supported: mp4 and common video formats.</div>
        </div>

        <div class="actions">
          <button class="primary" [disabled]="!file || loading" (click)="submit()">
            <span *ngIf="!loading">Start analysis</span>
            <span *ngIf="loading">Submitting…</span>
          </button>
          <button class="ghost" [disabled]="loading" (click)="reset()">Reset</button>
          <button class="link" type="button" (click)="advancedOpen = !advancedOpen">{{advancedOpen ? 'Hide' : 'Show'}} advanced settings</button>
        </div>

        <div class="err" *ngIf="error">{{error}}</div>

        <div class="advanced" *ngIf="advancedOpen">
          <div class="advHeader">Advanced settings</div>

          <div class="grid">
            <div class="field">
              <div class="k">Max sample frames</div>
              <div class="d">Frames used to build background median. Higher is more stable but slower.</div>
              <input type="number" min="50" max="2000" [(ngModel)]="params.max_sample_num" />
            </div>

            <div class="field">
              <div class="k">Batch size</div>
              <div class="d">Bigger can be faster but uses more GPU/CPU memory.</div>
              <input type="number" min="1" max="64" [(ngModel)]="params.batch_size" />
            </div>

            <div class="field">
              <div class="k">Workers</div>
              <div class="d">Parallel workers for pipeline steps. Use 0 if unsure.</div>
              <input type="number" min="0" max="32" [(ngModel)]="params.num_workers" />
            </div>

            <div class="field">
              <div class="k">Large video mode</div>
              <div class="d">Recommended for 4K or high-bitrate videos.</div>
              <label class="switch">
                <input type="checkbox" [(ngModel)]="params.large_video" />
                <span class="slider"></span>
              </label>
            </div>

            <div class="field span2">
              <div class="k">Video range (seconds)</div>
              <div class="d">Analyze only a segment. Leave empty to process the full video.</div>
              <div class="range">
                <div class="rangeCol">
                  <div class="mini">Start</div>
                  <input type="number" min="0" [(ngModel)]="rangeStart" />
                </div>
                <div class="rangeCol">
                  <div class="mini">End</div>
                  <input type="number" min="0" [(ngModel)]="rangeEnd" />
                </div>
              </div>
              <div class="warn" *ngIf="rangeWarning">{{rangeWarning}}</div>
            </div>
          </div>

          <div class="presets">
            <div class="presetTitle">Presets</div>
            <button class="chip" type="button" [disabled]="loading" (click)="applyPreset('default')">Default</button>
            <button class="chip" type="button" [disabled]="loading" (click)="applyPreset('4k')">4K</button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .page{display:flex;flex-direction:column;gap:14px}
    .title{display:flex;flex-direction:column;gap:6px;text-align:center}
    h1{margin:0;font-size:30px;letter-spacing:-0.02em}
    .lead{color:#64748b;font-size:13px}

    .card{background:#ffffff;border:1px solid #e5e7eb;border-radius:18px;padding:18px;max-width:1120px;width:100%;margin:0 auto;box-shadow:0 10px 30px rgba(15,23,42,.06)}
    .section{display:flex;flex-direction:column;gap:10px}
    .label{color:#475569;font-size:12px}
    .note{color:#64748b;font-size:12px}

    .file{position:absolute;left:-9999px;opacity:0;width:1px;height:1px}

    .drop{border:1px dashed #cbd5e1;background:#f8fafc;border-radius:16px;padding:20px;cursor:pointer;display:flex;flex-direction:column;gap:6px;transition:150ms ease}
    .drop:hover{border-color:#94a3b8}
    .drop.drag{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.15) inset}
    .dropTitle{font-weight:800;color:#0f172a}
    .dropSub{color:#64748b;font-size:12px}

    .fileMeta{margin-top:8px;padding-top:12px;border-top:1px solid #e5e7eb;display:flex;align-items:baseline;justify-content:space-between;gap:12px}
    .fileName{font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
    .fileInfo{color:#64748b;font-size:12px;flex:0 0 auto}

    input,select{background:#ffffff;color:#0f172a;border:1px solid #cbd5e1;border-radius:12px;padding:10px 12px;outline:none}
    input:focus,select:focus{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.15)}

    .actions{display:flex;align-items:center;justify-content:center;gap:10px;flex-wrap:wrap;margin-top:14px}
    .primary{background:#2563eb;color:#fff;border:0;border-radius:12px;padding:10px 16px;font-weight:800;cursor:pointer}
    .ghost{background:#ffffff;color:#0f172a;border:1px solid #cbd5e1;border-radius:12px;padding:10px 14px;font-weight:700;cursor:pointer}
    .link{background:transparent;border:0;color:#475569;cursor:pointer;padding:10px 6px}
    .link:hover{color:#0f172a}
    button:disabled{opacity:.55;cursor:not-allowed}

    .err{margin-top:10px;color:#dc2626;text-align:center}

    .advanced{margin-top:16px;border-top:1px solid #e5e7eb;padding-top:14px;display:flex;flex-direction:column;gap:12px}
    .advHeader{font-weight:900;color:#0f172a}
    .grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
    .field{display:flex;flex-direction:column;gap:6px}
    .k{font-size:12px;color:#334155;font-weight:700}
    .d{font-size:12px;color:#64748b}
    .span2{grid-column:1 / -1}

    .range{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
    .rangeCol{display:flex;flex-direction:column;gap:6px}
    .mini{font-size:11px;color:#64748b}
    .warn{color:#b45309;font-size:12px}

    .presets{display:flex;align-items:center;justify-content:center;gap:10px;flex-wrap:wrap;margin-top:4px}
    .presetTitle{color:#64748b;font-size:12px}
    .chip{background:#ffffff;color:#0f172a;border:1px solid #cbd5e1;border-radius:999px;padding:8px 12px;cursor:pointer;font-weight:800}
    .chip:hover{border-color:#94a3b8}

    .switch{position:relative;display:inline-block;width:46px;height:26px}
    .switch input{opacity:0;width:0;height:0}
    .slider{position:absolute;cursor:pointer;top:0;left:0;right:0;bottom:0;background:#cbd5e1;border-radius:999px;transition:150ms ease}
    .slider:before{position:absolute;content:'';height:20px;width:20px;left:3px;top:3px;background:#ffffff;border-radius:999px;transition:150ms ease;box-shadow:0 2px 8px rgba(15,23,42,.18)}
    .switch input:checked + .slider{background:#2563eb}
    .switch input:checked + .slider:before{transform:translateX(20px)}

    @media (max-width: 720px){
      .card{padding:14px}
      .grid{grid-template-columns:1fr}
      .range{grid-template-columns:1fr}
      .title{text-align:left}
      .actions{justify-content:flex-start}
      .presets{justify-content:flex-start}
    }
  `]
})
export class UploadPageComponent {
  file: File | null = null;
  loading = false;
  error = '';
  dragging = false;
  advancedOpen = false;
  rangeStart: number | null = null;
  rangeEnd: number | null = null;
  rangeWarning = '';
  params: any = { max_sample_num: 600, batch_size: 8, num_workers: 0, large_video: true };

  constructor(private api: ApiService, private router: Router) {}

  onFile(e: Event) {
    const input = e.target as HTMLInputElement;
    this.file = input.files && input.files.length > 0 ? input.files[0] : null;
  }

  openPicker(input: HTMLInputElement) {
    if (this.loading) return;
    input.click();
  }

  onDragOver(e: DragEvent) {
    e.preventDefault();
    if (this.loading) return;
    this.dragging = true;
  }

  onDragLeave(e: DragEvent) {
    e.preventDefault();
    this.dragging = false;
  }

  onDrop(e: DragEvent) {
    e.preventDefault();
    this.dragging = false;
    if (this.loading) return;
    const f = e.dataTransfer?.files && e.dataTransfer.files.length > 0 ? e.dataTransfer.files[0] : null;
    this.file = f;
  }

  reset() {
    if (this.loading) return;
    this.file = null;
    this.error = '';
    this.rangeStart = null;
    this.rangeEnd = null;
    this.rangeWarning = '';
    this.params = { max_sample_num: 600, batch_size: 8, num_workers: 0, large_video: true };
  }

  applyPreset(name: 'default' | '4k') {
    if (this.loading) return;
    if (name === 'default') this.params = { max_sample_num: 600, batch_size: 8, num_workers: 0, large_video: true };
    if (name === '4k') this.params = { max_sample_num: 800, batch_size: 4, num_workers: 0, large_video: true };
  }

  formatBytes(n: number) {
    if (!Number.isFinite(n) || n <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.min(Math.floor(Math.log(n) / Math.log(1024)), units.length - 1);
    const v = n / Math.pow(1024, i);
    const s = v >= 10 || i === 0 ? v.toFixed(0) : v.toFixed(1);
    return `${s} ${units[i]}`;
  }

  submit() {
    if (!this.file) return;
    this.loading = true;
    this.error = '';
    this.rangeWarning = '';
    const p: any = { ...this.params };

    if (this.rangeStart == null && this.rangeEnd == null) {
    } else if (this.rangeStart == null || this.rangeEnd == null) {
      this.loading = false;
      this.rangeWarning = 'Please set both start and end, or leave both empty.';
      return;
    } else if (this.rangeStart < 0 || this.rangeEnd < 0 || this.rangeEnd <= this.rangeStart) {
      this.loading = false;
      this.rangeWarning = 'Range must be positive, and End must be greater than Start.';
      return;
    } else {
      p.video_range = `${this.rangeStart},${this.rangeEnd}`;
    }

    this.api.createJob(this.file, p).subscribe({
      next: (res) => {
        this.loading = false;
        this.router.navigate(['/jobs', res.job_id]);
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail ?? 'Failed to create job';
      }
    });
  }
}