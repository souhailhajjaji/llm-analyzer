import axios from 'axios';
import type { AnalysisReport, AnalysisStatus, HealthStatus, FeedbackRequest } from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const analysisApi = {
  checkHealth: async (): Promise<HealthStatus> => {
    const response = await api.get<HealthStatus>('/health');
    return response.data;
  },

  analyzeFile: async (file: File): Promise<{ id: string; status: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  analyzeText: async (text: string): Promise<AnalysisReport> => {
    const response = await api.post<AnalysisReport>('/analyze/text', { text });
    return response.data;
  },

  getAnalysisStatus: async (id: string): Promise<AnalysisStatus> => {
    const response = await api.get<AnalysisStatus>(`/analyze/${id}/status`);
    return response.data;
  },

  getAnalysisResult: async (id: string): Promise<AnalysisReport> => {
    const response = await api.get<AnalysisReport>(`/analyze/${id}`);
    return response.data;
  },

  submitFeedback: async (feedback: FeedbackRequest) => {
    const response = await api.post('/feedback', feedback);
    return response.data;
  },
};
