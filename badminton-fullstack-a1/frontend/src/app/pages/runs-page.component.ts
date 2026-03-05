import { Component, DestroyRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService, RunSummaryResponse } from '../api.service';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Subscription, timer } from 'rxjs';
import { switchMap } from 'rxjs/operators';

type StatusFilter = 'all' | 'finished' | 'failed' | 'running' | 'unknown';

@Component({
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page">
      <div class="header">
        <div class="titleWrap">
          <h1>Runs</h1>
          <div class="sub">Browse completed analyses. Use search and filters to quickly locate a run.</div>
        </div>

        <div class="toolbar">
          <div class="left">
            <button class="primary" (click)="refresh()" [disabled]="loading || deletingAll">
              <span *ngIf="!loading">Refresh</span>
              <span *ngIf="loading">Loading…</span>
            </button>

            <label class="toggle">
              <input type="checkbox" [(ngModel)]="autoRefresh" (change)="onAutoRefreshChange()" [disabled]="deletingAll" />
              <span>Auto refresh</span>
            </label>

            <div class="meta" *ngIf="lastRefreshedText">
              Last: <span class="mono">{{ lastRefreshedText }}</span>
            </div>
          </div>

          <div class="right">
            <div class="field">
              <div class="k">Limit</div>
              <select [(ngModel)]="limit" (change)="refresh()" [disabled]="deletingAll">
                <option [ngValue]="20">20</option>
                <option [ngValue]="50">50</option>
                <option [ngValue]="200">200</option>
              </select>
            </div>

            <div class="field">
              <div class="k">Status</div>
              <select [(ngModel)]="statusFilter" (ngModelChange)="applyFilterSort()" [disabled]="deletingAll">
                <option value="all">All</option>
                <option value="finished">Finished</option>
                <option value="failed">Failed</option>
                <option value="running">Running</option>
                <option value="unknown">Other</option>
              </select>
            </div>

            <div class="search">
              <div class="k">Search</div>
              <input
                type="text"
                placeholder="Search run_id…"
                [(ngModel)]="query"
                (ngModelChange)="applyFilterSort()"
                [disabled]="deletingAll"
              />
            </div>
          </div>
        </div>

        <div class="notice err" *ngIf="error">{{ error }}</div>
      </div>

      <div class="card">
        <div class="summary">
          <div class="count">
            Showing <span class="mono">{{ viewRuns.length }}</span> of <span class="mono">{{ runs.length }}</span>
          </div>
          <div class="summaryActions">
            <button class="ghost" (click)="goUpload()" [disabled]="deletingAll">Upload new video</button>
            <button class="danger" (click)="deleteAll()" [disabled]="deletingAll || runs.length === 0">
              <span *ngIf="!deletingAll">Delete all</span>
              <span *ngIf="deletingAll">Deleting…</span>
            </button>
          </div>
        </div>

        <div class="table" *ngIf="viewRuns.length > 0">
          <div class="row head">
            <div>Run</div>
            <div>Status</div>
            <div>Updated</div>
            <div class="rightAlign">Actions</div>
          </div>

          <div class="row" *ngFor="let r of viewRuns">
            <div class="runCell">
              <button class="runLink" (click)="openRun(r.run_id)">{{ shortId(r.run_id) }}</button>
              <button class="copy" (click)="copyId(r.run_id)" title="Copy run_id">Copy</button>
              <div class="fullId mono">{{ r.run_id }}</div>
            </div>

            <div>
              <span class="badge" [class]="badgeClass(r.status)">{{ r.status || 'unknown' }}</span>
            </div>

            <div class="time">
              <div class="mono">{{ relTime(r.updated_at) }}</div>
              <div class="dim mono">{{ fmtTime(r.updated_at) }}</div>
            </div>

            <div class="actions rightAlign">
              <button class="pill" (click)="openRun(r.run_id)">Result</button>
              <a class="pill" [href]="api.streamlitRunUrl(r.run_id)" target="_blank" rel="noreferrer">Advanced</a>
              <button
                class="pill dangerPill"
                (click)="deleteOne(r)"
                [disabled]="deletingAll || isDeleting(r.run_id) || !canDeleteStatus(r.status)"
              >
                <span *ngIf="!isDeleting(r.run_id)">Delete</span>
                <span *ngIf="isDeleting(r.run_id)">Deleting…</span>
              </button>
            </div>
          </div>
        </div>

        <div class="empty" *ngIf="!loading && viewRuns.length === 0 && !error">
          <div class="emptyTitle">No runs found</div>
          <div class="emptySub">Try changing filters or upload a new video.</div>
          <div class="emptyActions">
            <button class="primary" (click)="goUpload()">Upload</button>
            <button class="ghost" (click)="resetFilters()">Reset filters</button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .page{display:flex;flex-direction:column;gap:14px}
    .header{max-width:1180px;width:100%;margin:0 auto;display:flex;flex-direction:column;gap:12px}
    .titleWrap{display:flex;flex-direction:column;gap:6px}
    h1{margin:0;font-size:30px;letter-spacing:-0.02em;color:#0f172a}
    .sub{color:#64748b;font-size:13px}

    .toolbar{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;flex-wrap:wrap}
    .left{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
    .right{display:flex;align-items:flex-end;gap:10px;flex-wrap:wrap}

    .primary{background:#2563eb;color:#fff;border:0;border-radius:12px;padding:10px 14px;font-weight:900;cursor:pointer}
    .ghost{background:#ffffff;color:#0f172a;border:1px solid #cbd5e1;border-radius:12px;padding:10px 14px;font-weight:800;cursor:pointer}
    .danger{background:#dc2626;color:#fff;border:0;border-radius:12px;padding:10px 14px;font-weight:900;cursor:pointer}
    .danger:disabled{opacity:.55;cursor:not-allowed}
    button:disabled{opacity:.55;cursor:not-allowed}

    .toggle{display:flex;align-items:center;gap:8px;color:#334155;font-size:13px;font-weight:700}
    .toggle input{width:16px;height:16px}

    .meta{color:#64748b;font-size:12px}
    .mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
    .dim{color:#94a3b8}

    .field{display:flex;flex-direction:column;gap:6px}
    .k{font-size:11px;color:#64748b;font-weight:800}
    select,input{background:#ffffff;color:#0f172a;border:1px solid #cbd5e1;border-radius:12px;padding:10px 12px;outline:none}
    input:focus,select:focus{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.15)}
    .search{display:flex;flex-direction:column;gap:6px;min-width:280px}

    .notice{max-width:1180px;margin:0 auto}
    .err{color:#b91c1c;font-weight:700}

    .card{background:#ffffff;border:1px solid #e5e7eb;border-radius:18px;padding:16px;max-width:1180px;width:100%;margin:0 auto;box-shadow:0 10px 30px rgba(15,23,42,.06)}
    .summary{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px;flex-wrap:wrap}
    .count{color:#334155;font-weight:800}
    .summaryActions{display:flex;gap:10px;flex-wrap:wrap}

    .table{display:flex;flex-direction:column;border:1px solid #e2e8f0;border-radius:14px;overflow:hidden}
    .row{display:grid;grid-template-columns: 1.2fr 140px 220px 320px;gap:12px;padding:12px 14px;border-top:1px solid #e2e8f0;align-items:center}
    .row.head{border-top:0;background:#f8fafc;color:#64748b;font-size:12px;font-weight:900}
    .rightAlign{justify-self:end;text-align:right}

    .runCell{display:flex;flex-direction:column;gap:6px}
    .runLink{background:transparent;border:0;padding:0;margin:0;cursor:pointer;color:#1d4ed8;font-weight:900;text-align:left}
    .runLink:hover{text-decoration:underline}
    .copy{width:fit-content;background:#f1f5f9;border:1px solid #e2e8f0;border-radius:999px;padding:6px 10px;font-weight:900;color:#0f172a;cursor:pointer}
    .copy:hover{border-color:#94a3b8}
    .fullId{font-size:12px;color:#94a3b8;word-break:break-all}

    .badge{display:inline-flex;align-items:center;justify-content:center;border-radius:999px;padding:7px 10px;font-weight:900;font-size:12px;border:1px solid transparent}
    .b-finished{background:#ecfdf5;color:#047857;border-color:#a7f3d0}
    .b-failed{background:#fef2f2;color:#b91c1c;border-color:#fecaca}
    .b-running{background:#eff6ff;color:#1d4ed8;border-color:#bfdbfe}
    .b-unknown{background:#f1f5f9;color:#334155;border-color:#e2e8f0}

    .time{display:flex;flex-direction:column;gap:4px}

    .actions{display:flex;gap:10px;flex-wrap:wrap;justify-content:flex-end}
    .pill{color:#0f172a;text-decoration:none;background:#f1f5f9;border:1px solid #e2e8f0;border-radius:999px;padding:7px 12px;font-weight:900;cursor:pointer}
    .pill:hover{border-color:#94a3b8}
    .dangerPill{background:#fee2e2;border-color:#fecaca;color:#b91c1c}
    .dangerPill:hover{border-color:#fca5a5}

    .empty{display:flex;flex-direction:column;gap:10px;align-items:flex-start;padding:18px;border:1px dashed #cbd5e1;border-radius:16px;background:#f8fafc}
    .emptyTitle{font-weight:900;color:#0f172a}
    .emptySub{color:#64748b;font-size:13px}
    .emptyActions{display:flex;gap:10px;flex-wrap:wrap}

    @media (max-width: 980px){
      .row{grid-template-columns: 1fr;gap:8px}
      .rightAlign{justify-self:start;text-align:left}
      .actions{justify-content:flex-start}
      .search{min-width:220px}
    }
  `]
})
export class RunsPageComponent {
  api: ApiService;
  private router: Router;
  private destroyRef = inject(DestroyRef);

  runs: RunSummaryResponse[] = [];
  viewRuns: RunSummaryResponse[] = [];
  loading = false;
  error = '';

  query = '';
  statusFilter: StatusFilter = 'all';
  limit = 200;

  autoRefresh = false;
  private autoSub: Subscription | null = null;
  lastRefreshedText = '';

  deletingAll = false;
  private deletingSet = new Set<string>();

  constructor(api: ApiService, router: Router) {
    this.api = api;
    this.router = router;
    this.refresh();
  }

  refresh() {
    this.loading = true;
    this.error = '';
    this.api.listRuns(this.limit).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (rows) => {
        this.runs = Array.isArray(rows) ? rows : [];
        this.loading = false;
        this.lastRefreshedText = new Date().toLocaleTimeString();
        this.applyFilterSort();
      },
      error: (e) => {
        this.loading = false;
        this.error = e?.error?.detail ?? e?.message ?? 'Failed to load runs';
      }
    });
  }

  onAutoRefreshChange() {
    if (this.autoRefresh) {
      this.autoSub?.unsubscribe();
      this.autoSub = timer(0, 5000).pipe(
        switchMap(() => this.api.listRuns(this.limit))
      ).subscribe({
        next: (rows) => {
          this.runs = Array.isArray(rows) ? rows : [];
          this.lastRefreshedText = new Date().toLocaleTimeString();
          this.applyFilterSort();
        },
        error: () => {}
      });
      this.destroyRef.onDestroy(() => this.autoSub?.unsubscribe());
    } else {
      this.autoSub?.unsubscribe();
      this.autoSub = null;
    }
  }

  deleteOne(r: RunSummaryResponse) {
    const runId = r.run_id;
    if (!runId) return;
    if (!this.canDeleteStatus(r.status)) {
      this.error = 'This run is active. Please wait until it finishes.';
      return;
    }
    const ok = confirm(`Delete run ${runId}?\nThis cannot be undone.`);
    if (!ok) return;

    this.deletingSet.add(runId);
    this.error = '';
    this.api.deleteRun(runId, false).subscribe({
      next: () => {
        this.deletingSet.delete(runId);
        this.runs = this.runs.filter(x => x.run_id !== runId);
        this.applyFilterSort();
      },
      error: (e) => {
        this.deletingSet.delete(runId);
        this.error = e?.error?.detail ?? e?.message ?? 'Failed to delete run';
      }
    });
  }

  deleteAll() {
    const ok = confirm('Delete ALL runs?\nThis cannot be undone.');
    if (!ok) return;

    this.deletingAll = true;
    this.error = '';
    this.api.deleteAllRuns(true, false).subscribe({
      next: (res) => {
        this.deletingAll = false;
        this.refresh();
        if (res?.skipped?.length) {
          this.error = `Some runs were skipped because they are active: ${res.skipped.length}`;
        }
        if (res?.failed && Object.keys(res.failed).length) {
          this.error = `Some runs failed to delete: ${Object.keys(res.failed).length}`;
        }
      },
      error: (e) => {
        this.deletingAll = false;
        this.error = e?.error?.detail ?? e?.message ?? 'Failed to delete all runs';
      }
    });
  }

  isDeleting(runId: string) {
    return this.deletingSet.has(runId);
  }

  canDeleteStatus(status: string) {
    const s = (status ?? '').toLowerCase();
    return !(s.includes('queue') || s.includes('run') || s.includes('process') || s.includes('start'));
  }

  applyFilterSort() {
    const q = (this.query ?? '').trim().toLowerCase();
    const f = this.statusFilter;

    let out = [...this.runs];

    if (f !== 'all') {
      out = out.filter(r => {
        const s = (r.status ?? '').toLowerCase();
        if (f === 'finished') return s.includes('finish') || s === 'done' || s === 'success';
        if (f === 'failed') return s.includes('fail') || s === 'error';
        if (f === 'running') return s.includes('run') || s.includes('process') || s.includes('queue') || s.includes('start');
        return !(s.includes('finish') || s.includes('done') || s.includes('success') || s.includes('fail') || s.includes('error') || s.includes('run') || s.includes('process') || s.includes('queue') || s.includes('start'));
      });
    }

    if (q) out = out.filter(r => (r.run_id ?? '').toLowerCase().includes(q));

    out.sort((a, b) => {
      const ta = this.parseTime(a.updated_at)?.getTime() ?? 0;
      const tb = this.parseTime(b.updated_at)?.getTime() ?? 0;
      return tb - ta;
    });

    this.viewRuns = out;
  }

  resetFilters() {
    this.query = '';
    this.statusFilter = 'all';
    this.applyFilterSort();
  }

  openRun(runId: string) {
    this.router.navigate(['/runs', runId]);
  }

  goUpload() {
    this.router.navigate(['/upload']);
  }

  async copyId(id: string) {
    try {
      await navigator.clipboard.writeText(id);
    } catch {
      try {
        (window as any).prompt('Copy run_id:', id);
      } catch {}
    }
  }

  shortId(id: string) {
    if (!id) return '—';
    if (id.length <= 18) return id;
    return `${id.slice(0, 10)}…${id.slice(-6)}`;
  }

  badgeClass(status: string) {
    const s = (status ?? '').toLowerCase();
    if (s.includes('finish') || s === 'done' || s === 'success') return 'b-finished';
    if (s.includes('fail') || s.includes('error')) return 'b-failed';
    if (s.includes('run') || s.includes('process') || s.includes('queue') || s.includes('start')) return 'b-running';
    return 'b-unknown';
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