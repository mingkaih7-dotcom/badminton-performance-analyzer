import { Component, NgZone, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService, JobStatusResponse } from '../api.service';
import { Subscription, timer, switchMap } from 'rxjs';

@Component({
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="page">
      <div class="header">
        <div class="titleWrap">
          <h1>Job</h1>
          <div class="sub">This page updates automatically while the job is running.</div>
        </div>

        <div class="topActions">
          <button class="ghost" (click)="goRuns()">Runs</button>
          <button class="ghost" (click)="goUpload()">Upload</button>
          <button class="primary" [disabled]="!job?.run_id" (click)="openRun()">Result</button>

          <a
            class="pill"
            *ngIf="job?.run_id as rid"
            [href]="api.streamlitRunUrl(rid)"
            target="_blank"
            rel="noreferrer"
          >Advanced</a>
        </div>
      </div>

      <div class="card" *ngIf="job; else loadingTpl">
        <div class="topRow">
          <div class="left">
            <div class="badgeRow">
              <span class="badge" [class]="badgeClass(job.status)">{{ job.status || 'unknown' }}</span>
              <span class="dim" *ngIf="lastRefreshedText">Last update: <span class="mono">{{ lastRefreshedText }}</span></span>
            </div>

            <div class="big">
              <span class="pct">{{ clamp(job.progress) }}</span><span class="pctSign">%</span>
            </div>
            <div class="hint">Overall progress</div>

            <div class="bar">
              <div class="fill" [style.width.%]="clamp(job.progress)"></div>
            </div>

            <div class="msg" *ngIf="job.status === 'running'">Running… You can keep this page open.</div>
            <div class="msg ok" *ngIf="job.status === 'finished'">Finished. Redirecting to result…</div>
            <div class="msg err" *ngIf="job.status === 'failed'">Failed. See error below.</div>
          </div>

          <div class="right">
            <div class="kv">
              <div class="k">job_id</div>
              <div class="v">
                <span class="mono">{{ job.job_id }}</span>
                <button class="copy" (click)="copy(job.job_id)">Copy</button>
              </div>

              <div class="k">run_id</div>
              <div class="v">
                <span class="mono">{{ job.run_id || '—' }}</span>
                <button class="copy" [disabled]="!job.run_id" (click)="copy(job.run_id)">Copy</button>
              </div>

              <div class="k">updated</div>
              <div class="v">
                <div class="mono">{{ relTime(job.updated_at) }}</div>
                <div class="dim mono">{{ fmtTime(job.updated_at) }}</div>
              </div>
            </div>

            <div class="sideActions">
              <button class="pillBtn" [disabled]="!job.run_id" (click)="openRun()">Open result</button>

              <a
                class="pillBtn"
                *ngIf="job.run_id as rid2"
                [href]="api.streamlitRunUrl(rid2)"
                target="_blank"
                rel="noreferrer"
              >Open advanced</a>

              <button class="pillBtn" (click)="refreshOnce()" [disabled]="loading">Refresh now</button>
            </div>
          </div>
        </div>

        <div class="errorBox" *ngIf="job.error">
          <div class="errorTitle">Error</div>
          <div class="errorText mono">{{ job.error }}</div>
        </div>

        <div class="netErr" *ngIf="error">
          <span class="mono">{{ error }}</span>
        </div>
      </div>

      <ng-template #loadingTpl>
        <div class="card">
          <div class="skeletonTitle">Loading job…</div>
          <div class="skeletonBar"></div>
          <div class="skeletonLines">
            <div class="line"></div>
            <div class="line"></div>
            <div class="line"></div>
          </div>
        </div>
      </ng-template>
    </div>
  `,
  styles: [`
    .page{display:flex;flex-direction:column;gap:14px}
    .header{max-width:1180px;width:100%;margin:0 auto;display:flex;align-items:flex-end;justify-content:space-between;gap:12px;flex-wrap:wrap}
    .titleWrap{display:flex;flex-direction:column;gap:6px}
    h1{margin:0;font-size:30px;letter-spacing:-0.02em;color:#0f172a}
    .sub{color:#64748b;font-size:13px}

    .topActions{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
    .primary{background:#2563eb;color:#fff;border:0;border-radius:12px;padding:10px 14px;font-weight:900;cursor:pointer}
    .ghost{background:#ffffff;color:#0f172a;border:1px solid #cbd5e1;border-radius:12px;padding:10px 14px;font-weight:800;cursor:pointer}
    .pill{color:#0f172a;text-decoration:none;background:#f1f5f9;border:1px solid #e2e8f0;border-radius:999px;padding:9px 12px;font-weight:900;cursor:pointer}
    .pill:hover{border-color:#94a3b8}
    button:disabled{opacity:.55;cursor:not-allowed}

    .card{background:#ffffff;border:1px solid #e5e7eb;border-radius:18px;padding:16px;max-width:1180px;width:100%;margin:0 auto;box-shadow:0 10px 30px rgba(15,23,42,.06)}
    .topRow{display:grid;grid-template-columns:1.2fr .8fr;gap:16px;align-items:start}
    .left{display:flex;flex-direction:column;gap:10px}
    .right{display:flex;flex-direction:column;gap:12px}

    .badgeRow{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
    .badge{display:inline-flex;align-items:center;justify-content:center;border-radius:999px;padding:7px 10px;font-weight:900;font-size:12px;border:1px solid transparent}
    .b-finished{background:#ecfdf5;color:#047857;border-color:#a7f3d0}
    .b-failed{background:#fef2f2;color:#b91c1c;border-color:#fecaca}
    .b-running{background:#eff6ff;color:#1d4ed8;border-color:#bfdbfe}
    .b-unknown{background:#f1f5f9;color:#334155;border-color:#e2e8f0}

    .mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
    .dim{color:#64748b;font-size:12px}

    .big{display:flex;align-items:baseline;gap:2px}
    .pct{font-size:44px;font-weight:950;letter-spacing:-0.03em;color:#0f172a;line-height:1}
    .pctSign{font-size:18px;color:#475569;font-weight:900}
    .hint{color:#64748b;font-size:13px;font-weight:700}

    .bar{height:12px;background:#f1f5f9;border:1px solid #e2e8f0;border-radius:999px;overflow:hidden}
    .fill{height:100%;background:#2563eb}

    .msg{color:#334155;font-weight:800;font-size:13px}
    .msg.ok{color:#047857}
    .msg.err{color:#b91c1c}

    .kv{display:grid;grid-template-columns:90px 1fr;gap:10px 12px;border:1px solid #e2e8f0;border-radius:14px;padding:12px;background:#f8fafc}
    .k{color:#64748b;font-size:12px;font-weight:900}
    .v{color:#0f172a;font-weight:800;word-break:break-all;display:flex;align-items:center;gap:10px;flex-wrap:wrap}

    .copy{background:#ffffff;border:1px solid #cbd5e1;border-radius:999px;padding:6px 10px;font-weight:900;color:#0f172a;cursor:pointer}
    .copy:hover{border-color:#94a3b8}

    .sideActions{display:flex;gap:10px;flex-wrap:wrap;justify-content:flex-start}
    .pillBtn{background:#ffffff;color:#0f172a;border:1px solid #cbd5e1;border-radius:999px;padding:9px 12px;font-weight:900;cursor:pointer;text-decoration:none}
    .pillBtn:hover{border-color:#94a3b8}

    .errorBox{margin-top:14px;border:1px solid #fecaca;background:#fef2f2;border-radius:16px;padding:12px}
    .errorTitle{font-weight:950;color:#991b1b;margin-bottom:6px}
    .errorText{color:#7f1d1d;font-weight:800;white-space:pre-wrap}

    .netErr{margin-top:12px;color:#b45309;font-weight:900}

    .skeletonTitle{font-weight:950;color:#0f172a;margin-bottom:12px}
    .skeletonBar{height:12px;border-radius:999px;background:#e2e8f0;overflow:hidden;position:relative}
    .skeletonBar:after{content:'';position:absolute;inset:0;background:linear-gradient(90deg, rgba(226,232,240,0) 0%, rgba(255,255,255,.9) 50%, rgba(226,232,240,0) 100%);transform:translateX(-100%);animation:shimmer 1.2s infinite}
    .skeletonLines{margin-top:12px;display:flex;flex-direction:column;gap:8px}
    .line{height:12px;border-radius:8px;background:#e2e8f0;position:relative;overflow:hidden}
    .line:after{content:'';position:absolute;inset:0;background:linear-gradient(90deg, rgba(226,232,240,0) 0%, rgba(255,255,255,.9) 50%, rgba(226,232,240,0) 100%);transform:translateX(-100%);animation:shimmer 1.2s infinite}

    @keyframes shimmer{to{transform:translateX(100%)}}

    @media (max-width: 980px){
      .topRow{grid-template-columns:1fr}
      .topActions{justify-content:flex-start}
    }
  `]
})
export class JobPageComponent implements OnDestroy {
  sub?: Subscription;
  job?: JobStatusResponse;
  loading = false;
  error = '';
  lastRefreshedText = '';
  private jobId = '';

  constructor(
    private route: ActivatedRoute,
    public api: ApiService,
    private router: Router,
    private zone: NgZone
  ) {
    this.jobId = this.route.snapshot.paramMap.get('jobId') || '';
    if (!this.jobId) {
      this.error = 'Missing jobId';
      return;
    }

    this.sub = timer(0, 1200).pipe(
      switchMap(() => this.api.getJob(this.jobId))
    ).subscribe({
      next: (j) => {
        this.zone.run(() => {
          this.job = j;
          this.loading = false;
          this.error = '';
          this.lastRefreshedText = new Date().toLocaleTimeString();

          if (j.status === 'finished') {
            this.sub?.unsubscribe();
            this.router.navigate(['/runs', j.run_id]);
            return;
          }
          if (j.status === 'failed') {
            this.sub?.unsubscribe();
          }
        });
      },
      error: (e) => {
        this.zone.run(() => {
          this.loading = false;
          this.error = e?.error?.detail ?? e?.message ?? 'Network error';
        });
      }
    });
  }

  ngOnDestroy() {
    this.sub?.unsubscribe();
  }

  refreshOnce() {
    if (!this.jobId) return;
    this.loading = true;
    this.api.getJob(this.jobId).subscribe({
      next: (j) => {
        this.zone.run(() => {
          this.job = j;
          this.loading = false;
          this.error = '';
          this.lastRefreshedText = new Date().toLocaleTimeString();
        });
      },
      error: (e) => {
        this.zone.run(() => {
          this.loading = false;
          this.error = e?.error?.detail ?? e?.message ?? 'Network error';
        });
      }
    });
  }

  goRuns() {
    this.router.navigate(['/runs-list']);
  }

  goUpload() {
    this.router.navigate(['/upload']);
  }

  openRun() {
    if (!this.job?.run_id) return;
    this.router.navigate(['/runs', this.job.run_id]);
  }

  clamp(p: number) {
    const x = Number.isFinite(p) ? p : 0;
    return Math.max(0, Math.min(100, Math.round(x)));
  }

  badgeClass(status: string) {
    const s = (status ?? '').toLowerCase();
    if (s.includes('finish') || s === 'done' || s === 'success') return 'b-finished';
    if (s.includes('fail') || s.includes('error')) return 'b-failed';
    if (s.includes('run') || s.includes('process') || s.includes('queue') || s.includes('start')) return 'b-running';
    return 'b-unknown';
  }

  async copy(text?: string) {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      try {
        (window as any).prompt('Copy:', text);
      } catch {}
    }
  }

  parseTime(s: string) {
    if (!s) return null;
    const d = new Date(s);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  fmtTime(s: string) {
    const d = this.parseTime(s);
    return d ? d.toLocaleString() : '—';
  }

  relTime(s: string) {
    const d = this.parseTime(s);
    if (!d) return '—';
    const ms = Date.now() - d.getTime();
    const sec = Math.floor(ms / 1000);
    if (sec < 10) return 'just now';
    if (sec < 60) return `${sec}s ago`;
    const min = Math.floor(sec / 60);
    if (min < 60) return `${min}m ago`;
    const hr = Math.floor(min / 60);
    if (hr < 24) return `${hr}h ago`;
    const day = Math.floor(hr / 24);
    return `${day}d ago`;
  }
}