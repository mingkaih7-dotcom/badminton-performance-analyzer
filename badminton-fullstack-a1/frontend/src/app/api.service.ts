import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../environments/environment';
import { Observable } from 'rxjs';

export type CreateJobResponse = { job_id: string; run_id: string };
export type JobStatusResponse = { job_id: string; run_id: string; status: string; progress: number; error?: string | null; updated_at: string };
export type RunInfoResponse = { run_id: string; status: string; created_at: string; updated_at: string; artifacts: Record<string,string>; metrics: any; params: any };
export type RunSummaryResponse = { run_id: string; status: string; created_at: string; updated_at: string };
export type AnalyticsResponse = { run_id: string; fps: number; trajectory: any; timeline: any; meta: any };
export type DeleteRunResponse = { ok: boolean; run_id: string };
export type DeleteAllRunsResponse = { ok: boolean; deleted: string[]; skipped: string[]; failed: Record<string, string> };

@Injectable({ providedIn: 'root' })
export class ApiService {
  base = environment.apiBaseUrl;
  streamlitBase = environment.streamlitBaseUrl;
  constructor(private http: HttpClient) {}

  createJob(file: File, params: any): Observable<CreateJobResponse> {
    const fd = new FormData();
    fd.append('video', file);
    fd.append('params', JSON.stringify(params ?? {}));
    return this.http.post<CreateJobResponse>(`${this.base}/jobs`, fd);
  }

  getJob(jobId: string): Observable<JobStatusResponse> {
    return this.http.get<JobStatusResponse>(`${this.base}/jobs/${jobId}`);
  }

  listRuns(limit: number = 50): Observable<RunSummaryResponse[]> {
    return this.http.get<RunSummaryResponse[]>(`${this.base}/runs?limit=${limit}`);
  }

  getRun(runId: string): Observable<RunInfoResponse> {
    return this.http.get<RunInfoResponse>(`${this.base}/runs/${runId}`);
  }

  getAnalytics(runId: string): Observable<AnalyticsResponse> {
    return this.http.get<AnalyticsResponse>(`${this.base}/runs/${runId}/analytics`);
  }

  getLogs(runId: string): Observable<{ text: string }> {
    return this.http.get<{ text: string }>(`${this.base}/runs/${runId}/logs`);
  }

  deleteRun(runId: string, force: boolean = false): Observable<DeleteRunResponse> {
    return this.http.delete<DeleteRunResponse>(`${this.base}/runs/${runId}?force=${force ? 'true' : 'false'}`);
  }

  deleteAllRuns(confirm: boolean = true, force: boolean = false): Observable<DeleteAllRunsResponse> {
    return this.http.delete<DeleteAllRunsResponse>(`${this.base}/runs?confirm=${confirm ? 'true' : 'false'}&force=${force ? 'true' : 'false'}`);
  }

  artifactUrl(runId: string, name: string): string {
    return `${this.base}/runs/${runId}/artifacts/${name}`;
  }

  streamlitRunUrl(runId: string): string {
    return `${this.streamlitBase}/?run_id=${encodeURIComponent(runId)}`;
  }
}