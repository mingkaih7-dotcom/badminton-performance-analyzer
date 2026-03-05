import { AfterViewInit, Component, ElementRef, OnDestroy, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService, RunInfoResponse, AnalyticsResponse } from '../api.service';
import * as Plotly from 'plotly.js-dist-min';

@Component({
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="page">
      <div class="header">
        <div class="titleWrap">
          <h1>Result</h1>
          <div class="sub">View overlay video, key charts, and download artifacts.</div>
        </div>

        <div class="topActions">
          <button class="ghost" (click)="goRuns()">Runs</button>
          <button class="ghost" (click)="goUpload()">Upload</button>
          <a class="pill" *ngIf="runId" [href]="streamlitUrl" target="_blank" rel="noreferrer">Advanced</a>
        </div>
      </div>

      <div class="card">
        <div class="summary">
          <div class="left">
            <div class="badgeRow">
              <span class="badge" [class]="badgeClass(run?.status)">{{ run?.status || (loadingRun ? 'loading' : 'unknown') }}</span>
              <span class="dim" *ngIf="run?.updated_at as upd">Updated: <span class="mono">{{ fmtTime(upd) }}</span></span>
            </div>

            <div class="idRow">
              <div class="idLabel">run_id</div>
              <div class="idValue mono">{{ runId }}</div>
              <button class="copy" [disabled]="!runId" (click)="copy(runId)">Copy</button>
            </div>

            <div class="miniGrid" *ngIf="run as r">
              <div class="mini">
                <div class="k">Created</div>
                <div class="v mono">{{ fmtTime(r.created_at) }}</div>
              </div>
              <div class="mini">
                <div class="k">Updated</div>
                <div class="v mono">{{ fmtTime(r.updated_at) }}</div>
              </div>
              <div class="mini" *ngIf="analytics?.fps">
                <div class="k">FPS</div>
                <div class="v mono">{{ analytics?.fps }}</div>
              </div>
              <div class="mini" *ngIf="analytics?.meta">
                <div class="k">Points / Events</div>
                <div class="v mono">{{ analytics?.meta?.n_points ?? 0 }} / {{ analytics?.meta?.n_events ?? 0 }}</div>
              </div>
            </div>

            <div class="err" *ngIf="error">{{ error }}</div>
          </div>

          <div class="right">
            <div class="dlBlock">
              <div class="dlTitle">Downloads</div>
              <div class="dlRow">
                <a class="chip" *ngIf="hasArtifact('overlay')" [href]="artifactUrl('overlay')" target="_blank">Overlay video</a>
                <a class="chip" *ngIf="hasArtifact('heatmap')" [href]="artifactUrl('heatmap')" target="_blank">Heatmap</a>
                <a class="chip" *ngIf="hasArtifact('events_csv')" [href]="artifactUrl('events_csv')" target="_blank">Events CSV</a>
                <a class="chip" *ngIf="hasArtifact('shuttle_csv')" [href]="artifactUrl('shuttle_csv')" target="_blank">Shuttle CSV</a>
                <a class="chip" *ngIf="hasArtifact('metrics_json')" [href]="artifactUrl('metrics_json')" target="_blank">Metrics JSON</a>
              </div>

              <button class="link" type="button" (click)="allDownloadsOpen = !allDownloadsOpen">
                {{ allDownloadsOpen ? 'Hide' : 'Show' }} all artifacts
              </button>

              <div class="allDl" *ngIf="allDownloadsOpen">
                <a class="chip subtle" *ngFor="let a of artifactEntries" [href]="a.url" target="_blank">{{ a.name }}</a>
              </div>
            </div>
          </div>
        </div>

        <div class="section">
          <div class="sectionTitle">Overlay</div>
          <div class="videoWrap" *ngIf="overlayUrl; else noOverlayTpl">
            <video controls [src]="overlayUrl" class="video"></video>
          </div>
          <ng-template #noOverlayTpl>
            <div class="emptyBox">Overlay not available for this run.</div>
          </ng-template>
        </div>

        <div class="section">
          <div class="sectionTitleRow">
            <div class="sectionTitle">Analytics</div>
            <div class="dim" *ngIf="analyticsMsg">{{ analyticsMsg }}</div>
          </div>

          <div class="grid2">
            <div class="panel">
              <div class="ptitle">Trajectory</div>
              <div #traj class="plot"></div>
              <div class="pHint" *ngIf="trajHint">{{ trajHint }}</div>
            </div>

            <div class="panel">
              <div class="ptitle">Hits per second</div>
              <div #timeline class="plot"></div>
              <div class="pHint" *ngIf="timelineHint">{{ timelineHint }}</div>
            </div>
          </div>
        </div>

        <div class="section">
          <button class="link" type="button" (click)="techOpen = !techOpen">
            {{ techOpen ? 'Hide' : 'Show' }} technical details
          </button>

          <div class="tech" *ngIf="techOpen">
            <div class="techGrid" *ngIf="run as r">
              <div class="techBox">
                <div class="techTitle">Metrics</div>
                <pre class="pre">{{ r.metrics | json }}</pre>
              </div>

              <div class="techBox">
                <div class="techTitle">Params</div>
                <pre class="pre">{{ r.params | json }}</pre>
              </div>

              <div class="techBox span2">
                <div class="techTitle">Logs</div>
                <div class="techActions">
                  <button class="ghostSmall" (click)="loadLogs()" [disabled]="loadingLogs">{{ loadingLogs ? 'Loading…' : 'Load logs' }}</button>
                </div>
                <pre class="pre">{{ logs }}</pre>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  `,
  styles: [`
    .page{display:flex;flex-direction:column;gap:14px}
    .header{max-width:1180px;width:100%;margin:0 auto;display:flex;align-items:flex-end;justify-content:space-between;gap:12px;flex-wrap:wrap}
    .titleWrap{display:flex;flex-direction:column;gap:6px}
    h1{margin:0;font-size:30px;letter-spacing:-0.02em;color:#0f172a}
    .sub{color:#64748b;font-size:13px}

    .topActions{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
    .ghost{background:#ffffff;color:#0f172a;border:1px solid #cbd5e1;border-radius:12px;padding:10px 14px;font-weight:800;cursor:pointer}
    .pill{color:#0f172a;text-decoration:none;background:#f1f5f9;border:1px solid #e2e8f0;border-radius:999px;padding:9px 12px;font-weight:900;cursor:pointer}
    .pill:hover{border-color:#94a3b8}

    .card{background:#ffffff;border:1px solid #e5e7eb;border-radius:18px;padding:16px;max-width:1180px;width:100%;margin:0 auto;box-shadow:0 10px 30px rgba(15,23,42,.06)}

    .summary{display:grid;grid-template-columns:1.25fr .75fr;gap:14px;align-items:start}
    .left{display:flex;flex-direction:column;gap:12px}
    .right{display:flex;flex-direction:column;gap:12px}

    .badgeRow{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
    .badge{display:inline-flex;align-items:center;justify-content:center;border-radius:999px;padding:7px 10px;font-weight:900;font-size:12px;border:1px solid transparent}
    .b-finished{background:#ecfdf5;color:#047857;border-color:#a7f3d0}
    .b-failed{background:#fef2f2;color:#b91c1c;border-color:#fecaca}
    .b-running{background:#eff6ff;color:#1d4ed8;border-color:#bfdbfe}
    .b-unknown{background:#f1f5f9;color:#334155;border-color:#e2e8f0}

    .mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
    .dim{color:#64748b;font-size:12px}
    .err{color:#b91c1c;font-weight:800}

    .idRow{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
    .idLabel{color:#64748b;font-size:12px;font-weight:900}
    .idValue{font-weight:900;color:#0f172a;word-break:break-all}
    .copy{background:#ffffff;border:1px solid #cbd5e1;border-radius:999px;padding:7px 10px;font-weight:900;color:#0f172a;cursor:pointer}
    .copy:hover{border-color:#94a3b8}
    button:disabled{opacity:.55;cursor:not-allowed}

    .miniGrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
    .mini{border:1px solid #e2e8f0;background:#f8fafc;border-radius:14px;padding:10px}
    .mini .k{color:#64748b;font-size:12px;font-weight:900}
    .mini .v{color:#0f172a;font-weight:900;margin-top:6px}

    .dlBlock{border:1px solid #e2e8f0;background:#f8fafc;border-radius:14px;padding:12px}
    .dlTitle{font-weight:950;color:#0f172a;margin-bottom:10px}
    .dlRow{display:flex;flex-wrap:wrap;gap:10px}
    .chip{color:#0f172a;text-decoration:none;background:#ffffff;border:1px solid #cbd5e1;border-radius:999px;padding:8px 12px;font-weight:900}
    .chip:hover{border-color:#94a3b8}
    .chip.subtle{background:#f1f5f9}
    .allDl{margin-top:10px;display:flex;flex-wrap:wrap;gap:10px}

    .link{background:transparent;border:0;color:#475569;font-weight:900;cursor:pointer;padding:8px 4px}
    .link:hover{color:#0f172a}

    .section{margin-top:16px}
    .sectionTitle{font-weight:950;color:#0f172a;margin-bottom:10px}
    .sectionTitleRow{display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:10px}

    .videoWrap{border:1px solid #e2e8f0;border-radius:16px;background:#0b0f17;overflow:hidden}
    .video{width:100%;max-height:560px;display:block;background:#000}

    .emptyBox{border:1px dashed #cbd5e1;border-radius:16px;background:#f8fafc;padding:14px;color:#64748b;font-weight:800}

    .grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
    .panel{border:1px solid #e2e8f0;border-radius:16px;background:#ffffff;padding:12px}
    .ptitle{color:#475569;font-size:12px;font-weight:950;margin-bottom:8px}
    .plot{width:100%;height:360px}
    .pHint{margin-top:8px;color:#b45309;font-weight:900;font-size:12px}

    .tech{margin-top:10px}
    .techGrid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
    .techBox{border:1px solid #e2e8f0;border-radius:16px;background:#f8fafc;padding:12px}
    .techTitle{font-weight:950;color:#0f172a;margin-bottom:10px}
    .techActions{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px}
    .ghostSmall{background:#ffffff;color:#0f172a;border:1px solid #cbd5e1;border-radius:12px;padding:8px 12px;font-weight:900;cursor:pointer}
    .ghostSmall:hover{border-color:#94a3b8}
    .pre{background:#ffffff;border:1px solid #e2e8f0;border-radius:14px;padding:12px;overflow:auto;max-height:280px}

    .span2{grid-column:1 / -1}

    @media (max-width: 980px){
      .summary{grid-template-columns:1fr}
      .grid2{grid-template-columns:1fr}
      .plot{height:320px}
      .techGrid{grid-template-columns:1fr}
      .miniGrid{grid-template-columns:1fr}
    }
  `]
})
export class RunPageComponent implements AfterViewInit, OnDestroy {
  runId = '';
  run?: RunInfoResponse;
  analytics?: AnalyticsResponse;

  loadingRun = false;
  error = '';

  overlayUrl = '';
  streamlitUrl = '';

  artifactEntries: Array<{ name: string; url: string }> = [];
  artifacts: Record<string, string> = {};

  analyticsMsg = '';
  trajHint = '';
  timelineHint = '';

  techOpen = false;
  logs = '';
  loadingLogs = false;

  allDownloadsOpen = false;

  private viewReady = false;
  private plotted = false;
  private resizeHandler = () => this.onResize();

  @ViewChild('traj', { static: true }) trajEl!: ElementRef<HTMLDivElement>;
  @ViewChild('timeline', { static: true }) timelineEl!: ElementRef<HTMLDivElement>;

  constructor(private route: ActivatedRoute, private api: ApiService, private router: Router) {
    this.runId = this.route.snapshot.paramMap.get('runId') || '';
    this.streamlitUrl = this.api.streamlitRunUrl(this.runId);
    this.loadRun();
    window.addEventListener('resize', this.resizeHandler);
  }

  ngAfterViewInit() {
    this.viewReady = true;
    this.tryRenderPlots();
  }

  ngOnDestroy() {
    window.removeEventListener('resize', this.resizeHandler);
  }

  goRuns() {
    this.router.navigate(['/runs-list']);
  }

  goUpload() {
    this.router.navigate(['/upload']);
  }

  artifactUrl(name: string) {
    return this.api.artifactUrl(this.runId, name);
  }

  hasArtifact(name: string) {
    return !!this.artifacts?.[name];
  }

  badgeClass(status?: string) {
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

  loadRun() {
    if (!this.runId) {
      this.error = 'Missing runId';
      return;
    }
    this.loadingRun = true;
    this.error = '';
    this.api.getRun(this.runId).subscribe({
      next: (r) => {
        this.run = r;
        this.loadingRun = false;

        this.artifacts = r.artifacts || {};
        this.artifactEntries = Object.keys(this.artifacts).map(k => ({ name: k, url: this.api.artifactUrl(this.runId, k) }));

        this.overlayUrl = this.artifacts['overlay'] ? this.api.artifactUrl(this.runId, 'overlay') : '';
        this.loadAnalytics();
      },
      error: (e) => {
        this.loadingRun = false;
        this.error = e?.error?.detail ?? e?.message ?? 'Failed to load run';
      }
    });
  }

  loadAnalytics() {
    this.analyticsMsg = 'Loading analytics…';
    this.trajHint = '';
    this.timelineHint = '';
    this.api.getAnalytics(this.runId).subscribe({
      next: (a) => {
        this.analytics = a;
        this.analyticsMsg = '';
        this.tryRenderPlots();
      },
      error: () => {
        this.analyticsMsg = 'Failed to load analytics';
      }
    });
  }

  loadLogs() {
    if (this.loadingLogs) return;
    this.loadingLogs = true;
    this.api.getLogs(this.runId).subscribe({
      next: (x) => {
        this.logs = x.text || '';
        this.loadingLogs = false;
      },
      error: () => {
        this.logs = 'Failed to load logs';
        this.loadingLogs = false;
      }
    });
  }

  tryRenderPlots() {
    if (!this.viewReady || !this.analytics) return;
    setTimeout(() => {
      this.renderTrajectory();
      this.renderTimeline();
      this.plotted = true;
      this.onResize();
    }, 0);
  }

  renderTrajectory() {
    const tr = this.analytics?.trajectory || {};
    const x = tr.x || [];
    const y = tr.y || [];

    if (!x.length || !y.length) {
      Plotly.purge(this.trajEl.nativeElement);
      this.trajHint = 'No trajectory points available';
      return;
    }

    this.trajHint = '';
    const data: any = [{ x, y, type: 'scatter', mode: 'lines' }];
    const layout: any = {
      margin: { l: 44, r: 10, t: 10, b: 42 },
      xaxis: { title: 'X (px)' },
      yaxis: { title: 'Y (px)', autorange: 'reversed' },
      showlegend: false
    };
    Plotly.react(this.trajEl.nativeElement, data, layout, { displayModeBar: false, responsive: true });
  }

  renderTimeline() {
    const tl = this.analytics?.timeline || {};
    const x = tl.x || [];
    const y = tl.y || [];

    if (!x.length || !y.length) {
      Plotly.purge(this.timelineEl.nativeElement);
      this.timelineHint = 'No events available';
      return;
    }

    this.timelineHint = '';
    const data: any = [{ x, y, type: 'bar' }];
    const layout: any = {
      margin: { l: 44, r: 10, t: 10, b: 42 },
      xaxis: { title: 'Time (s)' },
      yaxis: { title: 'Hits' },
      showlegend: false
    };
    Plotly.react(this.timelineEl.nativeElement, data, layout, { displayModeBar: false, responsive: true });
  }

  onResize() {
    if (!this.plotted) return;
    try {
      (Plotly as any).Plots.resize(this.trajEl.nativeElement);
      (Plotly as any).Plots.resize(this.timelineEl.nativeElement);
    } catch {}
  }
}