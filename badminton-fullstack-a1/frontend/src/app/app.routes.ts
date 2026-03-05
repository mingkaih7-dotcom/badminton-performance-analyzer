import { Routes } from '@angular/router';
import { UploadPageComponent } from './pages/upload-page.component';
import { RunsPageComponent } from './pages/runs-page.component';
import { JobPageComponent } from './pages/job-page.component';
import { RunPageComponent } from './pages/run-page.component';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'upload' },
  { path: 'upload', component: UploadPageComponent },
  { path: 'runs-list', component: RunsPageComponent },
  { path: 'jobs/:jobId', component: JobPageComponent },
  { path: 'runs/:runId', component: RunPageComponent },
  { path: '**', redirectTo: 'upload' }
];